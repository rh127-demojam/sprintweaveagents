"""Run CPAT Ansible playbooks and stream output."""

from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from typing import Any

from paths import cluster_artifacts_dir, ensure_data_dirs

CPAT_ROOT = os.environ.get("CPAT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
ANSIBLE_CONFIG = os.environ.get("ANSIBLE_CONFIG", os.path.join(CPAT_ROOT, "ansible.cfg"))
MAIN_PLAYBOOK = os.path.join(CPAT_ROOT, "ansible", "playbooks", "main.yml")
OCP_PLAYBOOK = os.path.join(CPAT_ROOT, "ansible", "playbooks", "ocp_install.yml")
OCP_VALIDATE_PLAYBOOK = os.path.join(CPAT_ROOT, "ansible", "playbooks", "ocp_validate.yml")

RHOSO_INSTALLATION_TASK_TAGS = {
    # --- manifests/ — Generate phase (1 entry) ---
    "Generate Manifests for Review": "manifests/manifest_generation",
    # --- prerequisites/ — Pre-deployment checks & operators (4 entries) ---
    "Pre-requisites": "prerequisites/prerequisites",
    "Verify Required CRDs": "common/_verify_required_crds",
    "Prerequisite Operator Installation": "prerequisites/prerequisite_operator_installation",
    "Disconnected Environment Preparation": "prerequisites/disconnected_environment_preparation",
    # --- secrets/ — Credential generation (3 entries) ---
    "Generate OSP Secret": "secrets/generate_osp_secret",
    "Generate Data Plane Secrets": "secrets/generate_data_plane_secrets",
    "Generate Ceph Secret": "secrets/generate_ceph_secret",
    # --- storage/ — Storage backends (3 entries) ---
    "Persistent Storage Configuration": "storage/persistent_storage_configuration",
    "Trident Storage Configuration": "storage/trident_storage_configuration",
    "Generate Storage CRs": "storage/_generate_storage_crs",
    # --- control_plane/ — Operator install & CP lifecycle (4 entries) ---
    "OpenStack Operator Installation and Preparation": (
        "control_plane/openstack_operator_installation_and_preparation"
    ),
    "RHOCP Preparation for RHOSO": "control_plane/rhocp_preparation_for_rhoso",
    "Control Plane Deployment and Verification": (
        "control_plane/control_plane_deployment_and_verification"
    ),
    "Control Plane Customization": "control_plane/control_plane_customization",
    # --- network/ — Network preparation (1 entry) ---
    "Network Preparation": "network/network_preparation",
    # --- data_plane/ — DP lifecycle (1 entry) ---
    "Data Plane Deployment and Verification": "data_plane/data_plane_deployment_and_verification",
    # --- post_deployment/ — Post-deploy (2 entries) ---
    "Post-Deployment Validation": "post_deployment/post_deployment_validation",
    "Observability Configuration": "post_deployment/observability_configuration",
    # --- 19 entries total across 9 functional subdirectories ---
}

RHOSO_GENERATE_TASK = "Generate Manifests for Review"
RHOSO_DEPLOY_TASKS = [
    name for name in RHOSO_INSTALLATION_TASK_TAGS if name != RHOSO_GENERATE_TASK
]


# ---------------------------------------------------------------------------
# OCP Installation Task Tags — maps UI task names to Ansible subdirectory paths
# ---------------------------------------------------------------------------

OCP_INSTALLATION_TASK_TAGS: dict[str, str] = {
    # --- manifests/ — Generate phase ---
    "OCP Generate Manifests": "generate_manifests",
    # --- prerequisites/ (combined) ---
    "OCP Prerequisites": "prerequisites",
    "OCP Bastion Preparation": "bastion_preparation",
    "OCP DNS DHCP Validation": "dns_dhcp_validation",
    "OCP NTP Sync": "ntp_sync",
    # --- mirror/ (disconnected) ---
    "OCP Mirror Registry Install": "mirror_registry",
    "OCP OC Mirror Execution": "oc_mirror",
    "OCP IDMS ITMS Configuration": "idms_itms_config",
    # --- install_config/ ---
    "OCP Generate Install Config": "install_config",
    "OCP Generate Agent Config": "agent_config",
    "OCP Generate NMState Configs": "nmstate_configs",
    # --- ignition/ ---
    "OCP Generate Ignition Configs": "ignition_configs",
    "OCP Create Agent ISO": "agent_iso",
    "OCP Boot Nodes From ISO": "boot_nodes",
    # --- bootstrap/ ---
    "OCP Bootstrap Cluster": "bootstrap",
    "OCP Wait Install Complete": "wait_install",
    # --- cluster_config/ ---
    "OCP Approve CSRs": "approve_csrs",
    "OCP Configure Authentication": "auth_config",
    "OCP Day-2 Operator Installation": "day2_operators",
    # --- network/ ---
    "OCP MetalLB Configuration": "metallb_config",
    "OCP SR-IOV Multus Configuration": "sriov_config",
    # --- validation/ ---
    "OCP Cluster Health Check": "health_check",
    "OCP Node Readiness Check": "node_readiness",
    # --- uninstall/ ---
    "OCP Uninstall Mirror Registry": "uninstall_mirror_registry",
    "OCP Destroy Cluster": "destroy_cluster",
    # --- full install ---
    "OCP Full Install": "full_install",
}

OCP_GENERATE_TASK = "OCP Generate Manifests"
OCP_DEPLOY_TASKS = [
    name for name in OCP_INSTALLATION_TASK_TAGS
    if name not in (OCP_GENERATE_TASK,)
]


class AnsibleRunnerError(Exception):
    pass


def stream_playbook(
    playbook_path: str,
    extra_vars: dict,
    tags: list[str] | None = None,
) -> Iterator[tuple[str, Any]]:
    """
    Run an Ansible playbook and yield (event_type, payload) tuples.

    event_type: log | complete | error
    """
    if not os.path.isfile(playbook_path):
        yield ("error", {"message": f"Playbook not found: {playbook_path}"})
        return

    # Write extra_vars to a temp JSON file to avoid shell arg length limits
    # and prevent huge JSON dumps in the log output.
    vars_file = None
    try:
        fd, vars_file = tempfile.mkstemp(suffix=".json", prefix="cpat_vars_")
        with os.fdopen(fd, "w") as fh:
            json.dump(extra_vars, fh)

        cmd = [
            "ansible-playbook",
            playbook_path,
            "-e", f"@{vars_file}",
        ]
        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        env = os.environ.copy()
        env["ANSIBLE_CONFIG"] = ANSIBLE_CONFIG
        env["ANSIBLE_FORCE_COLOR"] = "false"
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"

        playbook_name = os.path.basename(playbook_path)
        tag_str = f" --tags {','.join(tags)}" if tags else ""
        yield ("log", {"line": f"Executing: ansible-playbook {playbook_name}{tag_str}"})

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=CPAT_ROOT,
                env=env,
            )
        except FileNotFoundError:
            yield (
                "error",
                {"message": "ansible-playbook not found. Install Ansible in the container image."},
            )
            return
        except Exception as exc:
            yield ("error", {"message": f"Failed to start ansible-playbook: {exc}"})
            return

        assert process.stdout is not None

        # Use a threaded reader so we can send SSE keepalives while
        # Ansible blocks on long-running commands (mirror-registry
        # install, oc-mirror, etc.).  Without this, the idle SSE
        # connection can be dropped by nginx, the browser, or any
        # intermediate proxy.
        _KEEPALIVE_INTERVAL = 30  # seconds

        line_q: queue.Queue[str | None] = queue.Queue()

        def _reader() -> None:
            assert process.stdout is not None
            for raw in process.stdout:
                line_q.put(raw)
            line_q.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        while True:
            try:
                line = line_q.get(timeout=_KEEPALIVE_INTERVAL)
            except queue.Empty:
                if process.poll() is not None:
                    break
                yield ("log", {"line": "... (task in progress, waiting for output) ..."})
                continue
            if line is None:
                break
            cleaned = line.rstrip("\n")
            if cleaned:
                yield ("log", {"line": cleaned})

        reader_thread.join(timeout=5)
        return_code = process.wait()
        if return_code == 0:
            yield ("complete", {"message": "Ansible playbook completed successfully."})
        else:
            yield (
                "error",
                {
                    "message": f"Ansible playbook failed with exit code {return_code}.",
                    "exit_code": return_code,
                },
            )
    finally:
        if vars_file and os.path.isfile(vars_file):
            os.remove(vars_file)


def stream_register_cluster_playbook(
    ciq_file_path: str,
    cluster_description: str = "",
    registration_target: str = "",
) -> Iterator[tuple[str, Any]]:
    """Run main.yml with the register tag and yield (event_type, payload) tuples."""
    extra_vars = {
        "ciq_file_path": ciq_file_path,
        "cluster_description": cluster_description,
        "registration_target": registration_target,
    }
    yield from stream_playbook(MAIN_PLAYBOOK, extra_vars, tags=["register"])


def stream_rhoso_installation_playbook(
    cluster_name: str,
    rhoso_version: str,
    task_name: str,
    ciq_file_path: str = "",
    ciq_parameter_overrides: dict | None = None,
    rhoso_apply_manifests: bool = True,
    rhoso_skip_generation: bool = False,
    execution_uuid: str = "",
) -> Iterator[tuple[str, Any]]:
    """Run main.yml with rhoso role tags for the selected task."""
    task_tag = RHOSO_INSTALLATION_TASK_TAGS.get(task_name)
    if not task_tag:
        yield ("error", {"message": f"Unknown RHOSO installation task: {task_name}"})
        return

    # Generate-for-review always templates only (never apply).
    if task_name == RHOSO_GENERATE_TASK:
        rhoso_apply_manifests = False
        rhoso_skip_generation = False

    ensure_data_dirs()
    extra_vars = {
        "cluster_name": cluster_name,
        "rhoso_version": rhoso_version,
        "installation_task": task_tag,
        "rhoso_manifest_dir": cluster_artifacts_dir(cluster_name),
        "rhoso_apply_manifests": bool(rhoso_apply_manifests),
        "rhoso_skip_generation": bool(rhoso_skip_generation),
    }
    if ciq_file_path:
        extra_vars["ciq_file_path"] = ciq_file_path
    if ciq_parameter_overrides:
        extra_vars["ciq_parameter_overrides"] = ciq_parameter_overrides
    yield from stream_playbook(MAIN_PLAYBOOK, extra_vars, tags=["rhoso"])


def stream_ocp_installation_playbook(
    cluster_name: str,
    ocp_version: str,
    task_name: str,
    ciq_file_path: str = "",
    ciq_parameter_overrides: dict | None = None,
    ocp_apply_manifests: bool = True,
    ocp_skip_generation: bool = False,
    execution_uuid: str = "",
) -> Iterator[tuple[str, Any]]:
    """Run ocp_install.yml for the selected OCP task."""
    task_tag = OCP_INSTALLATION_TASK_TAGS.get(task_name)
    if not task_tag:
        yield ("error", {"message": f"Unknown OCP installation task: {task_name}"})
        return

    if task_name == OCP_GENERATE_TASK:
        ocp_apply_manifests = False
        ocp_skip_generation = False

    ensure_data_dirs()
    extra_vars: dict[str, Any] = {
        "ocp_cluster_name": cluster_name,
        "ocp_version": ocp_version,
        "ocp_task": task_tag,
        "ocp_manifest_dir": cluster_artifacts_dir(cluster_name),
        "ocp_apply_manifests": bool(ocp_apply_manifests),
        "ocp_skip_generation": bool(ocp_skip_generation),
    }
    if execution_uuid:
        extra_vars["cpat_execution_uuid"] = execution_uuid
    if ciq_file_path:
        extra_vars["ocp_ciq_file"] = ciq_file_path
    if ciq_parameter_overrides:
        extra_vars.update(ciq_parameter_overrides)
    yield from stream_playbook(OCP_PLAYBOOK, extra_vars)


def stream_register_ocp_playbook(
    parsed_ciq: dict,
) -> Iterator[tuple[str, Any]]:
    """Run ocp_validate.yml with parsed CIQ data and yield (event_type, payload) tuples.

    This streams live Ansible validation logs during OCP cluster registration,
    providing the same experience as RHOSO registration.
    """
    extra_vars: dict[str, Any] = {
        "ocp_cluster_name": parsed_ciq["cluster_name"],
        "ocp_ciq": parsed_ciq["parameters"],
        "ocp_install_method": parsed_ciq["parameters"].get("Install Method", "ABI").upper(),
        "ocp_deployment_mode": parsed_ciq["parameters"].get("Deployment Mode", "connected").lower(),
        "_raw_ocp_bmc_hosts": parsed_ciq.get("bmc_hosts", []),
        "_raw_ocp_nmstate_interfaces": parsed_ciq.get("nmstate_interfaces", []),
        "_raw_ocp_compute_nodes": parsed_ciq.get("compute_nodes", []),
        "_raw_ocp_dns_records": parsed_ciq.get("dns_records", []),
    }
    yield from stream_playbook(OCP_VALIDATE_PLAYBOOK, extra_vars)
