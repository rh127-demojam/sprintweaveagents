from __future__ import annotations

import hashlib
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from api.agent_runtime import AgentCancelled, run_agent_loop, WorkspaceTools
from api.langgraph_runtime import (
    langgraph_enabled_for,
    langgraph_importable,
    run_langgraph_complete_bundle,
    run_langgraph_single_shot,
    run_tool_agent,
)
from llm.client import complete
from api.job_store import save_job

TEXT_MAX = int(os.environ.get("SPRINTWEAVE_TEXT_MAX", "60000"))
# Lab single-shot: one LLM call → write generator → run it. No tool loop.
LAB_SINGLE_SHOT = os.environ.get(
    "SPRINTWEAVE_LAB_SINGLE_SHOT", "true"
).strip().lower() in {"1", "true", "yes"}
RDA_SINGLE_SHOT = os.environ.get(
    "SPRINTWEAVE_RDA_SINGLE_SHOT", "true"
).strip().lower() in {"1", "true", "yes"}
# RDE: streaming one-shot FILE bundles per layer (no explore tool loop).
# Extra one-shots only if the layer is still incomplete (Cursor continue).
RDE_SINGLE_SHOT = os.environ.get(
    "SPRINTWEAVE_RDE_SINGLE_SHOT", "true"
).strip().lower() in {"1", "true", "yes"}
RDE_LAYER_MAX_CALLS = max(1, int(os.environ.get("SPRINTWEAVE_RDE_LAYER_MAX_CALLS", "4")))
# Ansible tool-loop: keep running rounds until smoke/count gate passes (or safety cap).
ANSIBLE_ROUND_STEPS = max(10, int(os.environ.get("SPRINTWEAVE_ANSIBLE_ROUND_STEPS", "25")))
ANSIBLE_MAX_ROUNDS = max(1, int(os.environ.get("SPRINTWEAVE_ANSIBLE_MAX_ROUNDS", "12")))
# Cursor-like completeness: counts + smoke paths (not a hardcoded .j2 name list).
ANSIBLE_MIN_TEMPLATES = max(1, int(os.environ.get("SPRINTWEAVE_ANSIBLE_MIN_TEMPLATES", "19")))
ANSIBLE_MIN_TASK_YMLS = max(1, int(os.environ.get("SPRINTWEAVE_ANSIBLE_MIN_TASK_YMLS", "20")))
ANSIBLE_MIN_LIBRARY_PY = max(0, int(os.environ.get("SPRINTWEAVE_ANSIBLE_MIN_LIBRARY_PY", "2")))
ANSIBLE_REPAIR = os.environ.get(
    "SPRINTWEAVE_ANSIBLE_REPAIR", "true"
).strip().lower() in {"1", "true", "yes", "on"}
ANSIBLE_REPAIR_STEPS = max(4, int(os.environ.get("SPRINTWEAVE_ANSIBLE_REPAIR_STEPS", "20")))
AGENT_PROMPT_MAX = int(os.environ.get("SPRINTWEAVE_AGENT_PROMPT_MAX", "24000"))
PROMPTS_DIR = Path(os.environ.get("SPRINTWEAVE_PROMPTS", "/opt/app-root/src/prompts"))
AGENTS_DIR = Path(
    os.environ.get("SPRINTWEAVE_AGENTS_DIR", "/opt/app-root/src/sprintweave-agents")
)
RULES_DIR = AGENTS_DIR / ".cursor" / "rules"

DOCLING_EXTENSIONS = {".pdf", ".docx", ".pptx", ".doc", ".ppt"}
USE_DOCLING = os.environ.get("SPRINTWEAVE_USE_DOCLING", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
# Persist parsed markdown by content hash under the Docling cache dir (re-runs free).
DOCLING_MD_CACHE = os.environ.get(
    "SPRINTWEAVE_DOCLING_MD_CACHE", "true"
).strip().lower() in {"1", "true", "yes"}

# Agents that use the Cursor-like tool loop (write real files).
TOOL_AGENTS = {
    "RHOSO DA",
    "RHOSO Deployment Engineer",
    "OCP DA",
    "OCP Deployment Engineer",
}

AGENT_TEMPLATE_FILES = {
    "RHOSO DA": "rhoso-da.md",
    "RHOSO Deployment Engineer": "rhoso-deployment-engineer.md",
    "OCP DA": "ocp-da.md",
    "OCP Deployment Engineer": "ocp-deployment-engineer.md",
}

SKILLS_DIR = AGENTS_DIR / ".cursor" / "skills"
SKILL_PROMPT_MAX = int(os.environ.get("SPRINTWEAVE_SKILL_PROMPT_MAX", "12000"))

# ── Pipeline Config Loader ──────────────────────────────────────
# All stage/sub-stage definitions live in pipelines.yaml.
# worker.py reads them generically — no agent-specific routing.

_PIPELINES_CACHE: dict[str, Any] | None = None


def _load_pipeline_config() -> dict[str, Any]:
    """Load pipelines.yaml from the agents tree. Cached after first read."""
    global _PIPELINES_CACHE
    if _PIPELINES_CACHE is not None:
        return _PIPELINES_CACHE
    path = AGENTS_DIR / "context" / "pipelines.yaml"
    if not path.is_file():
        _PIPELINES_CACHE = {"version": 3, "custom": []}
        return _PIPELINES_CACHE
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _PIPELINES_CACHE = data
    return data


def _find_sub_stages(pipeline_id: str, stage_abbrev: str) -> list[dict]:
    """Look up sub_stages for a specific pipeline+stage from config."""
    config = _load_pipeline_config()
    for pipe in config.get("custom", []):
        if pipe.get("id") != pipeline_id:
            continue
        for stage in pipe.get("stages", []):
            if stage.get("abbrev") == stage_abbrev:
                return list(stage.get("sub_stages") or [])
    return []


def _find_stage_config(pipeline_id: str, stage_abbrev: str) -> dict:
    """Return the full stage config dict from pipelines.yaml."""
    config = _load_pipeline_config()
    for pipe in config.get("custom", []):
        if pipe.get("id") != pipeline_id:
            continue
        for stage in pipe.get("stages", []):
            if stage.get("abbrev") == stage_abbrev:
                return dict(stage)
    return {}


def _find_deploy_spec(pipeline_id: str, stage_abbrev: str) -> dict:
    """Return deploy_spec for a stage, if any."""
    stage = _find_stage_config(pipeline_id, stage_abbrev)
    return dict(stage.get("deploy_spec") or {})


def _filter_de_sub_stages(all_subs: list[dict], stage: dict) -> list[dict]:
    """
    If the pipeline stage is a single sub-stage (RDE-3 / ODE-1 / sub_stage=Frontend),
    run only that pass. Monolithic RDE/ODE stages still run the full list.
    """
    want_abbrev = str(stage.get("abbrev") or "").strip().upper()
    want_name = str(stage.get("sub_stage") or "").strip()
    # Whole-agent stage (legacy rhoso / ocp pipeline)
    if want_abbrev in {"RDE", "ODE"} and not want_name:
        return list(all_subs)
    if not want_name and "-" not in want_abbrev:
        return list(all_subs)

    matched: list[dict] = []
    for sub in all_subs:
        sab = str(sub.get("abbrev") or "").strip().upper()
        sname = str(sub.get("name") or "").strip()
        if want_abbrev and sab == want_abbrev:
            matched.append(sub)
        elif want_name and sname.lower() == want_name.lower():
            matched.append(sub)
    return matched if matched else list(all_subs)


# ── Validator Registry ──────────────────────────────────────────
# Generic validators. Pipeline config names them; worker.py runs them.
# Each validator takes a Path and returns list[str] of error messages.

def _validator_python_syntax(target_dir: Path) -> list[str]:
    """ast.parse every .py file — catches ANY syntax error."""
    return _validate_python_syntax(target_dir)


def _validator_python_imports(target_dir: Path) -> list[str]:
    """Resolve every from X import Y — catches import mismatches."""
    return _validate_python_imports(target_dir)


def _validator_frontend_jsx(target_dir: Path) -> list[str]:
    """Brace/paren balance on JSX/JS files."""
    return _validate_frontend(target_dir)


def _validator_dockerfile(target_path: Path) -> list[str]:
    """ENTRYPOINT/CMD, EXPOSE, COPY syntax."""
    return _validate_dockerfile(target_path)


def _validator_entrypoint_sh(target_path: Path) -> list[str]:
    """set -e + chmod detection."""
    return _validate_entrypoint(target_path)


def _validator_nginx_conf(cpat_root: Path) -> list[str]:
    """Config existence + listen directive."""
    return _validate_nginx(cpat_root)


def _validator_yaml_lint(target_dir: Path) -> list[str]:
    """Basic YAML syntax check on .yml/.yaml files."""
    errors: list[str] = []
    if not target_dir.is_dir():
        return errors
    for ext in ("*.yml", "*.yaml"):
        for f in sorted(target_dir.rglob(ext)):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    yaml.safe_load(text)
            except yaml.YAMLError as exc:
                errors.append(f"YAML error in {f.name}: {exc}")
    return errors


# Maps validator name (from pipelines.yaml) → (function, path_resolver)
# path_resolver: given workspace root + cpat root, returns the Path to validate
VALIDATOR_REGISTRY: dict[str, tuple[callable, str]] = {
    "python_syntax":  (_validator_python_syntax, "backend"),
    "python_imports": (_validator_python_imports, "backend"),
    "frontend_jsx":   (_validator_frontend_jsx, "frontend"),
    "dockerfile":     (_validator_dockerfile, "Dockerfile"),
    "entrypoint_sh":  (_validator_entrypoint_sh, "docker/entrypoint.sh"),
    "nginx_conf":     (_validator_nginx_conf, "."),
    "yaml_lint":      (_validator_yaml_lint, "."),
}


def _run_validators_by_name(
    cpat: Path, validator_names: list[str]
) -> list[str]:
    """Run named validators from the registry. Returns combined error list."""
    errors: list[str] = []
    for name in validator_names:
        entry = VALIDATOR_REGISTRY.get(name)
        if entry is None:
            continue
        func, rel_path = entry
        target = cpat / rel_path if rel_path != "." else cpat
        try:
            errors.extend(func(target))
        except Exception as exc:
            errors.append(f"Validator '{name}' crashed: {exc}")
    return errors


# ── Golden Template Seeder ──────────────────────────────────────
# Copies pre-tested files into workspace BEFORE the LLM runs.
# The LLM sees them as existing files and works around them.

def _seed_golden_templates(
    workspace: Path, templates: list[dict], logs: list[str]
) -> int:
    """Copy golden templates from agents tree into workspace. Returns count."""
    count = 0
    for t in templates:
        src = AGENTS_DIR / t["src"]
        dest = workspace / t["dest"]
        if not src.is_file():
            logs.append(f"[golden] SKIP (not found): {t['src']}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        count += 1
    if count:
        logs.append(f"[golden] seeded {count} template(s) into workspace")
    return count


# ── Generic Sub-Stage Loop ──────────────────────────────────────
# Replaces the hardcoded if agent_name == "RHOSO Deployment Engineer" block.
# Driven entirely by sub_stages config from pipelines.yaml.

def _run_sub_stage_loop(
    *,
    sub_stages: list[dict],
    workspace: Path,
    system: str,
    stage: dict,
    job: dict,
    previous: str,
    logs: list[str],
    flush_logs,
    cancelled,
    output_dir: Path,
    follow_block: str = "",
) -> str:
    """Execute sub-stages sequentially with validation per layer.

    Returns joined summary text. This is the generic version of what was
    previously hardcoded as the RHOSO DE / OCP DE routing blocks.
    """
    from api.agent_runtime import run_agent_loop

    summaries: list[str] = []
    agent_name = stage.get("agent", "")
    da_context = previous[:15000] if previous else "(none)"
    tag = sub_stages[0].get("abbrev", "SUB").split("-")[0].lower() if sub_stages else "sub"

    for sub in sub_stages:
        if cancelled():
            from api.worker import _mark_cancelled
            _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
            return ""

        sub_name = sub.get("name", "?")
        sub_abbrev = sub.get("abbrev", sub_name)
        logs.append(f"[{tag}-pass] {sub_name} — starting")
        flush_logs(logs)

        # Seed golden templates before LLM runs
        golden = sub.get("golden_templates") or []
        if golden:
            _seed_golden_templates(workspace, golden, logs)
            flush_logs(logs)

        part = ""
        used_single = False
        force_tool_loop = sub.get("tool_loop", False)

        if RDE_SINGLE_SHOT and not force_tool_loop:
            try:
                part = _run_rde_single_shot(
                    workspace=workspace,
                    sub=sub,
                    rda_context=da_context,
                    logs=logs,
                    flush_logs=lambda: flush_logs(logs),
                    should_cancel=cancelled,
                )
                used_single = True
            except Exception as ss_exc:
                logs.append(
                    f"[{tag}-single-shot] {sub_name} failed "
                    f"({type(ss_exc).__name__}) — falling back to tool loop"
                )
                flush_logs(logs)
        elif force_tool_loop:
            logs.append(f"[{tag}-pass] {sub_name} — using tool loop")
            flush_logs(logs)

        if not used_single:
            user = (
                f"Stage: {stage.get('abbrev', '')} {agent_name}\n"
                f"{sub.get('prompt', '')}\n"
                f"Expected overall deliverables: {stage.get('output', '')}\n"
                f"Input set id: {job.get('input_id') or '(none)'}\n"
                f"{_format_cursor_prompt(job)}\n\n"
                f"{follow_block}"
                "Workspace: input/, parsed/, context/, "
                ".cursor/skills/, output/.\n"
                "Prior stage analysis (summary below).\n"
                "Write ONLY this sub-stage's files. "
                "Prefer many small files.\n"
                "Edit like Cursor: write_file → "
                "append_file/str_replace.\n"
                "FORBIDDEN: run_python(code=...), "
                "exploring parsed/.\n\n"
                f"Prior stage output:\n{da_context}\n\n"
            )

            # Ansible-specific: copy schema before RDE-2+
            if sub_name == "Ansible":
                pass  # Ansible is first, no prior schema to copy
            elif sub.get("layer") == "backend":
                _ensure_ansible_schema_copy(workspace, logs)

            part = run_agent_loop(
                workspace=workspace,
                system=system,
                user=user,
                logs=logs,
                on_log=lambda: flush_logs(logs),
                should_cancel=cancelled,
            )

        # Verify expected output files
        vp = list(sub.get("verify_paths") or [])
        if vp:
            vp_found, vp_miss = [], []
            for rel in vp:
                p = workspace / rel
                if p.is_file() and p.stat().st_size > 0:
                    vp_found.append(rel)
                else:
                    vp_miss.append(rel)
            status = "OK" if not vp_miss else "WARN"
            logs.append(
                f"[verify_paths] {sub_abbrev} "
                f"{status} — {len(vp_found)} verified, "
                f"{len(vp_miss)} missing"
            )
            for m in vp_miss:
                logs.append(f"[verify_paths] MISSING: {m}")
            flush_logs(logs)

        summaries.append(f"### {sub_abbrev}-{sub_name}\n\n{part}\n")
        _sync_workspace_output(workspace, output_dir)

        # Run validators declared in pipeline config
        validator_names = sub.get("validators") or []
        layer = sub.get("layer")
        cpat = workspace / "output" / "cpat"

        if validator_names:
            logs.append(
                f"[validate] running {', '.join(validator_names)} "
                f"on {layer or 'all'}..."
            )
            flush_logs(logs)
            remaining = _run_validators_by_name(cpat, validator_names)

            if remaining:
                # Cursor-style fix loop — feed errors to LLM
                logs.append(
                    f"[validate] {len(remaining)} issue(s) found — "
                    f"running fix loop..."
                )
                flush_logs(logs)
                remaining = _cpat_validate_and_fix(
                    workspace=workspace,
                    layer=layer,
                    system=system,
                    logs=logs,
                    flush_logs=lambda: flush_logs(logs),
                    should_cancel=cancelled,
                )
                if remaining:
                    summaries.append(
                        f"### {sub_abbrev}-Validation\n\n"
                        f"⚠ {len(remaining)} issue(s) remain:\n"
                        + "\n".join(f"- {e}" for e in remaining[:10])
                        + "\n"
                    )
            else:
                logs.append(f"[validate] {sub_abbrev} passed ✓")
            flush_logs(logs)

        _sync_workspace_output(workspace, output_dir)
        logs.append(f"[{tag}-pass] {sub_name} — done")
        flush_logs(logs)
        follow_block = ""

    # Final cross-layer validation
    cpat = workspace / "output" / "cpat"
    if cpat.is_dir():
        final_errors = _run_cpat_validators(cpat)
        if final_errors:
            logs.append(
                f"[validate-final] {len(final_errors)} issue(s) across all layers:"
            )
            for e in final_errors[:15]:
                logs.append(f"[validate-final]   • {e}")
        else:
            logs.append("[validate-final] all layers passed validation ✓")
        flush_logs(logs)

    return "\n".join(summaries)


# ── Legacy sub-stage lists (kept as fallback if pipelines.yaml is missing) ──
# These are the SAME data that now lives in pipelines.yaml.
# worker.py prefers pipelines.yaml; falls back to these if not found.
RDE_SUB_STAGES: list[dict] = [
    {
        "name": "Ansible",
        "abbrev": "RDE-1",
        "tool_loop": True,
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Ansible. "
            "Generate the complete Ansible layer: 25 task files in 9 subdirs, "
            "19 Jinja2 templates, ~170 defaults, library modules, module_utils "
            "(v1.4 schema). Write all files to output/cpat/ansible/. Follow the "
            "agent rule at .cursor/rules/agent-rhoso-deployment-engineer.md. "
            "CRITICAL: Task files live in subdirectories — main.yml includes "
            "'{{ installation_task }}.yml' so backend tags MUST be subdir/task "
            "(e.g. 'network/network_preparation'). Schema file MUST be complete "
            "Python — no truncation. If >500 lines, write in parts."
        ),
        "verify_paths": [
            "output/cpat/ansible/playbooks/roles/rhoso/tasks/main.yml",
            "output/cpat/ansible/playbooks/roles/rhoso/templates/openstack_control_plane.yaml.j2",
            "output/cpat/ansible/playbooks/roles/rhoso/defaults/main.yml",
        ],
    },
    {
        "name": "Backend",
        "abbrev": "RDE-2",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Backend. "
            "Generate the complete Flask backend: app.py (19+ routes), "
            "ansible_runner.py (19 task tags with subdir/task paths), "
            "ciq_parser.py (cross-sheet), models.py, paths.py, input_files.py, "
            "version.py, rhoso_ciq_schema.py shim, requirements.txt. Write all "
            "files to output/cpat/backend/. Read the CIQ schema from "
            "output/cpat/ansible/module_utils/rhoso_ciq_schema.py. "
            "CRITICAL: RHOSO_INSTALLATION_TASK_TAGS values MUST use "
            "'subdir/task_name' format (19 entries). Backend schema shim MUST "
            "import the SAME symbol names as module_utils defines.\n"
            "CRITICAL — rhoso_ciq_schema.py shim: NEVER use "
            "importlib.import_module('rhoso_ciq_schema') — that circular-imports "
            "the shim itself and crashes Gunicorn. Load the canonical file with "
            "importlib.util.spec_from_file_location pointing at "
            "ansible/module_utils/rhoso_ciq_schema.py, then alias symbols "
            "(RHOSO_CIQ_SCHEMA ↔ RHOSO_PARAMETER_SCHEMA, etc.)."
        ),
        "verify_paths": [
            "output/cpat/backend/app.py",
            "output/cpat/backend/ansible_runner.py",
        ],
    },
    {
        "name": "Frontend",
        "abbrev": "RDE-3",
        "tool_loop": True,
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Frontend. "
            "Generate the complete React frontend: 11 components, App.jsx, "
            "api.js, index.css, vite.config.js, package.json, nginx config. "
            "Write all files to output/cpat/frontend/. Match API routes "
            "from output/cpat/backend/app.py.\n"
            "CRITICAL: Logo SVGs are already seeded at "
            "output/cpat/frontend/public/redhat-logo.svg and "
            "redhat-logo-sidebar.svg — do NOT overwrite or invent placeholder "
            "SVGs (no solid red rects). Login.jsx must use "
            "<img src=\"/redhat-logo.svg\" className=\"login-logo\" /> with "
            "CSS .login-logo { height: 40px; width: auto; max-width: 220px; }."
        ),
        "verify_paths": [
            "output/cpat/frontend/src/components/RhosoInstallation.jsx",
            "output/cpat/frontend/package.json",
        ],
        "golden_templates": [
            {
                "src": "context/templates/nrho-cpat-frontend/public/redhat-logo.svg",
                "dest": "output/cpat/frontend/public/redhat-logo.svg",
            },
            {
                "src": "context/templates/nrho-cpat-frontend/public/redhat-logo-sidebar.svg",
                "dest": "output/cpat/frontend/public/redhat-logo-sidebar.svg",
            },
        ],
    },
    {
        "name": "Docker",
        "abbrev": "RDE-4",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Docker. "
            "Generate Dockerfile (multi-stage Node+Python+Nginx), "
            "docker/entrypoint.sh, bringup.sh (Podman lifecycle), "
            ".dockerignore, and USAGE.md. Write to output/cpat/.\n\n"
            "CRITICAL — OpenShift + Linux compatibility rules for the Dockerfile:\n"
            "1. OpenShift runs containers as a RANDOM non-root UID (e.g. 1000890000). "
            "Any directory the app writes to at runtime MUST be world-writable.\n"
            "2. After ALL mkdir/COPY steps, add: "
            "RUN chmod -R 777 /cpat-data /app/data /app/instance /app/uploads /tmp 2>/dev/null || true\n"
            "3. Do NOT use 'USER root' at the end. Use a non-root USER or omit USER.\n"
            "4. Do NOT use shell redirects in COPY/ADD (e.g. '2>/dev/null || true'). "
            "COPY does not support shell syntax — use 'RUN cp ... || true' instead.\n"
            "5. For COPY of optional directories, first check they exist or skip.\n"
            "6. Use EXPOSE 8080 (not 80) — OpenShift blocks ports < 1024 for non-root.\n"
            "7. In entrypoint.sh: mkdir -p runtime dirs; NEVER chmod the /cpat-data "
            "mount root under 'set -e' (OpenShift emptyDir rejects it — use "
            "'chmod ... 2>/dev/null || true' or omit). Create nginx temp dirs under /tmp.\n"
            "8. In nginx.conf: listen 8080; set client_body_temp_path/proxy_temp_path to /tmp/...\n"
            "9. Dockerfile: chmod -R 777 /var/lib/nginx /var/log/nginx /run /tmp as well.\n"
            "10. The Dockerfile must work on both plain Docker/Podman AND OpenShift.\n"
        ),
        "verify_paths": [
            "output/cpat/Dockerfile",
            "output/cpat/bringup.sh",
            "output/cpat/USAGE.md",
        ],
    },
    {
        "name": "AAP",
        "abbrev": "RDE-5",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=AAP. "
            "Generate RHOSO-specific AAP 2.5 exports:\n"
            "1. output/cpat/aap/exports/rhoso-job-templates.yml — "
            "CPAT RHOSO Install JT (main.yml --tags rhoso, survey with 19 "
            "installation_task choices from RHOSO_INSTALLATION_TASK_TAGS) + "
            "CPAT RHOSO Register JT (main.yml --tags register).\n"
            "2. output/cpat/aap/exports/rhoso-workflow-templates.yml — "
            "CPAT RHOSO Full Install WT (19 nodes chaining the Install JT "
            "with different extra_data per task).\n"
            "Read RHOSO_INSTALLATION_TASK_TAGS from output/cpat/backend/ansible_runner.py "
            "to build the survey choices and workflow nodes. Follow the agent rule "
            "at .cursor/rules/agent-rhoso-deployment-engineer.md."
        ),
        "verify_paths": [
            "output/cpat/aap/exports/rhoso-job-templates.yml",
            "output/cpat/aap/exports/rhoso-workflow-templates.yml",
        ],
    },
]


# ODE sub-stages — OCP Deployment Engineer pipeline (mirrors run_pipeline.py _OCP_DE_STAGES).
ODE_SUB_STAGES: list[dict] = [
    {
        "name": "Ansible",
        "abbrev": "ODE-1",
        "tool_loop": True,
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Ansible. "
            "Generate the complete OCP Ansible role: 33 task files in 11 subdirs "
            "(common, prerequisites, mirror, install_config, ignition, bootstrap, "
            "cluster_config, network, validation, manifests, uninstall), "
            "12 Jinja2 templates, ~120 defaults. Write all files to "
            "output/cpat/ansible/playbooks/roles/ocp/. Also generate "
            "output/cpat/ansible/playbooks/ocp_install.yml and ocp_validate.yml. "
            "Follow the agent rule at .cursor/rules/agent-ocp-deployment-engineer.md. "
            "CRITICAL: Long-running tasks (mirror, ISO, bootstrap) MUST use "
            "async/poll pattern with fetch log. Boot nodes via Redfish API. "
            "Smart media-eject on bootstrap 100% disk-write."
        ),
        "verify_paths": [
            "output/cpat/ansible/playbooks/roles/ocp/tasks/main.yml",
            "output/cpat/ansible/playbooks/roles/ocp/defaults/main.yml",
            "output/cpat/ansible/playbooks/ocp_install.yml",
        ],
    },
    {
        "name": "Backend",
        "abbrev": "ODE-2",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Backend. "
            "Update the Flask backend with OCP support: add OCP routes to app.py, "
            "add OCP_INSTALLATION_TASK_TAGS (26 tasks) + OCP_TASK_COMMAND_LOGS "
            "to ansible_runner.py with stream_ocp_installation_playbook "
            "(execution_uuid, SSE keepalive), update ciq_parser.py as unified "
            "RHOSO+OCP parser, add ocp_ciq_schema.py copy, add "
            "OcpInstallationExecution to models.py, add command-log endpoint. "
            "Write to output/cpat/backend/."
        ),
        "verify_paths": [
            "output/cpat/backend/ciq_parser.py",
            "output/cpat/backend/ocp_ciq_schema.py",
        ],
    },
    {
        "name": "Frontend",
        "abbrev": "ODE-3",
        "tool_loop": True,
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Frontend. "
            "Generate OCP frontend components: OcpInstallation.jsx (4 sections: "
            "Generate, Deploy, Prerequisites, Uninstall with confirmation), "
            "OcpTaskProgress.jsx, update ExecutionTable.jsx (View Log + Command Log), "
            "update InstallationLogModal.jsx (reusable for command logs), "
            "ocpInputFiles.js, update api.js with OCP endpoints. "
            "Write to output/cpat/frontend/src/."
        ),
        "verify_paths": [
            "output/cpat/frontend/src/components/OcpInstallation.jsx",
            "output/cpat/frontend/src/ocpInputFiles.js",
        ],
    },
    {
        "name": "Docker",
        "abbrev": "ODE-4",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Docker. "
            "Update Dockerfile with OCP binary bundling (3 detection paths: "
            "pre-extracted, tarballs, internet download for oc + openshift-install), "
            "update bringup.sh (port 8080, not 80 — HAProxy needs 80), "
            "update USAGE.md with OCP sections, create binaries/README.md. "
            "Write to output/cpat/."
        ),
        "verify_paths": [
            "output/cpat/Dockerfile",
            "output/cpat/bringup.sh",
            "output/cpat/USAGE.md",
        ],
    },
    {
        "name": "AAP",
        "abbrev": "ODE-5",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=AAP. "
            "Generate AAP 2.5 deliverables:\n"
            "1. output/cpat/aap/execution-environment/ — execution-environment.yml "
            "(ansible-builder v3, ee-minimal-rhel9), requirements.yml, "
            "requirements.txt (openpyxl), bindep.txt.\n"
            "2. output/cpat/aap/exports/credential-types.yml — 3 custom types: "
            "Bastion SSH, BMC, Pull Secret.\n"
            "3. output/cpat/aap/exports/ocp-job-templates.yml — CPAT OCP Install "
            "(26 task survey from OCP_INSTALLATION_TASK_TAGS) + CPAT OCP Validate.\n"
            "4. output/cpat/aap/exports/ocp-workflow-templates.yml — 3 WTs: "
            "ABI Full (11 nodes), ABI-DC Full (14 nodes), Destroy (1 node).\n"
            "5. output/cpat/aap/exports/all-objects.yml — unified import merging "
            "OCP + RHOSO templates.\n"
            "6. output/cpat/aap/README.md — EE build + AAP setup guide.\n"
            "Read OCP_INSTALLATION_TASK_TAGS from output/cpat/backend/ansible_runner.py. "
            "Follow .cursor/rules/agent-ocp-deployment-engineer.md."
        ),
        "verify_paths": [
            "output/cpat/aap/execution-environment/execution-environment.yml",
            "output/cpat/aap/exports/ocp-job-templates.yml",
            "output/cpat/aap/exports/ocp-workflow-templates.yml",
            "output/cpat/aap/exports/all-objects.yml",
            "output/cpat/aap/README.md",
        ],
    },
]

def _ensure_ansible_schema_copy(workspace: Path, logs: list[str]) -> None:
    """Copy RDA schema into ansible/module_utils (deterministic, no LLM)."""
    src = workspace / "output" / "ciq-generators" / "rhoso_ciq_schema.py"
    dest = (
        workspace / "output" / "cpat" / "ansible" / "module_utils" / "rhoso_ciq_schema.py"
    )
    if not src.is_file():
        logs.append("[ansible-gate] no RDA schema to copy into module_utils")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    logs.append(f"[ansible-gate] copied schema → {dest.relative_to(workspace).as_posix()}")


def _ansible_missing(workspace: Path) -> list[str]:
    """Cursor-like Ansible gate: smoke paths + counts (no hardcoded .j2 names).

    Which specific templates to write comes from the RHOSO DE agent rule.
    This only ensures shape: key files exist and counts meet Cursor prompt
    expectations (≈19 templates, library modules, task tree).
    """
    root = workspace / "output" / "cpat" / "ansible"
    missing: list[str] = []
    # Same smoke trio as cpat-main/agents/cursor/run_pipeline.py verify_paths
    # plus schema + playbook entry (needed for CPAT contract).
    smoke = [
        root / "playbooks" / "main.yml",
        root / "playbooks" / "roles" / "rhoso" / "tasks" / "main.yml",
        root / "playbooks" / "roles" / "rhoso" / "defaults" / "main.yml",
        root
        / "playbooks"
        / "roles"
        / "rhoso"
        / "templates"
        / "openstack_control_plane.yaml.j2",
        root / "module_utils" / "rhoso_ciq_schema.py",
    ]
    for p in smoke:
        if not p.is_file() or p.stat().st_size <= 0:
            missing.append(p.relative_to(workspace / "output").as_posix())

    cfg_ok = any(
        p.is_file()
        for p in (
            workspace / "output" / "cpat" / "ansible.cfg",
            root / "ansible.cfg",
        )
    )
    if not cfg_ok:
        missing.append("cpat/ansible.cfg")

    tmpl_dir = root / "playbooks" / "roles" / "rhoso" / "templates"
    templates = (
        [p for p in tmpl_dir.glob("*.j2") if p.is_file()] if tmpl_dir.is_dir() else []
    )
    if len(templates) < ANSIBLE_MIN_TEMPLATES:
        missing.append(
            f"cpat/ansible/.../templates/*.j2 "
            f"(have {len(templates)}, need ≥{ANSIBLE_MIN_TEMPLATES} — "
            "follow agent rule for the full set)"
        )

    tasks_dir = root / "playbooks" / "roles" / "rhoso" / "tasks"
    task_ymls = (
        [p for p in tasks_dir.rglob("*.yml") if p.is_file()]
        if tasks_dir.is_dir()
        else []
    )
    if len(task_ymls) < ANSIBLE_MIN_TASK_YMLS:
        missing.append(
            f"cpat/ansible/.../tasks/**/*.yml "
            f"(have {len(task_ymls)}, need ≥{ANSIBLE_MIN_TASK_YMLS})"
        )

    lib_dir = root / "library"
    lib_py = (
        [p for p in lib_dir.glob("*.py") if p.is_file() and p.stat().st_size > 0]
        if lib_dir.is_dir()
        else []
    )
    if len(lib_py) < ANSIBLE_MIN_LIBRARY_PY:
        missing.append(
            f"cpat/ansible/library/*.py "
            f"(have {len(lib_py)}, need ≥{ANSIBLE_MIN_LIBRARY_PY} — "
            "see agent rule for required library modules)"
        )

    if (root / "playbooks" / "site.yml").is_file() and not (
        root / "playbooks" / "main.yml"
    ).is_file():
        missing.append("cpat/ansible/playbooks/main.yml (have site.yml instead)")
    if (root / "playbooks" / "roles" / "rhoso_deployment").is_dir() and not (
        root / "playbooks" / "roles" / "rhoso"
    ).is_dir():
        missing.append(
            "cpat/ansible/playbooks/roles/rhoso/ (have rhoso_deployment/ instead)"
        )
    return missing


def _validate_ansible_layer(workspace: Path) -> tuple[bool, str]:
    """Lightweight Ansible-layer validator (Cursor validate_rhoso_output style).

    Returns (ok, report). Does not require backend/frontend (those come later).
    Also tries gold ``agents/validate_rhoso_output.py`` when present in image.
    """
    import ast as _ast

    lines: list[str] = []
    failures = 0
    cpat = workspace / "output" / "cpat"
    ansible = cpat / "ansible"
    tasks_dir = ansible / "playbooks" / "roles" / "rhoso" / "tasks"
    tmpl_dir = ansible / "playbooks" / "roles" / "rhoso" / "templates"
    schema = ansible / "module_utils" / "rhoso_ciq_schema.py"

    def _ok(name: str, passed: bool, detail: str = "") -> None:
        nonlocal failures
        if passed:
            lines.append(f"PASS {name}")
        else:
            failures += 1
            lines.append(f"FAIL {name}" + (f" — {detail}" if detail else ""))

    missing = _ansible_missing(workspace)
    _ok("Smoke paths + counts gate", not missing, "; ".join(missing[:12]))

    if schema.is_file():
        text = schema.read_text(encoding="utf-8", errors="replace")
        try:
            _ast.parse(text)
            _ok("module_utils/rhoso_ciq_schema.py parses", True)
        except SyntaxError as exc:
            _ok("module_utils/rhoso_ciq_schema.py parses", False, str(exc))
        _ok("SCHEMA_VERSION defined", "SCHEMA_VERSION" in text)
        _ok(
            "get_validation_schema defined",
            "def get_validation_schema" in text,
        )
        # Gate 2b: field count (Cursor checks ≥200 — structural, not name-based)
        # Gold schema uses _param() calls or {"name": ...} dicts — count both patterns.
        field_count = max(
            len(re.findall(r'["\']field["\']', text)),
            len(re.findall(r'["\']name["\']', text)),
            len(re.findall(r'_param\(', text)),
        )
        _ok(
            f"Schema parameter count ≥ 200 (found {field_count})",
            field_count >= 200,
        )
    else:
        _ok("module_utils/rhoso_ciq_schema.py present", False)

    if tmpl_dir.is_dir():
        brace_bad: list[str] = []
        for j2 in sorted(tmpl_dir.glob("*.j2")):
            t = j2.read_text(encoding="utf-8", errors="replace")
            if t.count("{{") != t.count("}}") or t.count("{%") != t.count("%}"):
                brace_bad.append(j2.name)
        _ok(
            f"Jinja braces balanced ({len(list(tmpl_dir.glob('*.j2')))} templates)",
            not brace_bad,
            ", ".join(brace_bad[:8]),
        )
    else:
        _ok("templates/ directory", False)

    if tasks_dir.is_dir():
        broken: list[str] = []
        for yml in tasks_dir.rglob("*.yml"):
            text = yml.read_text(encoding="utf-8", errors="replace")
            for inc in re.findall(r"include_tasks:\s*[\"']?([^\s\"'#]+)", text):
                if "{{" in inc:
                    continue
                if not (yml.parent / inc).is_file() and not (tasks_dir / inc).is_file():
                    broken.append(f"{yml.relative_to(tasks_dir)} -> {inc}")
        _ok(
            f"Static include_tasks resolve ({len(broken)} broken)",
            not broken,
            "; ".join(broken[:8]),
        )
    else:
        _ok("tasks/ directory", False)

    # ── Gate: Truncation check (Cursor Gate 7) ──
    # Detect Python files that end mid-token — sign of incomplete generation.
    py_files: list[Path] = []
    if (cpat / "backend").is_dir():
        py_files.extend(cpat / "backend" / p for p in (cpat / "backend").glob("*.py"))
    if schema.is_file():
        py_files.append(schema)
    for lib_py in (ansible / "library").glob("*.py") if (ansible / "library").is_dir() else []:
        py_files.append(lib_py)
    truncated: list[str] = []
    for pyf in py_files:
        text = pyf.read_text(encoding="utf-8", errors="replace").rstrip()
        if not text:
            continue
        if text.endswith(("\\", '("', "('", '"', "'")):
            truncated.append(pyf.name)
            continue
        try:
            _ast.parse(text)
        except SyntaxError:
            truncated.append(pyf.name)
    _ok(
        f"No truncated Python files ({len(py_files)} checked)",
        not truncated,
        ", ".join(truncated[:8]),
    )

    # ── Gate: Cross-layer sync (Cursor Gates 1, 3, 4 — only when BE/FE exist) ──
    runner = cpat / "backend" / "ansible_runner.py"
    schema_be = cpat / "backend" / "rhoso_ciq_schema.py"
    rhoso_jsx = cpat / "frontend" / "src" / "components" / "RhosoInstallation.jsx"

    # Gate 1: task-tag → file resolution (reads tag list from generated runner)
    if runner.is_file() and tasks_dir.is_dir():
        runner_text = runner.read_text(encoding="utf-8", errors="replace")
        tag_values = re.findall(
            r'RHOSO_INSTALLATION_TASK_TAGS\s*=\s*\{([^}]+)\}',
            runner_text, re.DOTALL,
        )
        if tag_values:
            tags = re.findall(r'["\']([a-z_/]+)["\']', tag_values[0])
            tag_paths = [t for t in tags if "/" in t or t.replace("_", "").isalpha()]
            bare = [t for t in tag_paths if "/" not in t]
            _ok("No bare task tags (subdir/task format)", not bare, str(bare[:5]))
            unresolved = [t for t in tag_paths if not (tasks_dir / f"{t}.yml").is_file()]
            _ok(
                f"All {len(tag_paths)} task tags resolve to YML files",
                not unresolved,
                ", ".join(unresolved[:8]),
            )
            _ok("Task tag count ≥ 19", len(tag_paths) >= 19, f"found {len(tag_paths)}")

    # Gate 3: schema symbol sync (module_utils ↔ backend shim)
    if schema.is_file() and schema_be.is_file():
        mu_text = schema.read_text(encoding="utf-8", errors="replace")
        be_text = schema_be.read_text(encoding="utf-8", errors="replace")
        canonical = (
            "RHOSO_PARAMETER_SCHEMA" if "RHOSO_PARAMETER_SCHEMA" in mu_text
            else "RHOSO_CIQ_PARAMETERS" if "RHOSO_CIQ_PARAMETERS" in mu_text
            else "RHOSO_CIQ_PARAMS" if "RHOSO_CIQ_PARAMS" in mu_text
            else "RHOSO_CIQ_SCHEMA" if "RHOSO_CIQ_SCHEMA" in mu_text
            else None
        )
        if canonical:
            _ok(
                f"Backend shim uses same symbol '{canonical}'",
                canonical in be_text,
                f"module_utils defines '{canonical}', backend doesn't reference it",
            )
        mu_ver = re.search(r'SCHEMA_VERSION\s*=\s*["\']([^"\']+)', mu_text)
        be_ver = re.search(r'SCHEMA_VERSION\s*=\s*["\']([^"\']+)', be_text)
        if mu_ver and be_ver:
            _ok(
                f"SCHEMA_VERSION matches ({mu_ver.group(1)} vs {be_ver.group(1)})",
                mu_ver.group(1) == be_ver.group(1),
            )
        try:
            _ast.parse(be_text)
            _ok("Backend schema shim parses as Python", True)
        except SyntaxError as exc:
            _ok("Backend schema shim parses as Python", False, str(exc))

    # Gate 4: frontend/backend task list sync
    if runner.is_file() and rhoso_jsx.is_file():
        runner_text = runner.read_text(encoding="utf-8", errors="replace")
        jsx_text = rhoso_jsx.read_text(encoding="utf-8", errors="replace")
        _kw = ("Pre", "Generate", "Install", "Deploy", "Config", "Valid",
               "Network", "Control", "Data", "RHOCP", "Storage", "CRD",
               "Observ", "Disconn", "Trident", "Ceph")
        be_tasks = {n for n in re.findall(r'"([A-Z][^"]+)"(?:\s*:|\s*\))', runner_text)
                    if any(w in n for w in _kw)}
        fe_tasks = {n for n in re.findall(r"""['"]([A-Z][^'"]+)['"]""", jsx_text)
                    if any(w in n for w in _kw)}
        only_be = be_tasks - fe_tasks
        if len(only_be) > 3:
            _ok(
                f"Frontend covers backend tasks ({len(be_tasks)} BE, {len(fe_tasks)} FE)",
                False,
                f"In backend only: {only_be}",
            )
        elif only_be:
            lines.append(
                f"WARN Frontend missing {len(only_be)} backend task(s): {only_be} "
                "(minor — not a hard failure)"
            )

    # Optional: run gold Cursor validator if bundled (skips BE/FE gates when absent).
    gold_validator = AGENTS_DIR / "agents" / "validate_rhoso_output.py"
    if gold_validator.is_file():
        import subprocess
        import sys

        try:
            proc = subprocess.run(
                [sys.executable, str(gold_validator), str(workspace / "output")],
                capture_output=True,
                text=True,
                timeout=90,
                cwd=str(AGENTS_DIR),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            lines.append("--- gold validate_rhoso_output.py ---")
            lines.append(out[-4000:] if len(out) > 4000 else out)
            if proc.returncode != 0:
                # Only count as hard fail if ansible-related FAIL lines appear
                ansible_fail = any(
                    "FAIL" in ln
                    and any(
                        k in ln.lower()
                        for k in ("template", "jinja", "schema", "include", "task")
                    )
                    for ln in out.splitlines()
                )
                if ansible_fail:
                    failures += 1
                    lines.append("FAIL gold validator reported ansible-related issues")
                else:
                    lines.append(
                        "NOTE gold validator exit!=0 (likely BE/FE gates skipped/failed "
                        "— expected during Ansible-only pass)"
                    )
        except Exception as exc:
            lines.append(f"NOTE gold validator skipped ({type(exc).__name__}: {exc})")

    report = "\n".join(lines)
    return failures == 0, report


def _ansible_repair_pass(
    *,
    workspace: Path,
    system: str,
    report: str,
    logs: list[str],
    flush_logs,
    should_cancel,
) -> str:
    """One Cursor-style repair loop after validation failures."""
    logs.append(
        f"[ansible-repair] starting repair pass (max {ANSIBLE_REPAIR_STEPS} steps)"
    )
    flush_logs()
    missing = _ansible_missing(workspace)
    miss_list = "\n".join(f"- {m}" for m in missing[:40])

    # Build inventory of what already exists so the model writes, not reads.
    _root = workspace / "output" / "cpat" / "ansible"
    _td = _root / "playbooks" / "roles" / "rhoso" / "templates"
    _existing_j2 = sorted(p.name for p in _td.glob("*.j2")) if _td.is_dir() else []
    _tk = _root / "playbooks" / "roles" / "rhoso" / "tasks"
    _existing_tasks = sorted(
        str(p.relative_to(_tk).as_posix())
        for p in _tk.rglob("*.yml") if p.is_file()
    ) if _tk.is_dir() else []
    _ld = _root / "library"
    _existing_lib = sorted(p.name for p in _ld.glob("*.py")) if _ld.is_dir() else []
    inventory = (
        f"ALREADY WRITTEN — do NOT re-read or re-create:\n"
        f"  templates ({len(_existing_j2)}): {', '.join(_existing_j2)}\n"
        f"  tasks ({len(_existing_tasks)}): {', '.join(_existing_tasks[:30])}\n"
        f"  library ({len(_existing_lib)}): {', '.join(_existing_lib)}\n"
    )

    user = (
        "REPAIR MODE — Ansible validation FAILED. Do NOT explore.\n\n"
        f"Validator report:\n{report[:6000]}\n\n"
        f"{inventory}\n"
        f"MISSING / INCOMPLETE ({len(missing)}):\n{miss_list}\n\n"
        "STRICT RULES:\n"
        "- FORBIDDEN: list_dir, search_files, run_python, reading parsed/.\n"
        "- Next tool calls MUST be write_file / append_file only.\n"
        "- If library modules are missing, create them under "
        "output/cpat/ansible/library/ (see agent rule for required modules).\n"
        "- Add enough Jinja templates under "
        "output/cpat/ansible/playbooks/roles/rhoso/templates/ to reach ≥19 "
        "(.j2). Follow the RHOSO DE agent rule for the complete list.\n"
        "- Add enough task YAMLs under roles/rhoso/tasks/ to reach ≥20.\n"
        "- Paths: playbooks/roles/rhoso/ + playbooks/main.yml only "
        "(never rhoso_deployment or site.yml).\n"
        "- Do NOT rewrite files that already exist and pass.\n"
        "Write 2–4 files per step until the missing list is empty.\n"
    )
    return run_tool_agent(
        workspace=workspace,
        system=system,
        user=user,
        logs=logs,
        on_log=flush_logs,
        should_cancel=should_cancel,
        max_steps=ANSIBLE_REPAIR_STEPS,
        scope="ansible",
        write_only=False,
    )


# ── CPAT Validate-and-Fix (Cursor-style feedback loop) ──────────────────────
# After each RDE sub-stage generates code, run *real* tool-based validators
# (ast.parse, import resolution, brace balance, Dockerfile checks) and feed
# the actual error messages back to the LLM for targeted repair.  This is
# exactly how Cursor fixes code: generate → lint → feed errors → fix → re-lint.
# Unlike hardcoded pattern-matching, these validators catch ANY error their
# underlying tool catches — including patterns we've never seen before.

_CPAT_VALIDATE_FIX_ROUNDS = max(1, int(os.environ.get("SPRINTWEAVE_CPAT_FIX_ROUNDS", "3")))
_CPAT_FIX_MAX_STEPS = int(os.environ.get("SPRINTWEAVE_CPAT_FIX_STEPS", "10"))

# Legacy — kept for backwards-compat; new code uses _cpat_validate_and_fix.
_CPAT_REVIEW_MAX_STEPS = int(os.environ.get("SPRINTWEAVE_CPAT_REVIEW_STEPS", "12"))


# ── Layer-specific validators (real tools, not pattern matching) ─────────────

def _validate_python_syntax(backend_dir: Path) -> list[str]:
    """ast.parse every .py — catches ANY syntax error or truncation."""
    import ast as _ast

    errors: list[str] = []
    if not backend_dir.is_dir():
        return errors
    for py in sorted(backend_dir.glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace").rstrip()
        if not text:
            continue
        try:
            _ast.parse(text)
        except SyntaxError as exc:
            errors.append(f"{py.name}:{exc.lineno}: SyntaxError: {exc.msg}")
        if text.endswith(("\\", '("', "('", '"', "'", ",")):
            errors.append(f"{py.name}: appears truncated (ends with '{text[-3:]}')")
    return errors


def _validate_python_imports(backend_dir: Path) -> list[str]:
    """Resolve every from-import against local modules — catches ANY import mismatch."""
    import ast as _ast

    errors: list[str] = []
    if not backend_dir.is_dir():
        return errors

    # Build export map: module_stem → set of top-level names
    exports: dict[str, set[str]] = {}
    for py in backend_dir.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        try:
            tree = _ast.parse(text)
        except SyntaxError:
            continue
        names: set[str] = set()
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                names.add(node.name)
            elif isinstance(node, _ast.ClassDef):
                names.add(node.name)
            elif isinstance(node, _ast.Assign):
                for target in node.targets:
                    if isinstance(target, _ast.Name):
                        names.add(target.id)
        exports[py.stem] = names

    # Check every from-import within the backend package
    for py in backend_dir.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        try:
            tree = _ast.parse(text)
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom) and node.module in exports:
                for alias in (node.names or []):
                    name = alias.name
                    if name != "*" and name not in exports[node.module]:
                        avail = sorted(exports[node.module])[:10]
                        errors.append(
                            f"{py.name}: ImportError: cannot import '{name}' "
                            f"from '{node.module}' "
                            f"(available: {', '.join(avail)})"
                        )

    # Circular-import detection in schema shim
    shim = backend_dir / "rhoso_ciq_schema.py"
    if shim.is_file():
        st = shim.read_text(encoding="utf-8", errors="replace")
        if 'import_module("rhoso_ciq_schema")' in st or "import_module('rhoso_ciq_schema')" in st:
            errors.append(
                "rhoso_ciq_schema.py: circular import — "
                "import_module('rhoso_ciq_schema') loads the shim itself. "
                "Use importlib.util.spec_from_file_location with the absolute "
                "path to ansible/module_utils/rhoso_ciq_schema.py instead."
            )
    return errors


def _validate_frontend(frontend_dir: Path) -> list[str]:
    """Brace/paren balance on JSX/JS — catches ANY truncation."""
    errors: list[str] = []
    src = frontend_dir / "src"
    if not src.is_dir():
        return errors
    for ext in ("*.jsx", "*.js"):
        for f in src.rglob(ext):
            text = f.read_text(encoding="utf-8", errors="replace").rstrip()
            if not text:
                continue
            opens = text.count("{") + text.count("(")
            closes = text.count("}") + text.count(")")
            diff = abs(opens - closes)
            if diff > 3:
                errors.append(
                    f"{f.name}: truncated — {opens} open delimiters vs "
                    f"{closes} close (imbalance {diff})"
                )
    return errors


def _validate_dockerfile(dockerfile: Path) -> list[str]:
    """Structural check on Dockerfile — catches missing directives, bad syntax."""
    errors: list[str] = []
    if not dockerfile.is_file():
        errors.append("Dockerfile not found")
        return errors
    text = dockerfile.read_text(encoding="utf-8", errors="replace")
    if "ENTRYPOINT" not in text and "CMD" not in text:
        errors.append("Dockerfile: no ENTRYPOINT or CMD — container won't start")
    if "EXPOSE" not in text:
        errors.append("Dockerfile: no EXPOSE — port won't be accessible in OpenShift")
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.upper().startswith("COPY") and ("2>/dev/null" in s or "|| true" in s):
            errors.append(
                f"Dockerfile:{i}: COPY uses shell syntax (redirects/|| true) "
                f"which is invalid — use 'RUN cp ... || true' instead: {s[:80]}"
            )
    return errors


def _validate_entrypoint(entrypoint: Path) -> list[str]:
    """Check entrypoint.sh for shell issues that crash on OpenShift."""
    errors: list[str] = []
    if not entrypoint.is_file():
        return errors
    text = entrypoint.read_text(encoding="utf-8", errors="replace")
    has_set_e = "set -e" in text
    if has_set_e:
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if s.startswith("chmod") and "|| true" not in s and "2>/dev/null" not in s:
                if "/cpat-data" in s or "${CPAT_DATA_DIR}" in s or "/app" in s:
                    errors.append(
                        f"entrypoint.sh:{i}: fatal chmod under 'set -e' — "
                        f"OpenShift non-root UID will crash here: {s[:80]}"
                    )
    return errors


def _validate_nginx(cpat: Path) -> list[str]:
    """Check nginx config exists and has required directives."""
    errors: list[str] = []
    nginx_found = False
    for d in (cpat / "frontend" / "nginx", cpat / "nginx", cpat / "docker" / "nginx"):
        if d.is_dir():
            for conf in d.rglob("*.conf"):
                nginx_found = True
                text = conf.read_text(encoding="utf-8", errors="replace")
                if "listen" not in text:
                    errors.append(f"nginx/{conf.name}: no 'listen' directive")
    if not nginx_found:
        errors.append("No nginx config found — web server won't start")
    return errors


def _run_cpat_validators(cpat: Path, layer: str | None = None) -> list[str]:
    """Run real tool-based validators on a CPAT package.

    Unlike hardcoded regex sanitizers, these use real parsers (ast.parse,
    import resolution, structural checks) that catch ANY error — including
    patterns we've never seen before.

    Args:
        cpat:  Root of the generated CPAT package (output/cpat/).
        layer: 'backend', 'frontend', 'docker', or None (all layers).

    Returns:
        List of human-readable error strings (empty = all good).
    """
    errors: list[str] = []

    if layer in (None, "backend"):
        errors += _validate_python_syntax(cpat / "backend")
        errors += _validate_python_imports(cpat / "backend")

    if layer in (None, "frontend"):
        errors += _validate_frontend(cpat / "frontend")

    if layer in (None, "docker"):
        errors += _validate_dockerfile(cpat / "Dockerfile")
        errors += _validate_entrypoint(cpat / "docker" / "entrypoint.sh")
        errors += _validate_nginx(cpat)

    return errors


def _collect_layer_files(cpat: Path, layer: str) -> str:
    """Collect file contents for a specific layer — used as LLM context."""
    sections: list[str] = []

    def _add(path: Path, rel_label: str | None = None):
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        label = rel_label or path.relative_to(cpat).as_posix()
        if len(text) > 6000:
            text = text[:6000] + "\n... (truncated)"
        sections.append(f"=== {label} ===\n{text}")

    if layer == "backend":
        be = cpat / "backend"
        if be.is_dir():
            for py in sorted(be.glob("*.py")):
                _add(py)
        canonical = cpat / "ansible" / "module_utils" / "rhoso_ciq_schema.py"
        _add(canonical)

    elif layer == "frontend":
        src = cpat / "frontend" / "src"
        if src.is_dir():
            for ext in ("*.jsx", "*.js"):
                for f in sorted(src.rglob(ext)):
                    _add(f)

    elif layer == "docker":
        _add(cpat / "Dockerfile")
        _add(cpat / "docker" / "entrypoint.sh")
        _add(cpat / ".dockerignore")
        for d in (cpat / "frontend" / "nginx", cpat / "nginx", cpat / "docker" / "nginx"):
            if d.is_dir():
                for conf in d.rglob("*.conf"):
                    _add(conf)

    return "\n\n".join(sections)


def _cpat_validate_and_fix(
    *,
    workspace: Path,
    layer: str,
    system: str,
    logs: list[str],
    flush_logs,
    should_cancel,
    max_rounds: int | None = None,
) -> list[str]:
    """Cursor-style validate → LLM-fix → re-validate loop for one CPAT layer.

    This is exactly how Cursor fixes code:
        1. Generate/edit code
        2. Run linters (ReadLints) — real tools, not pattern matching
        3. Feed lint errors back to the LLM
        4. LLM fixes the code
        5. Re-lint — loop until clean or max rounds

    The validators use real parsers (ast.parse, import resolution, structural
    checks) so they catch ANY error including patterns never seen before.
    The LLM sees the actual error messages and reasons about the fix —
    no hardcoded replacement rules.

    Returns remaining errors (empty = all clear).
    """
    if max_rounds is None:
        max_rounds = _CPAT_VALIDATE_FIX_ROUNDS
    cpat = workspace / "output" / "cpat"

    for round_num in range(1, max_rounds + 1):
        errors = _run_cpat_validators(cpat, layer=layer)
        if not errors:
            logs.append(f"[validate-fix] {layer}: clean ✓ (round {round_num})")
            flush_logs()
            return []

        logs.append(
            f"[validate-fix] {layer} round {round_num}/{max_rounds}: "
            f"{len(errors)} error(s)"
        )
        for e in errors:
            logs.append(f"[validate-fix]   • {e}")
        flush_logs()

        if should_cancel and should_cancel():
            return errors

        error_block = "\n".join(f"- {e}" for e in errors)
        file_context = _collect_layer_files(cpat, layer)

        fix_prompt = (
            f"VALIDATION ERRORS found in the {layer} layer "
            f"(round {round_num}/{max_rounds}):\n\n"
            f"{error_block}\n\n"
            "These are real errors from Python's ast.parse, import resolution, "
            "and structural analysis — not guesses. Fix ONLY the files that "
            "have errors. Write the complete corrected file contents.\n\n"
            "Use write_file('output/cpat/<path>', '<full corrected content>') "
            "for each file you fix.\n\n"
            f"CURRENT FILE CONTENTS:\n\n{file_context[:24000]}\n"
        )

        try:
            run_tool_agent(
                workspace=workspace,
                system=system,
                user=fix_prompt,
                logs=logs,
                on_log=flush_logs,
                should_cancel=should_cancel,
                max_steps=_CPAT_FIX_MAX_STEPS,
                scope=f"validate-fix-{layer}-r{round_num}",
                write_only=False,
            )
        except Exception as exc:
            logs.append(
                f"[validate-fix] {layer} fix round {round_num} failed: "
                f"{type(exc).__name__}: {exc}"
            )
            flush_logs()
            break

    # Final validation
    remaining = _run_cpat_validators(cpat, layer=layer)
    if remaining:
        logs.append(
            f"[validate-fix] {layer}: {len(remaining)} error(s) remain "
            f"after {max_rounds} round(s)"
        )
        for e in remaining[:5]:
            logs.append(f"[validate-fix]   ⚠ {e}")
    else:
        logs.append(f"[validate-fix] {layer}: all clear after fix round(s) ✓")
    flush_logs()
    return remaining


# Legacy wrapper — old code may call _cpat_precheck; delegate to new validators.
def _cpat_precheck(cpat: Path) -> list[str]:
    return _run_cpat_validators(cpat)


def _cpat_review_pass(
    *,
    workspace: Path,
    system: str,
    logs: list[str],
    flush_logs,
    should_cancel,
) -> str:
    """Legacy wrapper — delegates to per-layer validate-and-fix loops."""
    cpat = workspace / "output" / "cpat"
    all_remaining: list[str] = []
    for layer in ("backend", "frontend", "docker"):
        remaining = _cpat_validate_and_fix(
            workspace=workspace,
            layer=layer,
            system=system,
            logs=logs,
            flush_logs=flush_logs,
            should_cancel=should_cancel,
        )
        all_remaining.extend(remaining)
    if all_remaining:
        return f"Remaining issues: {len(all_remaining)}"
    return ""


_docling_available: bool | None = None

_TS_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} ")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_log() -> str:
    return _utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")


def _stamp_log(msg: str) -> str:
    text = str(msg or "")
    if _TS_RE.match(text):
        return text
    return f"[{_utc_log()}] {text}"


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return ""
    sec = max(0, int(seconds))
    if sec < 60:
        return f"{sec}s"
    mins, rem = divmod(sec, 60)
    if mins < 60:
        return f"{mins}m {rem}s"
    hours, rem_m = divmod(mins, 60)
    return f"{hours}h {rem_m}m"


def _close_stage_timing(job: dict, finished_at: str | None = None) -> None:
    timings = list(job.get("stage_timings") or [])
    if not timings:
        return
    last = dict(timings[-1])
    if last.get("finished_at"):
        job["stage_timings"] = timings
        return
    end = finished_at or _utc_iso()
    last["finished_at"] = end
    try:
        start = datetime.strptime(last.get("started_at") or "", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        last["duration_s"] = int((_utc_now() - start).total_seconds())
        last["duration"] = _fmt_duration(last["duration_s"])
    except ValueError:
        last["duration_s"] = None
        last["duration"] = ""
    timings[-1] = last
    job["stage_timings"] = timings


def _check_docling() -> bool:
    global _docling_available
    if _docling_available is None:
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401

            _docling_available = True
        except ImportError:
            _docling_available = False
    return _docling_available


def _ensure_writable_docling_cache() -> Path:
    """OpenShift runs as a random non-root UID — cache must be world-writable or emptyDir."""
    candidates = [
        os.environ.get("DOCLING_CACHE_DIR", "").strip(),
        os.environ.get("HF_HOME", "").strip(),
        "/tmp/docling-cache",
        "/opt/docling-cache",
    ]
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw)
        try:
            path.mkdir(parents=True, exist_ok=True)
            hub = path / "hub"
            hub.mkdir(parents=True, exist_ok=True)
            probe = hub / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            continue
        os.environ["HOME"] = os.environ.get("HOME") or "/tmp"
        os.environ["HF_HOME"] = str(path)
        os.environ["TRANSFORMERS_CACHE"] = str(path)
        os.environ["DOCLING_CACHE_DIR"] = str(path)
        os.environ["HUGGINGFACE_HUB_CACHE"] = str(hub)
        os.environ["XDG_CACHE_HOME"] = str(path)
        return path
    raise RuntimeError(
        "No writable Docling/HF cache dir. Mount emptyDir at /opt/docling-cache "
        "or ensure /tmp/docling-cache is writable."
    )


def _file_sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _md_cache_dir(cache_root: Path) -> Path:
    d = cache_root / "md-by-sha256"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_input_docs(input_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file()
        and p.name != "meta.json"
        and p.suffix.lower() in DOCLING_EXTENSIONS
    )


def _parse_with_docling(src: Path, dest: Path, converter=None) -> tuple[Path, str]:
    """Convert a binary document to Markdown using Docling only.

    Returns (md_path, source) where source is 'cache' or 'docling'.
    """
    cache = _ensure_writable_docling_cache()
    md_path = dest / (src.stem + ".md")

    digest = None
    if DOCLING_MD_CACHE:
        digest = _file_sha256(src)
        cached = _md_cache_dir(cache) / f"{digest}.md"
        if cached.is_file() and cached.stat().st_size > 0:
            shutil.copy2(cached, md_path)
            return md_path, "cache"

    if converter is None:
        converter = _get_shared_converter()
    result = converter.convert(str(src))
    md_text = result.document.export_to_markdown()
    if not (md_text or "").strip():
        raise RuntimeError(
            f"Docling returned empty markdown for {src.name} "
            f"(cache={cache})"
        )
    md_path.write_text(md_text, encoding="utf-8")
    if DOCLING_MD_CACHE and digest:
        cached = _md_cache_dir(cache) / f"{digest}.md"
        try:
            cached.write_text(md_text, encoding="utf-8")
        except OSError:
            pass
    return md_path, "docling"


_shared_converter = None


def _get_shared_converter():
    """Create a single DocumentConverter, reuse across all files in a job."""
    global _shared_converter
    if _shared_converter is not None:
        return _shared_converter

    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter, PdfFormatOption

    use_ocr = os.environ.get("SPRINTWEAVE_DOCLING_OCR", "false").strip().lower() in {
        "1", "true", "yes",
    }
    do_tables = os.environ.get("SPRINTWEAVE_DOCLING_TABLES", "false").strip().lower() in {
        "1", "true", "yes",
    }

    # Prefer threaded pipeline when available (page-level parallelism inside one PDF).
    pdf_opts = None
    try:
        from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions

        pdf_opts = ThreadedPdfPipelineOptions(
            do_ocr=use_ocr,
            do_table_structure=do_tables,
        )
        for attr, val in (
            ("ocr_batch_size", 4),
            ("layout_batch_size", 4),
            ("table_batch_size", 4),
        ):
            if hasattr(pdf_opts, attr):
                setattr(pdf_opts, attr, val)
    except Exception:
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        pdf_opts = PdfPipelineOptions(
            do_ocr=use_ocr,
            do_table_structure=do_tables,
        )

    # Fast path: no page/picture rendering or enrichments (RHOSO PDFs are text-layer).
    for attr, val in (
        ("generate_page_images", False),
        ("generate_picture_images", False),
        ("do_code_enrichment", False),
        ("do_formula_enrichment", False),
        ("do_picture_classification", False),
    ):
        if hasattr(pdf_opts, attr):
            setattr(pdf_opts, attr, val)

    _shared_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts),
        }
    )
    return _shared_converter


def _parse_inputs(
    input_dir: Path,
    parsed_dir: Path,
    logs: list[str],
    on_log: callable | None = None,
) -> dict[str, int]:
    """Run Docling on supported files. Returns counts: attempted / ok.

    No pypdf fallback — Docling only.
    """
    stats = {"attempted": 0, "ok": 0, "cache_hits": 0}
    if not input_dir.is_dir():
        return stats
    parsed_dir.mkdir(parents=True, exist_ok=True)
    if not USE_DOCLING:
        logs.append("[info] SPRINTWEAVE_USE_DOCLING=false — skipping parse")
        if on_log:
            on_log()
        return stats
    if not _check_docling():
        logs.append("[parse-error] Docling not installed in image")
        if on_log:
            on_log()
        return stats

    try:
        cache = _ensure_writable_docling_cache()
        logs.append(f"[docling] cache={cache}")
        logs.append(
            "[docling] fast opts: "
            f"ocr={os.environ.get('SPRINTWEAVE_DOCLING_OCR', 'false')} "
            f"tables={os.environ.get('SPRINTWEAVE_DOCLING_TABLES', 'false')} "
            f"md_cache={DOCLING_MD_CACHE}"
        )
        if on_log:
            on_log()
    except Exception as exc:
        logs.append(f"[parse-error] Docling cache not writable: {exc}")
        if on_log:
            on_log()
        return stats

    to_parse = _list_input_docs(input_dir)
    n_pdfs = len(to_parse)
    logs.append(f"[docling] parsing {n_pdfs} file(s) — loading converter once")
    if on_log:
        on_log()

    import time as _time
    t0_conv = _time.monotonic()
    converter = _get_shared_converter()
    logs.append(f"[docling] converter ready in {_time.monotonic() - t0_conv:.1f}s")
    if on_log:
        on_log()

    t0_all = _time.monotonic()
    for path in to_parse:
        stats["attempted"] += 1
        logs.append(
            f"[docling] {stats['attempted']}/{n_pdfs} starting {path.name}"
        )
        if on_log:
            on_log()
        t0_file = _time.monotonic()
        try:
            md_path, source = _parse_with_docling(
                path, parsed_dir, converter=converter
            )
            elapsed = _time.monotonic() - t0_file
            if source == "cache":
                stats["cache_hits"] += 1
                logs.append(
                    f"[cached] {path.name} → {md_path.name} ({elapsed:.1f}s)"
                )
            else:
                logs.append(
                    f"[parsed] {path.name} → {md_path.name} ({elapsed:.1f}s)"
                )
            stats["ok"] += 1
        except Exception as exc:
            logs.append(f"[parse-error] {path.name}: {exc}")
        if on_log:
            on_log()
    logs.append(
        f"[docling] done in {_time.monotonic() - t0_all:.1f}s "
        f"(ok={stats['ok']} cache_hits={stats['cache_hits']})"
    )
    if on_log:
        on_log()
    return stats


def _count_parsed_md(parsed_dir: Path) -> int:
    if not parsed_dir.is_dir():
        return 0
    return sum(1 for p in parsed_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md")


# Same names as ui/pipelines.py stages. Files live in sprintweave-agents/.cursor/rules/
AGENT_FILES = {
    "Requirements Analyst": "agent-requirements-analyst.md",
    "Solution Architect": "agent-solution-architect.md",
    "Technical Lead": "agent-technical-lead.md",
    "QA Architect": "agent-qa-architect.md",
    "DevOps Engineer": "agent-devops-engineer.md",
    "Cloud Deployment Engineer": "agent-cloud-deployment-engineer.md",
    "Automation Engineer": "agent-automation-engineer.md",
    "SRE Engineer": "agent-sre-engineer.md",
    "Technical Writer": "agent-technical-writer.md",
    "Governance Specialist": "agent-governance-specialist.md",
    "Project Manager": "agent-project-manager.md",
    "Sprint Coach": "agent-sprint-coach.md",
    "Proposal Writer": "agent-proposal-writer.md",
    "RHOSO DA": "agent-rhoso-da.md",
    "RHOSO Deployment Engineer": "agent-rhoso-deployment-engineer.md",
    "NRHO DA": "agent-nrho-da.md",
    "NRHO Deployment Engineer": "agent-nrho-deployment-engineer.md",
}


def _format_cursor_prompt(job: dict) -> str:
    """Expand Cursor-style @ mentions for the agent user message."""
    raw = (job.get("instructions") or "").strip()
    if not raw:
        return "(none)"
    iid = (job.get("input_id") or "").strip()
    lines = [
        "User prompt (Cursor-style):",
        raw,
        "",
        "@ reference map (OpenShift workspace):",
        "- @cpat → write/generate CPAT under output/cpat/",
        "- @input → uploaded docs in input/ and Docling text in parsed/",
        "- @context → context/ (templates, glossary, team-config)",
    ]
    if iid:
        lines.append(f"- @input:{iid} → input set id '{iid}' (same as @input for this job)")
    lines.append("- @<filename> → that file under input/ or parsed/ (prefer parsed/*.md)")
    lines.append(
        "Honour the user prompt and @ refs. Prefer tools (read/write/run_python) over chat-only answers."
    )
    return "\n".join(lines)


def _generic_system() -> str:
    candidates = [
        PROMPTS_DIR / "system.md",
        Path("/opt/app-root/src/sprintweave-web/prompts/system.md"),
        Path("/opt/app-root/src/prompts/system.md"),
        Path(__file__).resolve().parents[1] / "prompts" / "system.md",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return "You are a SprintWeave agent. Ground answers in the uploaded files."


def _load_skills_prompt() -> str:
    """Load Cursor SKILL.md files into the system prompt (capped)."""
    if not SKILLS_DIR.is_dir():
        return ""
    chunks: list[str] = []
    total = 0
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            body = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        name = skill_md.parent.name
        block = f"### Skill: {name}\nPath: .cursor/skills/{name}/SKILL.md\n\n{body}\n"
        if total + len(block) > SKILL_PROMPT_MAX:
            remain = SKILL_PROMPT_MAX - total
            if remain > 200:
                chunks.append(block[:remain] + "\n... truncated\n")
            break
        chunks.append(block)
        total += len(block)
    if not chunks:
        return ""
    return (
        "\n\n---\n# Cursor skills (apply when relevant)\n"
        "Full skill files are also under `.cursor/skills/` in the workspace — "
        "use read_file if you need more detail.\n\n"
        + "\n".join(chunks)
    )


def _resolve_rule_path(
    agent_name: str,
    *,
    rule_file: str = "",
) -> tuple[Path | None, str]:
    """Prefer PVC custom rule, then baked image rules. Returns (path, source label)."""
    try:
        from api.custom_agents import resolve_rule_file

        custom = resolve_rule_file(agent_name=agent_name, rule_file=rule_file)
        if custom is not None and custom.is_file():
            return custom, f"pvc:custom-agents/rules/{custom.name}"
    except Exception:
        pass
    filename = AGENT_FILES.get(agent_name, "")
    if filename:
        baked = RULES_DIR / filename
        if baked.is_file():
            return baked, f"sprintweave-agents/.cursor/rules/{filename}"
    return None, ""


_OUTPUT_PATH_RE = re.compile(r"`(output/[^\s`]+)`")


def _rule_extract_verify_paths(rule_path: Path | None) -> list[str]:
    """Scan a rule markdown for output/ paths suitable as verify_paths.

    Looks for lines like:  - `output/cpat/backend/app.py`
    Returns up to 30 unique paths (auto-infer when user didn't set them).
    """
    if not rule_path or not rule_path.is_file():
        return []
    try:
        text = rule_path.read_text(encoding="utf-8")[:20000]
    except OSError:
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for m in _OUTPUT_PATH_RE.finditer(text):
        p = m.group(1)
        ext = Path(p).suffix
        if ext and p not in seen:
            seen.add(p)
            paths.append(p)
        if len(paths) >= 30:
            break
    return paths


def _system_for_agent(
    agent_name: str,
    *,
    tool_mode: bool = False,
    rule_file: str = "",
) -> str:
    generic = _generic_system()
    rule_path, source = _resolve_rule_path(agent_name, rule_file=rule_file)
    if rule_path is not None and rule_path.is_file():
        body = rule_path.read_text(encoding="utf-8")[:AGENT_PROMPT_MAX]
        base = (
            f"{generic}\n\n---\n# Agent: {agent_name}\n"
            f"Source: {source}\n\n{body}"
        )
    else:
        filename = AGENT_FILES.get(agent_name, rule_file or "(none)")
        base = (
            f"{generic}\n\nYou are acting as: {agent_name}. "
            f"(No rule file found for '{filename}' — using generic prompt.)"
        )
    if not tool_mode:
        return base

    template_name = AGENT_TEMPLATE_FILES.get(agent_name, "")
    template_hint = ""
    if template_name:
        template_hint = (
            f"\nAlso read `context/templates/{template_name}` if present "
            "and follow its structure.\n"
        )
    skills = _load_skills_prompt()
    return (
        base
        + "\n\n---\n# OpenShift tool runtime\n"
        "You are running in a Cursor-like agent loop on OpenShift.\n"
        "Workspace root is the current project. Use tools to inspect and write files.\n"
        "Available tools: list_dir, read_file, write_file, append_file, str_replace, "
        "delete_file, run_python, search_files.\n"
        "Paths are relative to the workspace:\n"
        "- `input/` — uploaded source documents (may be binary PDFs)\n"
        "- `parsed/` — Docling markdown extracted from PDFs/DOCX (prefer these)\n"
        "- `context/` — team config, glossary, templates\n"
        "- `.cursor/skills/` — Cursor skills\n"
        "- `output/` — write ALL deliverables here (ciq-generators, ciq-workbooks, "
        "pipeline-reports, cpat, …)\n"
        "You MUST write real files (not chat-only summaries).\n"
        "CRITICAL — Cursor-like file edits (avoid rewrite loops):\n"
        "- Create with a short write_file skeleton (imports + main stubs).\n"
        "- Grow the file with append_file and/or str_replace (like Cursor Apply hunks).\n"
        "- Do NOT call write_file repeatedly on the same path with the full file.\n"
        "- When the generator is complete, run_python(script_path=...) once.\n"
        "CRITICAL — step budget (token cost):\n"
        "- Skip glossary/templates unless required for the deliverable.\n"
        "- At most one read_file or a few search_files on parsed/.\n"
        "- FORBIDDEN: run_python(code=...) to open/print parsed/*.md line ranges.\n"
        "- By step 3 you MUST start write_file under output/.\n"
        "- run_python only with script_path= after the .py exists on disk.\n"
        "CRITICAL — Docling already ran before you started:\n"
        "- Read document content ONLY from `parsed/*.md`.\n"
        "- NEVER pip install. NEVER open or parse `input/*.pdf` or `input/*.docx` with Python.\n"
        "- NEVER install pypdf / PyPDF2 / pdfminer / python-docx for extraction.\n"
        "- list_dir on input/ is OK to see names; content comes from parsed/.\n"
        "Use search_files to find existing schema/templates before rewriting.\n"
        f"{template_hint}"
        "When finished, briefly summarize files you created (paths).\n"
        f"{skills}"
    )


def _run_lab_single_shot(
    workspace: Path,
    sources: str,
    logs: list[str],
    flush_logs: callable,
    should_cancel: callable,
) -> str:
    """
    Lab single-shot: ONE LLM call returns the full generator script.
    We write it + requirements.txt, then run_python. No tool loop = no resending.
    Cost: ~1 LLM call (~20k input + ~4k output) instead of 21 calls.
    """
    logs.append("[lab-single-shot] generating workbook script in one call")
    flush_logs()

    system = (
        "You are a Python developer. Write a COMPLETE openpyxl script that creates "
        "an RHOSO Lab Requirements sizing workbook (.xlsx) from the document content below.\n"
        "Output ONLY the Python script — no explanations, no markdown fences.\n"
        "The script must:\n"
        "- import openpyxl, os\n"
        "- Create sheets for hardware, network, storage, and deployment sizing\n"
        "- Extract requirements from the document content provided\n"
        "- Save to output/lab-requirements/rhoso-18.0-lab-requirements.xlsx\n"
        "- Print a confirmation message on success\n"
    )
    user = (
        "Generate the complete Python script.\n\n"
        f"DOCUMENT CONTENT:\n{sources[:30000]}\n"
    )

    if should_cancel and should_cancel():
        return "cancelled"

    script_text = complete(system, user)
    logs.append("[lab-single-shot] got script, writing files")
    flush_logs()

    tools = WorkspaceTools(workspace)

    # Clean up markdown fences if model wrapped the code
    code = script_text.strip()
    if code.startswith("```"):
        first_newline = code.index("\n") if "\n" in code else 3
        code = code[first_newline + 1 :]
    if code.endswith("```"):
        code = code[:-3].rstrip()

    tools.write_file("output/lab-requirements/generate_lab_requirements_workbook.py", code)
    tools.write_file("output/lab-requirements/requirements.txt", "openpyxl\n")
    logs.append("[lab-single-shot] wrote generator + requirements.txt")
    flush_logs()

    if should_cancel and should_cancel():
        return "cancelled"

    result = tools.run_python(script_path="output/lab-requirements/generate_lab_requirements_workbook.py")
    logs.append(f"[lab-single-shot] run_python: {result.splitlines()[0][:120]}")
    flush_logs()

    if "exit=0" not in result and ("SyntaxError" in result or "truncat" in result.lower()):
        logs.append("[lab-single-shot] syntax/truncation error — regenerating shorter script")
        flush_logs()
        if should_cancel and should_cancel():
            return "cancelled"
        retry_system = (
            "You are a Python developer. Write a SHORTER, COMPLETE openpyxl script "
            "(under 100 lines) that creates an RHOSO lab requirements .xlsx. "
            "No markdown fences. Save to output/lab-requirements/rhoso-18.0-lab-requirements.xlsx.\n"
        )
        retry_text = complete(retry_system, f"DOCUMENT:\n{sources[:20000]}")
        retry_code = retry_text.strip()
        if retry_code.startswith("```"):
            retry_code = retry_code[retry_code.index("\n") + 1:] if "\n" in retry_code else retry_code[3:]
        if retry_code.endswith("```"):
            retry_code = retry_code[:-3].rstrip()
        tools._write_counts.pop("output/lab-requirements/generate_lab_requirements_workbook.py", None)
        tools.write_file("output/lab-requirements/generate_lab_requirements_workbook.py", retry_code)
        result = tools.run_python(script_path="output/lab-requirements/generate_lab_requirements_workbook.py")
        logs.append(f"[lab-single-shot] retry run_python: {result.splitlines()[0][:120]}")
        flush_logs()

    if "exit=0" in result:
        logs.append("[lab-single-shot] success — .xlsx generated")
    else:
        logs.append(f"[lab-single-shot] script error — may need tool-loop fallback")

    flush_logs()
    return f"Lab single-shot completed.\n\nScript output:\n{result[:2000]}"


def _rda_cpat_contract() -> str:
    """Hard CPAT CIQ contract for RDA single-shot (prevents storage-PDF drift)."""
    # Prefer agent rule from image/workspace so we stay aligned with colleague agents
    # without editing those files.
    rule_text = ""
    for candidate in (
        RULES_DIR / "agent-rhoso-da.md",
        AGENTS_DIR / ".cursor" / "rules" / "agent-rhoso-da.md",
    ):
        if candidate.is_file():
            try:
                rule_text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                rule_text = ""
            break
    # Keep prompt bounded — table contract is the critical part
    if "CIQ Schema v1.4" in rule_text:
        start = rule_text.find("## CIQ Schema v1.4")
        end = rule_text.find("## CIQ Workbook Structure", start)
        if start >= 0 and end > start:
            rule_text = rule_text[start:end]
        else:
            rule_text = rule_text[:12000]
    else:
        rule_text = rule_text[:12000]

    return (
        "CRITICAL — This is a CPAT deployment CIQ schema (NOT a Red Hat storage PDF schema).\n"
        "You MUST follow the CPAT v1.4 contract below. Do NOT invent categories like "
        "storage_general / block_storage_* / image_service_* from the PDF alone.\n"
        "SCHEMA_VERSION MUST be exactly \"1.4\" (X.Y format). NEVER use \"18.0.0\".\n"
        "RHOSO_PARAMETER_SCHEMA entries MUST use a `table` field with ONLY these tables:\n"
        "rhoso_details, rhoso_access, rhoso_disconnected, rhoso_storage, rhoso_ceph_storage, "
        "rhoso_trident_storage, rhoso_lso_storage, rhoso_control_plane, rhoso_services, "
        "rhoso_observability, rhoso_pv_sizing, rhoso_cinder_backend, rhoso_multipath, "
        "rhoso_neutron_config, rhoso_edpm_network_config, rhoso_data_plane.\n"
        "Also define RHOSO_NETWORK_FIELD_SCHEMA (rhoso_networks columns) and "
        "RHOSO_NODE_FIELD_SCHEMA (rhoso_data_plane_nodes columns).\n"
        "Use a `_param(...)` helper returning dicts with keys like: field, type, required, "
        "table, when, description (match CPAT style).\n"
        "Include at least 200 parameter entries across tables.\n"
        "Use uploaded documents only to fill descriptions / examples / defaults — "
        "NOT to redesign the table structure.\n\n"
        f"CPAT AGENT CONTRACT (from agent-rhoso-da.md):\n{rule_text}\n"
    )


def _strip_md_fence(text: str) -> str:
    code = (text or "").strip()
    if code.startswith("```"):
        code = code[code.index("\n") + 1 :] if "\n" in code else code[3:]
    if code.endswith("```"):
        code = code[:-3].rstrip()
    return code


def _run_rda_single_shot(
    workspace: Path,
    sources: str,
    logs: list[str],
    flush_logs: callable,
    should_cancel: callable,
    sub_stage: str = "",
) -> str:
    """
    RHOSO DA single-shot, optionally scoped to one sub-stage:
      Schema → CIQ schema only (RDA-1)
      Generator → workbook generator only (RDA-2)
      Workbooks → run generator → .xlsx + report (RDA-3)
      (empty) → full Schema + Generator + Workbooks (legacy single RDA)
    """
    tools = WorkspaceTools(workspace)
    cpat_contract = _rda_cpat_contract()
    # Normalize: "Schema", "RDA-1", "schema" → schema | generator | workbooks | ""
    raw = (sub_stage or "").strip().lower().replace("_", "-")
    _map = {
        "schema": "schema",
        "rda-1": "schema",
        "generator": "generator",
        "rda-2": "generator",
        "workbooks": "workbooks",
        "workbook": "workbooks",
        "rda-3": "workbooks",
    }
    want = _map.get(raw, raw if raw in {"schema", "generator", "workbooks"} else "")
    do_schema = want in {"", "schema"}
    do_generator = want in {"", "generator"}
    do_workbooks = want in {"", "workbooks"}
    # Scoped stages must NOT run the other phases
    if want == "schema":
        do_generator = do_workbooks = False
    elif want == "generator":
        do_schema = do_workbooks = False
    elif want == "workbooks":
        do_schema = do_generator = False
    schema_path = "output/ciq-generators/rhoso_ciq_schema.py"
    gen_path = "output/ciq-generators/generate_rhoso_ciq_workbooks.py"
    logs.append(f"[rda-single-shot] mode={want or 'full'} (sub_stage={sub_stage!r})")
    flush_logs()

    code = ""
    result = ""

    if do_schema:
        logs.append("[rda-single-shot] generating CIQ schema in one call (CPAT v1.4 contract)")
        flush_logs()
        if should_cancel and should_cancel():
            return "cancelled"

        schema_system = (
            "You are the RHOSO DA (Design Architect) for CPAT.\n"
            "Write a COMPLETE Python module rhoso_ciq_schema.py.\n"
            "Output ONLY the Python code — no explanations, no markdown fences.\n"
            "Required exports:\n"
            "- SCHEMA_VERSION = \"1.4\"\n"
            "- CIQ_TYPES (validators / type map used by CPAT)\n"
            "- RHOSO_PARAMETER_SCHEMA (list of dicts with table=rhoso_* names)\n"
            "- RHOSO_NETWORK_FIELD_SCHEMA\n"
            "- RHOSO_NODE_FIELD_SCHEMA\n"
            "- get_validation_schema()\n"
            f"\n{cpat_contract}\n"
        )
        schema_text = complete(
            schema_system,
            "Build the CPAT v1.4 CIQ schema. Documents below are supporting context only.\n\n"
            f"DOCUMENT:\n{sources[:30000]}\n",
        )
        code = _strip_md_fence(schema_text)
        drifted = (
            'SCHEMA_VERSION = "18.' in code
            or 'SCHEMA_VERSION: str = "18.' in code
            or "storage_general" in code
            or "block_storage_api" in code
            or "rhoso_details" not in code
        )
        if drifted:
            logs.append(
                "[rda-single-shot] schema drifted from CPAT v1.4 — regenerating with stricter prompt"
            )
            flush_logs()
            if should_cancel and should_cancel():
                return "cancelled"
            retry_system = (
                schema_system
                + "\nPREVIOUS OUTPUT WAS REJECTED because it used storage-PDF categories "
                "or SCHEMA_VERSION != 1.4.\n"
                "Regenerate with rhoso_details / rhoso_access / ... tables ONLY.\n"
            )
            schema_text = complete(
                retry_system,
                "CPAT v1.4 schema ONLY. Supporting docs:\n" + sources[:20000],
            )
            code = _strip_md_fence(schema_text)

        tools.write_file(schema_path, code)
        logs.append("[rda-single-shot] wrote CIQ schema")
        flush_logs()
        if want == "schema":
            return f"RDA-1 Schema complete.\n- `{schema_path}`\n"

    if do_generator:
        if should_cancel and should_cancel():
            return "cancelled"
        if not code:
            sp = workspace / schema_path
            if not sp.is_file():
                raise RuntimeError(
                    f"RDA-2 Generator requires {schema_path} (finish RDA-1 Schema first)"
                )
            code = sp.read_text(encoding="utf-8", errors="replace")

        logs.append("[rda-single-shot] generating workbook generator in one call")
        flush_logs()
        gen_system = (
            "You are a Python developer writing the CPAT CIQ workbook generator.\n"
            "Output ONLY the Python script — no explanations, no markdown fences.\n"
            "The script must:\n"
            "- import openpyxl, os, and symbols from rhoso_ciq_schema\n"
            "- Create EXACTLY these sheets (CPAT multi-sheet layout):\n"
            "  Versioning, Environment, Storage, Control Plane, Networks, Data Plane, "
            "values (hidden), Guidelines, Operators\n"
            "- Group tables: Environment=rhoso_details/access/disconnected; "
            "Storage=rhoso_storage/ceph/trident/lso/cinder/multipath; "
            "Control Plane=rhoso_control_plane/services/observability/pv_sizing/neutron; "
            "Networks=rhoso_networks; Data Plane=rhoso_edpm_network_config/data_plane + nodes\n"
            "- Create sample-rhoso.ciq.xlsx AND rhoso-ciq-template.xlsx\n"
            "- Save under output/ciq-workbooks/rhoso/\n"
            "- Print confirmation on success\n"
            "Do NOT create one sheet per storage_general/block_storage category.\n"
        )
        gen_text = complete(
            gen_system,
            f"CIQ SCHEMA:\n{code[:15000]}\n\n"
            f"DOCUMENT EXCERPT (for sample values only):\n{sources[:10000]}\n",
        )
        gen_code = _strip_md_fence(gen_text)
        tools.write_file(gen_path, gen_code)
        tools.write_file("output/ciq-generators/requirements.txt", "openpyxl\n")
        logs.append("[rda-single-shot] wrote workbook generator + requirements.txt")
        flush_logs()
        if want == "generator":
            return (
                "RDA-2 Generator complete.\n"
                f"- `{gen_path}`\n"
                "- `output/ciq-generators/requirements.txt`\n"
            )

    if do_workbooks:
        if should_cancel and should_cancel():
            return "cancelled"
        if not (workspace / gen_path).is_file():
            raise RuntimeError(
                f"RDA-3 Workbooks requires {gen_path} (finish RDA-2 Generator first)"
            )
        if not code:
            sp = workspace / schema_path
            if sp.is_file():
                code = sp.read_text(encoding="utf-8", errors="replace")

        result = tools.run_python(script_path=gen_path)
        first_line = result.splitlines()[0][:120] if result else "(no output)"
        logs.append(f"[rda-single-shot] run_python: {first_line}")

        if "exit=0" not in result and ("SyntaxError" in result or "truncat" in result.lower()):
            logs.append(
                "[rda-single-shot] syntax/truncation error — regenerating shorter generator"
            )
            flush_logs()
            if should_cancel and should_cancel():
                return "cancelled"
            gen_system_retry = (
                "You are a Python developer. The previous script was truncated. "
                "Write a SHORTER, COMPLETE openpyxl script that creates ONE RHOSO CIQ "
                "workbook (.xlsx). Keep it under 120 lines. No markdown fences.\n"
                "- import openpyxl, os\n"
                "- One sheet per CIQ category (use simple loops)\n"
                "- Save to output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx\n"
                "- Print confirmation\n"
            )
            retry_code = _strip_md_fence(
                complete(gen_system_retry, f"CIQ SCHEMA:\n{code[:12000]}\n")
            )
            tools._write_counts.pop(gen_path, None)
            tools.write_file(gen_path, retry_code)
            result = tools.run_python(script_path=gen_path)
            first_line = result.splitlines()[0][:120] if result else "(no output)"
            logs.append(f"[rda-single-shot] retry run_python: {first_line}")

        if "exit=0" in result:
            logs.append("[rda-single-shot] success — .xlsx generated")
        else:
            logs.append("[rda-single-shot] generator error — may need tool-loop retry")

        report_dir = workspace / "output" / "pipeline-reports" / "rda"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = (
            "# RDA — RHOSO DA Pipeline Report\n\n"
            "## Generated Files\n\n"
            f"- `{schema_path}` — CIQ parameter schema\n"
            f"- `{gen_path}` — Workbook generator\n"
            "- `output/ciq-generators/requirements.txt`\n"
            "- `output/ciq-workbooks/rhoso/*.xlsx` — Generated workbooks\n\n"
            f"## Generator Output\n\n```\n{result[:3000]}\n```\n"
        )
        (report_dir / "rda-report.md").write_text(report, encoding="utf-8")
        (report_dir / "ciq-parameter-reference.md").write_text(report, encoding="utf-8")
        logs.append(
            "[rda-single-shot] wrote pipeline-reports/rda/"
            "rda-report.md + ciq-parameter-reference.md"
        )
        flush_logs()
        if want == "workbooks":
            return f"RDA-3 Workbooks complete.\n\nGenerator output:\n{result[:2000]}\n"
        return f"RDA single-shot completed.\n\nGenerator output:\n{result[:2000]}\n\n{report}"

    return f"RDA single-shot ({want or 'full'}) finished."


def _parse_file_bundle(text: str) -> list[tuple[str, str]]:
    """
    Parse multi-file LLM output.

    Expected format (repeatable)::

        ### FILE: output/cpat/backend/app.py
        <file contents>
        ### FILE: output/cpat/backend/models.py
        <file contents>
    """
    body = (text or "").strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", body)
        if body.endswith("```"):
            body = body[:-3].rstrip()

    parts = re.split(r"(?m)^### FILE:\s*", body)
    files: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        nl = part.find("\n")
        if nl < 0:
            continue
        path = part[:nl].strip().strip("`").strip()
        content = part[nl + 1 :]
        if content.rstrip().endswith("```"):
            content = content.rstrip()
            if content.endswith("```"):
                content = content[:-3].rstrip() + "\n"
        if not path or ".." in Path(path).parts:
            continue
        if not path.startswith("output/"):
            if path.startswith("cpat/"):
                path = "output/" + path
            else:
                continue
        files.append((path, content if content.endswith("\n") else content + "\n"))
    return files


def _run_custom_single_shot(
    workspace: Path,
    *,
    agent_name: str,
    stage: dict,
    sources: str,
    previous: str,
    follow_block: str,
    cursor_prompt: str,
    logs: list[str],
    flush_logs: callable,
    should_cancel: callable,
) -> str:
    """Generic ### FILE bundle single-shot for custom pipeline stages."""
    tools = WorkspaceTools(workspace)
    stage_rule = str(stage.get("rule_file") or "")
    system = _system_for_agent(agent_name, tool_mode=False, rule_file=stage_rule)
    system += (
        "\n\n---\n# Single-shot file bundle mode\n"
        "Output ONLY a file bundle — no chat, no questions.\n"
        "For EACH file use exactly:\n\n"
        "### FILE: output/path/to/file.ext\n"
        "<complete file contents>\n\n"
        "Rules:\n"
        "- Paths MUST start with output/\n"
        "- Each file must be COMPLETE\n"
        "- Prefer several small files over one giant file\n"
    )
    user = (
        f"Stage: {stage.get('abbrev')} {agent_name}\n"
        f"Expected deliverables: {stage.get('output')}\n"
        f"{cursor_prompt}\n\n"
        f"{follow_block}"
        f"DOCUMENT CONTENT:\n{sources[:30000]}\n\n"
        f"Previous stage summary:\n{previous or '(none)'}\n"
    )
    label = str(stage.get("abbrev") or "custom")

    def _legacy() -> str:
        logs.append(f"[custom-single-shot] {label} — generating ### FILE bundle")
        flush_logs()
        if should_cancel and should_cancel():
            return "cancelled"
        files = _parse_file_bundle(complete(system, user))
        if not files:
            raise RuntimeError(
                f"custom single-shot {label}: no ### FILE blocks in model output"
            )
        written: list[str] = []
        for path, content in files:
            tools._write_counts.pop(path, None)
            tools.write_file(path, content)
            written.append(path)
        logs.append(f"[custom-single-shot] {label} wrote {len(written)} file(s)")
        flush_logs()
        listing = "\n".join(f"- `{p}`" for p in written)
        return f"Custom single-shot {label} wrote {len(written)} files:\n{listing}\n"

    if langgraph_enabled_for("custom") and langgraph_importable():
        try:
            return run_langgraph_single_shot(
                workspace=workspace,
                system=system,
                user=user,
                logs=logs,
                on_log=flush_logs,
                should_cancel=should_cancel,
                label=f"custom-{label}",
            )
        except AgentCancelled:
            raise
        except Exception as exc:
            logs.append(
                f"[langgraph] custom single-shot failed ({type(exc).__name__}) — legacy"
            )
            flush_logs()
            return _legacy()
    return _legacy()


def _list_cpat_paths(workspace: Path, limit: int = 80) -> str:
    root = workspace / "output" / "cpat"
    if not root.is_dir():
        return "(none yet)"
    paths = sorted(
        p.relative_to(workspace).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    )
    if not paths:
        return "(none yet)"
    lines = paths[:limit]
    if len(paths) > limit:
        lines.append(f"... ({len(paths)} total)")
    return "\n".join(lines)


def _run_rde_single_shot(
    workspace: Path,
    sub: dict[str, str],
    rda_context: str,
    logs: list[str],
    flush_logs: callable,
    should_cancel: callable,
) -> str:
    """
    Streaming one-shot per layer → parse ### FILE: blocks → write to disk.
    Agent rule + parsed PDF content are injected so the model adapts to
    the actual input documents (like Cursor's tool-loop reads them).
    Extra one-shots if the layer is still thin (Cursor continue).
    """
    name = sub["name"]
    tools = WorkspaceTools(workspace)
    prior_listing = _list_cpat_paths(workspace)

    # Load agent rule — full text, no truncation (Cursor agent reads the whole file)
    rule_body = ""
    rule_file = RULES_DIR / "agent-rhoso-deployment-engineer.md"
    if rule_file.is_file():
        rule_body = rule_file.read_text(encoding="utf-8")

    # Load context template — FULL text (this is the spec that lists every file,
    # component, template, and CIQ mapping). Truncating this is why the model
    # was generating wrong components and missing helpers.
    template_body = ""
    tmpl_file = AGENTS_DIR / "context" / "templates" / "rhoso-deployment-engineer.md"
    if not tmpl_file.is_file():
        tmpl_file = workspace / "context" / "templates" / "rhoso-deployment-engineer.md"
    if tmpl_file.is_file():
        template_body = tmpl_file.read_text(encoding="utf-8")

    def _one_call(extra_instruction: str = "") -> list[tuple[str, str]]:
        system = (
            "You are RHOSO Deployment Engineer generating CPAT source files.\n"
            "Output ONLY a file bundle — no chat, no markdown fences around the whole reply.\n"
            "For EACH file use exactly this format:\n\n"
            "### FILE: output/cpat/path/to/file.ext\n"
            "<complete file contents>\n\n"
            "### FILE: output/cpat/another/file.ext\n"
            "<complete file contents>\n\n"
            "Rules:\n"
            "- Paths MUST start with output/cpat/ (or output/pipeline-reports/rde/ for reports).\n"
            "- Generate ALL files the input documents and agent rule require — "
            "do not limit to a fixed count.\n"
            "- Each file must be COMPLETE and valid.\n"
            "- Prefer many small files over one giant file.\n"
            "- Do not invent tools or ask questions — only emit ### FILE blocks.\n"
        )
        if rule_body:
            system += f"\n\n---\n# Agent Rule\n{rule_body}\n"
        if template_body:
            system += f"\n\n---\n# Context Template\n{template_body}\n"

        # Load parsed PDF content so model can discover tasks from documents
        parsed_content = ""
        parsed_dir = workspace / "parsed"
        if parsed_dir.is_dir():
            for md in sorted(parsed_dir.iterdir()):
                if md.is_file() and md.suffix == ".md":
                    text = md.read_text(encoding="utf-8", errors="replace")
                    parsed_content += f"\n## {md.name}\n{text[:20000]}\n"
                    if len(parsed_content) > 60000:
                        break

        user = (
            f"{sub['prompt']}\n"
            f"{extra_instruction}\n\n"
            f"RDA / CIQ context:\n{rda_context[:20000]}\n\n"
            f"Files already on disk from earlier sub-stages:\n{prior_listing[:4000]}\n"
        )
        if parsed_content:
            user += f"\n\nParsed input documents (generate tasks/files based on this content):\n{parsed_content}\n"
        # LangGraph single-shot node (streaming complete) when enabled for rde
        if langgraph_enabled_for("rde") and langgraph_importable():
            try:
                return run_langgraph_complete_bundle(
                    system=system,
                    user=user,
                    logs=logs,
                    on_log=flush_logs,
                    should_cancel=should_cancel,
                    label=f"rde-{name}",
                )
            except AgentCancelled:
                raise
            except Exception as exc:
                logs.append(
                    f"[langgraph] rde-{name} bundle failed ({type(exc).__name__}) — "
                    "legacy complete()"
                )
                flush_logs()
        return _parse_file_bundle(complete(system, user))

    use_lg = langgraph_enabled_for("rde") and langgraph_importable()
    logs.append(
        f"[rde-single-shot] {name} — one-shot generation"
        + (" via langgraph" if use_lg else "")
    )
    flush_logs()
    if should_cancel and should_cancel():
        return "cancelled"

    # No MIN_FILES or SMOKE hard-gates — model decides completeness,
    # exactly like Cursor's tool loop where verify_paths only logs.
    written: list[str] = []

    # --- Pass 1: main generation ---
    files = _one_call()
    if not files:
        raise RuntimeError(f"RDE single-shot {name}: no ### FILE blocks in model output")
    for path, content in files:
        tools._write_counts.pop(path, None)
        tools.write_file(path, content)
        written.append(path)
    logs.append(f"[rde-single-shot] {name} wrote {len(files)} file(s)")
    flush_logs()

    # --- Self-check passes: model compares written files vs the spec ---
    # This is equivalent to Cursor's tool loop where the agent can read what
    # it wrote and decide whether to write more. We give it the file listing
    # and ask it to self-check against the agent rule.
    for attempt in range(1, RDE_LAYER_MAX_CALLS):
        if should_cancel and should_cancel():
            return "cancelled"
        updated_listing = _list_cpat_paths(workspace)
        hint = (
            f"SELF-CHECK — Review the {name} layer against the Agent Rule "
            f"(provided in the system prompt). Compare every file the spec "
            f"requires for sub_stage={name} with what exists on disk below.\n\n"
            f"Files currently on disk:\n{updated_listing[:6000]}\n\n"
            f"If ANY required files are missing, emit them now as ### FILE: blocks.\n"
            f"If the layer is COMPLETE (all spec'd files exist), output exactly:\n"
            f"LAYER_COMPLETE\n\n"
            f"Do NOT rewrite files that already exist."
        )
        logs.append(
            f"[rde-single-shot] {name} self-check {attempt}"
            + (" via langgraph" if use_lg else "")
        )
        flush_logs()
        more = _one_call(hint)
        if not more:
            logs.append(f"[rde-single-shot] {name} model reports COMPLETE")
            break
        for path, content in more:
            tools._write_counts.pop(path, None)
            tools.write_file(path, content)
            written.append(path)
        logs.append(f"[rde-single-shot] {name} +{len(more)} file(s)")
        flush_logs()
    flush_logs()

    listing = "\n".join(f"- `{p}`" for p in written)
    return f"RDE single-shot {name} wrote {len(written)} files:\n{listing}\n"

def _read_inputs(input_dir: Path, parsed_dir: Path | None = None) -> str:
    """Read text from parsed/ first (Docling output), then raw input/ for plain text."""
    chunks: list[str] = []
    seen_stems: set[str] = set()

    if parsed_dir and parsed_dir.is_dir():
        for path in sorted(parsed_dir.iterdir()):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            chunks.append(f"## {path.name} (parsed)\n{text[:TEXT_MAX]}\n")
            seen_stems.add(path.stem)

    if not input_dir.is_dir():
        return "\n".join(chunks) if chunks else "(no input directory)"

    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name == "meta.json":
            continue
        if path.stem in seen_stems:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        if sum(c == "\ufffd" for c in text) > 50 or "\x00" in text[:1000]:
            chunks.append(f"## {path.name}\n(binary file stored at {path})\n")
            continue
        chunks.append(f"## {path.name}\n{text[:TEXT_MAX]}\n")
    return "\n".join(chunks) if chunks else "(no files)"


def _link_or_copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    try:
        dest.symlink_to(src)
    except OSError:
        shutil.copy2(src, dest)


def _seed_golden_baseline(workspace: Path, logs: list[str], on_log: callable = None) -> bool:
    """Copy golden output into workspace so agents patch instead of generate from scratch.

    The golden baseline (cpat-main/output) is baked into the container image
    under AGENTS_DIR. If it exists, copy it into the workspace. This lets the
    RDE agent skip creating files that already match the golden reference —
    it only writes files that need changes based on the input documents.

    Returns True if baseline was seeded.
    """
    golden = AGENTS_DIR / "output"
    if not golden.is_dir():
        return False
    ws_output = workspace / "output"
    if (ws_output / "cpat").is_dir():
        logs.append("[baseline] output/cpat already exists — skipping seed")
        if on_log:
            on_log()
        return True
    ws_output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(golden, ws_output, dirs_exist_ok=True)
    n_files = sum(1 for _ in ws_output.rglob("*") if _.is_file())
    logs.append(f"[baseline] seeded {n_files} golden files into output/ (ENHANCE mode)")
    if on_log:
        on_log()
    return True


def _seed_workspace(
    workspace: Path,
    input_dir: Path,
    logs: list[str],
    on_log: callable | None = None,
) -> dict[str, int]:
    """Prepare Cursor-like workspace: input/, parsed/, context/, output/.

    Returns Docling parse stats ``{attempted, ok}``.
    """
    ws_input = workspace / "input"
    ws_parsed = workspace / "parsed"
    ws_output = workspace / "output"
    ws_context = workspace / "context"
    ws_input.mkdir(parents=True, exist_ok=True)
    ws_parsed.mkdir(parents=True, exist_ok=True)
    ws_output.mkdir(parents=True, exist_ok=True)

    if input_dir.is_dir():
        for path in sorted(input_dir.iterdir()):
            if not path.is_file() or path.name == "meta.json":
                continue
            _link_or_copy_file(path.resolve(), ws_input / path.name)
        logs.append(f"[workspace] linked inputs from {input_dir}")
        if on_log:
            on_log()

    # Seed context (templates, glossary, team-config) from image agents tree
    src_context = AGENTS_DIR / "context"
    if src_context.is_dir():
        if ws_context.exists():
            shutil.rmtree(ws_context)
        shutil.copytree(src_context, ws_context)
        logs.append("[workspace] seeded context/ from sprintweave-agents")
    else:
        ws_context.mkdir(parents=True, exist_ok=True)
        logs.append("[workspace] no agents context/ in image — empty context/")
    if on_log:
        on_log()

    # Seed Cursor skills into workspace
    ws_skills = workspace / ".cursor" / "skills"
    if SKILLS_DIR.is_dir():
        if ws_skills.exists():
            shutil.rmtree(ws_skills)
        shutil.copytree(SKILLS_DIR, ws_skills)
        n = len(list(ws_skills.glob("*/SKILL.md")))
        logs.append(f"[workspace] seeded .cursor/skills/ ({n} skills)")
    else:
        ws_skills.mkdir(parents=True, exist_ok=True)
        logs.append("[workspace] no .cursor/skills in image")
    if on_log:
        on_log()

    return _parse_inputs(ws_input, ws_parsed, logs, on_log=on_log)


def _sync_workspace_output(workspace: Path, output_dir: Path) -> None:
    """Mirror workspace/output into job output/ for API downloads."""
    src = workspace / "output"
    if not src.is_dir():
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        dest = output_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def _list_generated(workspace: Path, limit: int = 80) -> list[str]:
    out = workspace / "output"
    if not out.is_dir():
        return []
    files = [p.relative_to(workspace).as_posix() for p in sorted(out.rglob("*")) if p.is_file()]
    return files[:limit]


def _stage_summary(agent_name: str, abbrev: str, final_text: str, files: list[str]) -> str:
    listing = "\n".join(f"- `{f}`" for f in files) or "- (no files under output/ yet)"
    return (
        f"# {abbrev} {agent_name}\n\n"
        f"## Agent summary\n\n{final_text.strip() or '(no text)'}\n\n"
        f"## Generated files\n\n{listing}\n"
    )


def _rda_soft_ok(workspace: Path) -> bool:
    out = workspace / "output"
    has_schema = any(out.rglob("*rhoso_ciq_schema.py"))
    has_gen = (
        any(out.rglob("generate*rhoso*ciq*.py"))
        or any(out.rglob("generate_rhoso_ciq_workbooks.py"))
        or any(out.rglob("generate_lab_requirements*.py"))
    )
    has_xlsx = any(out.rglob("*.xlsx"))
    has_lab = (out / "lab-requirements").is_dir() and any(
        (out / "lab-requirements").rglob("*")
    )
    has_report = any((out / "pipeline-reports" / "rda").rglob("*.md")) if (
        out / "pipeline-reports" / "rda"
    ).exists() else False
    return bool(has_schema or has_gen or has_xlsx or has_lab or has_report)


def _rde_soft_ok(workspace: Path) -> bool:
    cpat = workspace / "output" / "cpat"
    if not cpat.is_dir():
        return any((workspace / "output" / "pipeline-reports" / "rde").rglob("*"))
    return any(cpat.rglob("*"))


def _finish_job(job: dict, output_dir: Path, combined: list[str], logs: list[str]) -> None:
    summary = output_dir / "summary.md"
    summary.write_text("\n".join(combined), encoding="utf-8")
    job["artifact_md"] = summary.read_text(encoding="utf-8")
    job["current_index"] = len(job["stages"])
    job["status"] = "succeeded"
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)
    _close_stage_timing(job)
    now = _utc_iso()
    job["finished_at"] = now
    job["updated_at"] = now
    started = job.get("started_at")
    try:
        start = datetime.strptime(started or "", "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        job["duration_s"] = int((_utc_now() - start).total_seconds())
        job["duration"] = _fmt_duration(job["duration_s"])
    except ValueError:
        pass
    logs.append(f"[done] files written under {output_dir}")
    job["logs"] = [_stamp_log(x) for x in logs]
    save_job(job)


def apply_gate_edit(job: dict, data_root: Path, edited_text: str) -> None:
    """Rewrite the gated stage artifact and update chain context."""
    idx = int(job["gate_stage_index"])
    stage = job["stages"][idx]
    output_dir = data_root / "jobs" / job["id"] / "output"
    out_file = output_dir / f"{stage['abbrev']}.md"
    out_file.write_text(edited_text, encoding="utf-8")
    job["previous"] = edited_text
    job["pending_artifact"] = edited_text
    combined = list(job.get("_combined") or [])
    header = f"# {stage['abbrev']} {stage['agent']}\n\n"
    entry = f"{header}{edited_text}\n"
    if idx < len(combined):
        combined[idx] = entry
    else:
        combined.append(entry)
    job["_combined"] = combined
    logs = list(job.get("logs") or [])
    logs.append(f"[edited] {stage['abbrev']} artifact updated before approval")
    job["logs"] = logs


def approve_and_continue(
    job: dict,
    data_root: Path,
    edited_text: str | None = None,
    follow_up: str = "",
) -> None:
    """Leave awaiting_approval and either finish or resume the next stage."""
    if job.get("status") != "awaiting_approval":
        raise ValueError("job is not awaiting approval")
    if edited_text is not None:
        apply_gate_edit(job, data_root, edited_text)

    idx = int(job["gate_stage_index"])
    next_index = idx + 1
    stages = job["stages"]
    output_dir = data_root / "jobs" / job["id"] / "output"
    logs = list(job.get("logs") or [])
    combined = list(job.get("_combined") or [])

    follow = (follow_up or "").strip()
    if follow:
        job["follow_up"] = follow
        logs.append(f"[follow-up] queued for next stage ({len(follow)} chars)")
    else:
        job.pop("follow_up", None)

    logs.append(f"[approved] {job.get('gate_abbrev', stages[idx]['abbrev'])} — continuing")
    job["logs"] = list(logs)
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)

    if next_index >= len(stages):
        _finish_job(job, output_dir, combined, logs)
        return

    job["status"] = "queued"
    logs.append("[queued] waiting for worker")
    job["logs"] = list(logs)
    start_job_thread(job, data_root, start_index=next_index)


def reject_job(job: dict, reason: str = "") -> None:
    if job.get("status") != "awaiting_approval":
        raise ValueError("job is not awaiting approval")
    logs = list(job.get("logs") or [])
    detail = reason.strip() or "no reason given"
    logs.append(f"[rejected] {job.get('gate_abbrev', '?')}: {detail}")
    job["status"] = "rejected"
    job["logs"] = logs
    job.pop("pending_artifact", None)


def skip_and_continue(
    job: dict,
    data_root: Path,
    *,
    skip_rest: bool = False,
) -> None:
    """
    At a gate: skip the current agent and continue.
    If skip_rest=True, mark all remaining stages skipped and finish the job.
    """
    if job.get("status") != "awaiting_approval":
        raise ValueError("job is not awaiting approval")

    idx = int(job["gate_stage_index"])
    stages = job["stages"]
    output_dir = data_root / "jobs" / job["id"] / "output"
    logs = list(job.get("logs") or [])
    combined = list(job.get("_combined") or [])
    abbrev = job.get("gate_abbrev") or stages[idx].get("abbrev", "?")
    agent = stages[idx].get("agent", "")

    skip_note = (
        f"# {abbrev} {agent}\n\n"
        f"(Skipped by user at gate — no further work for this stage.)\n"
    )
    out_file = output_dir / f"{abbrev}.md"
    out_file.write_text(skip_note, encoding="utf-8")
    entry = skip_note
    if idx < len(combined):
        combined[idx] = entry
    else:
        combined.append(entry)
    job["_combined"] = combined
    job["previous"] = job.get("previous") or skip_note

    logs.append(f"[skip] {abbrev} {agent} — skipped by user")
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)
    job.pop("follow_up", None)
    _close_stage_timing(job)

    if skip_rest:
        for j in range(idx + 1, len(stages)):
            s = stages[j]
            sab = s.get("abbrev", f"S{j}")
            note = (
                f"# {sab} {s.get('agent', '')}\n\n"
                f"(Skipped by user — remaining stages skipped.)\n"
            )
            (output_dir / f"{sab}.md").write_text(note, encoding="utf-8")
            if j < len(combined):
                combined[j] = note
            else:
                combined.append(note)
            logs.append(f"[skip] {sab} {s.get('agent', '')} — remaining skipped")
        job["_combined"] = combined
        job["logs"] = logs
        _finish_job(job, output_dir, combined, logs)
        return

    next_index = idx + 1
    if next_index >= len(stages):
        job["logs"] = logs
        _finish_job(job, output_dir, combined, logs)
        return

    job["status"] = "queued"
    job["current_index"] = next_index
    logs.append("[queued] waiting for worker")
    job["logs"] = logs
    save_job(job)
    start_job_thread(job, data_root, start_index=next_index)


def resume_job_from_stage(
    job: dict,
    data_root: Path,
    stage_abbrev: str = "RDE",
) -> None:
    """
    Resume a finished/rejected job from a stage (e.g. RDE) without re-running
    Docling or earlier stages. Reuses workspace/parsed + prior stage outputs.
    """
    status = job.get("status")
    if status in {"queued", "running"}:
        raise ValueError(f"job is already {status}")
    stages = job.get("stages") or []
    if not stages:
        raise ValueError("job has no stages")

    want = (stage_abbrev or "RDE").strip().upper()
    start_index = next(
        (i for i, s in enumerate(stages) if str(s.get("abbrev", "")).upper() == want),
        None,
    )
    if start_index is None:
        raise ValueError(f"stage '{stage_abbrev}' not found in pipeline")

    job_dir = data_root / "jobs" / job["id"]
    workspace = Path(job.get("workspace_path") or (job_dir / "workspace"))
    output_dir = Path(job.get("output_path") or (job_dir / "output"))
    parsed = workspace / "parsed"
    if not parsed.is_dir() or not any(parsed.glob("*.md")):
        raise ValueError(
            "no parsed/*.md in workspace — cannot skip Docling; start a new job"
        )

    previous = ""
    if start_index == 0:
        # Resume from first stage — Docling already done
        previous = ""
    else:
        prior = stages[start_index - 1]
        prior_md = output_dir / f"{prior.get('abbrev', 'RDA')}.md"
        if prior_md.is_file():
            previous = prior_md.read_text(encoding="utf-8", errors="replace")
        elif job.get("previous"):
            previous = str(job.get("previous") or "")
        if not previous.strip():
            raise ValueError(
                f"missing prior stage output ({prior_md.name}) — "
                "finish/approve earlier stage first, or resume from that stage"
            )

    logs = list(job.get("logs") or [])
    logs.append(
        f"[resume] starting from {want} (index {start_index}) — "
        "skipping Docling and earlier stages"
    )
    job["logs"] = logs
    job["previous"] = previous
    job["_sources"] = _read_inputs(workspace / "input", parsed)
    job["_combined"] = list(job.get("_combined") or [])
    job["cancel_requested"] = False
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)
    job["status"] = "queued"
    job["current_index"] = start_index
    logs.append("[queued] waiting for worker")
    job["logs"] = logs
    save_job(job)
    start_job_thread(job, data_root, start_index=start_index)


def cancel_job(job: dict) -> None:
    """Request stop (like Cursor Stop). Worker halts between LLM/tool steps."""
    status = job.get("status")
    if status not in {"queued", "running", "awaiting_approval"}:
        raise ValueError(f"job cannot be cancelled from status={status}")
    if job.get("status") == "cancelled":
        return
    job["cancel_requested"] = True
    logs = list(job.get("logs") or [])
    logs.append(
        "[cancel] stop requested — halting after the current LLM/tool step "
        "(in-flight model call may finish first)"
    )
    job["logs"] = logs
    # No active agent loop yet (or paused at gate): finish cancel immediately
    if status in {"queued", "awaiting_approval"}:
        job["status"] = "cancelled"
        logs.append("[cancelled] stopped by user")
        job["logs"] = logs
        job.pop("pending_artifact", None)
        job.pop("gate_stage_index", None)
        job.pop("gate_abbrev", None)


def _mark_cancelled(
    job: dict,
    logs: list[str],
    *,
    workspace: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    if workspace is not None and output_dir is not None:
        _sync_workspace_output(workspace, output_dir)
        job["artifacts"] = _list_generated(workspace, limit=200)
    logs.append("[cancelled] stopped by user")
    job["status"] = "cancelled"
    _close_stage_timing(job)
    now = _utc_iso()
    job["finished_at"] = now
    job["updated_at"] = now
    job["logs"] = [_stamp_log(x) for x in logs]
    save_job(job)
    job.pop("pending_artifact", None)
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)


def run_job(job: dict, data_root: Path, start_index: int = 0) -> None:
    job_id = job["id"]
    job_dir = data_root / "jobs" / job_id
    # Prefer shared input set on PVC (/data/inputs/<input_id>); fall back to job-local.
    if job.get("input_path"):
        input_dir = Path(job["input_path"])
    elif job.get("input_id"):
        input_dir = data_root / "inputs" / str(job["input_id"])
    else:
        input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    workspace = job_dir / "workspace"
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    # Honour cancel that landed while still queued
    if job.get("cancel_requested") or job.get("status") == "cancelled":
        logs0 = list(job.get("logs") or [])
        if job.get("status") != "cancelled":
            _mark_cancelled(job, logs0, workspace=workspace, output_dir=output_dir)
        return

    job["status"] = "running"
    job["started_at"] = job.get("started_at") or _utc_iso()
    job["updated_at"] = _utc_iso()
    job["input_path"] = str(input_dir)
    job["output_path"] = str(output_dir)
    job["workspace_path"] = str(workspace)

    stages = job["stages"]

    def flush_logs(logs: list[str]) -> None:
        logs[:] = [_stamp_log(x) for x in logs]
        job["logs"] = list(logs)
        job["updated_at"] = _utc_iso()
        save_job(job)

    def cancelled() -> bool:
        return bool(job.get("cancel_requested"))

    if start_index == 0:
        logs: list[str] = []
        combined: list[str] = []
        parse_stats = _seed_workspace(
            workspace, input_dir, logs, on_log=lambda: flush_logs(logs)
        )
        # Golden baseline available but disabled — enable by uncommenting:
        # _seed_golden_baseline(workspace, logs, on_log=lambda: flush_logs(logs))
        flush_logs(logs)
        if cancelled():
            _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
            return
        # Docling-only: abort before LLM if PDF/DOCX inputs produced no parsed/*.md
        require_parse = os.environ.get(
            "SPRINTWEAVE_REQUIRE_PARSED", "true"
        ).strip().lower() in {"1", "true", "yes"}
        attempted = int(parse_stats.get("attempted") or 0)
        ok = int(parse_stats.get("ok") or 0)
        parsed_n = _count_parsed_md(workspace / "parsed")
        if require_parse and attempted > 0 and (ok == 0 or parsed_n == 0):
            job["status"] = "failed"
            logs.append(
                f"[failed] Docling produced no parsed files "
                f"(attempted={attempted}, ok={ok}, parsed_md={parsed_n}). "
                "Fix Docling cache permissions / emptyDir mount; not starting LLM."
            )
            flush_logs(logs)
            return
        if attempted == 0 and USE_DOCLING:
            logs.append(
                "[warn] no PDF/DOCX/PPT inputs to parse — continuing with plain text inputs only"
            )
            flush_logs(logs)
        sources = _read_inputs(workspace / "input", workspace / "parsed")
        previous = ""
        job["_sources"] = sources
        job["_combined"] = combined
        job["previous"] = previous
    else:
        logs = list(job.get("logs") or [])
        combined = list(job.get("_combined") or [])
        sources = job.get("_sources") or _read_inputs(
            workspace / "input", workspace / "parsed"
        )
        previous = job.get("previous") or ""
        if logs and logs[-1].startswith("[queued]"):
            logs.pop()
            flush_logs(logs)

    try:
        for index in range(start_index, len(stages)):
            if cancelled():
                _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
                return

            job["current_index"] = index
            stage = stages[index]
            agent_name = stage["agent"]

            # Skip optional stages unless explicitly requested
            if stage.get("optional"):
                logs.append(f"[skip] {stage['abbrev']} {agent_name} — optional (skipped)")
                flush_logs(logs)
                continue

            logs.append(f"[running] {stage['abbrev']} {agent_name} — {stage['output']}")
            _close_stage_timing(job)
            job["stage_timings"] = list(job.get("stage_timings") or []) + [
                {
                    "abbrev": stage["abbrev"],
                    "agent": agent_name,
                    "started_at": _utc_iso(),
                    "finished_at": None,
                    "duration_s": None,
                    "duration": "",
                }
            ]
            flush_logs(logs)

            follow_up = (job.pop("follow_up", None) or "").strip()
            follow_block = (
                f"Follow-up prompt from reviewer (apply to this stage):\n{follow_up}\n\n"
                if follow_up
                else ""
            )
            running_log_idx = len(logs) - 1
            if follow_up:
                logs.append(f"[follow-up] applied to {stage['abbrev']}")
                flush_logs(logs)

            stage_rule = str(stage.get("rule_file") or "")
            # Per-stage mode (custom pipelines set tool_loop explicitly).
            # Do NOT force tool_loop just because stage.custom is true —
            # single_shot custom stages must use ### FILE bundles.
            if "tool_loop" in stage:
                use_tools = bool(stage.get("tool_loop"))
            else:
                use_tools = agent_name in TOOL_AGENTS
            mode_label = "tool_loop" if use_tools else "single_shot"
            if stage.get("custom") or stage_rule:
                logs.append(
                    f"[mode] {stage['abbrev']} → {mode_label}"
                    + (f" (rule={stage_rule})" if stage_rule else "")
                )
                flush_logs(logs)
            if use_tools:
                system = _system_for_agent(
                    agent_name, tool_mode=True, rule_file=stage_rule
                )
                summaries: list[str] = []
                if agent_name == "RHOSO Deployment Engineer":
                    # RDE needs RDA output + prior cpat files — not raw PDFs.
                    rde_context = previous[:15000] if previous else "(none)"
                    rde_subs = _filter_de_sub_stages(RDE_SUB_STAGES, stage)
                    if len(rde_subs) < len(RDE_SUB_STAGES):
                        logs.append(
                            f"[rde-pass] filtered to {[s.get('abbrev') for s in rde_subs]} "
                            f"(stage={stage.get('abbrev')})"
                        )
                        flush_logs(logs)
                    for sub in rde_subs:
                        if cancelled():
                            _mark_cancelled(
                                job, logs, workspace=workspace, output_dir=output_dir
                            )
                            return
                        logs.append(f"[rde-pass] {sub['name']} — starting")
                        flush_logs(logs)
                        golden = sub.get("golden_templates") or []
                        if golden:
                            _seed_golden_templates(workspace, golden, logs)
                        flush_logs(logs)
                        part = ""
                        used_single = False
                        force_tool_loop = sub.get("tool_loop", False)
                        if RDE_SINGLE_SHOT and not force_tool_loop:
                            try:
                                part = _run_rde_single_shot(
                                    workspace=workspace,
                                    sub=sub,
                                    rda_context=rde_context,
                                    logs=logs,
                                    flush_logs=lambda: flush_logs(logs),
                                    should_cancel=cancelled,
                                )
                                used_single = True
                            except Exception as ss_exc:
                                logs.append(
                                    f"[rde-single-shot] {sub['name']} failed "
                                    f"({type(ss_exc).__name__}) — falling back to tool loop"
                                )
                                flush_logs(logs)
                        elif force_tool_loop:
                            logs.append(
                                f"[rde-pass] {sub['name']} — using Cursor-like tool loop "
                                "(too many files for single-shot)"
                            )
                            flush_logs(logs)
                        if not used_single:
                            if force_tool_loop and sub.get("name") == "Ansible":
                                # Until-complete: keep rounds until all required
                                # files exist (or ANSIBLE_MAX_ROUNDS safety cap).
                                parts: list[str] = []
                                prev_missing_n = None
                                stall = 0
                                for round_i in range(1, ANSIBLE_MAX_ROUNDS + 1):
                                    if cancelled():
                                        _mark_cancelled(
                                            job,
                                            logs,
                                            workspace=workspace,
                                            output_dir=output_dir,
                                        )
                                        return
                                    missing = _ansible_missing(workspace)
                                    if round_i > 1 and not missing:
                                        break
                                    if round_i == 1 and not missing:
                                        # Fresh workspace — still need first gen
                                        pass
                                    elif round_i > 1 and missing:
                                        if prev_missing_n is not None and len(missing) >= prev_missing_n:
                                            stall += 1
                                        else:
                                            stall = 0
                                        if stall >= 3:
                                            logs.append(
                                                "[ansible-gate] stopping — missing "
                                                "count not decreasing (3 stalled rounds)"
                                            )
                                            flush_logs(logs)
                                            break

                                    # If ansible already partially exists (resume /
                                    # fill-in), use inventory continue prompt even on
                                    # round 1 — otherwise the model burns all steps
                                    # re-reading files (list_dir/read_file) before
                                    # writing anything.
                                    _root = workspace / "output" / "cpat" / "ansible"
                                    _td = (
                                        _root
                                        / "playbooks"
                                        / "roles"
                                        / "rhoso"
                                        / "templates"
                                    )
                                    _tk = (
                                        _root
                                        / "playbooks"
                                        / "roles"
                                        / "rhoso"
                                        / "tasks"
                                    )
                                    _ld = _root / "library"
                                    _existing_j2 = (
                                        sorted(p.name for p in _td.glob("*.j2"))
                                        if _td.is_dir()
                                        else []
                                    )
                                    _existing_tasks = (
                                        sorted(
                                            str(p.relative_to(_tk).as_posix())
                                            for p in _tk.rglob("*.yml")
                                            if p.is_file()
                                        )
                                        if _tk.is_dir()
                                        else []
                                    )
                                    _existing_lib = (
                                        sorted(p.name for p in _ld.glob("*.py"))
                                        if _ld.is_dir()
                                        else []
                                    )
                                    partial_exists = bool(
                                        _existing_j2 or _existing_tasks or _existing_lib
                                    )
                                    use_fill_in = (
                                        round_i > 1 or (round_i == 1 and partial_exists)
                                    )

                                    if not use_fill_in:
                                        logs.append(
                                            f"[ansible-gate] round {round_i}/"
                                            f"{ANSIBLE_MAX_ROUNDS} — initial generation "
                                            f"({ANSIBLE_ROUND_STEPS} steps)"
                                        )
                                        flush_logs(logs)
                                        user = (
                                            f"Stage: {stage['abbrev']} {agent_name}\n"
                                            f"{sub['prompt']}\n"
                                            f"Expected overall deliverables: "
                                            f"{stage.get('output', '')}\n"
                                            f"Input set id: "
                                            f"{job.get('input_id') or '(none)'}\n"
                                            f"{_format_cursor_prompt(job)}\n\n"
                                            f"{follow_block}"
                                            "Workspace: input/, parsed/, context/, "
                                            ".cursor/skills/, output/.\n"
                                            "RDA already produced the CIQ schema "
                                            "(summary below).\n"
                                            "Write ONLY this sub-stage's files. "
                                            "Prefer many small files.\n"
                                            "Edit like Cursor: write_file → "
                                            "append_file/str_replace.\n"
                                            "FORBIDDEN: run_python(code=...), "
                                            "list_dir/read_file on output/cpat/ansible "
                                            "(nothing is there yet — WRITE first).\n"
                                            "Follow the RHOSO DE agent rule for the "
                                            "complete Ansible set (task tree, ≈19 Jinja "
                                            "templates named in the rule, library "
                                            "modules, module_utils schema). "
                                            "Do not invent a short template list — "
                                            "match the rule.\n"
                                            "By step 2 you MUST call write_file.\n\n"
                                            f"RDA stage output (CIQ schema/analysis):\n"
                                            f"{rde_context}\n\n"
                                        )
                                    else:
                                        if round_i > 1:
                                            prev_missing_n = len(missing)
                                        miss_list = "\n".join(
                                            f"- {m}" for m in missing[:50]
                                        )
                                        mode = (
                                            "fill-in"
                                            if round_i == 1
                                            else "continue"
                                        )
                                        logs.append(
                                            f"[ansible-gate] round {round_i}/"
                                            f"{ANSIBLE_MAX_ROUNDS} — {mode}: "
                                            f"{len(missing)} gap(s); "
                                            f"have tmpl={len(_existing_j2)} "
                                            f"tasks={len(_existing_tasks)} "
                                            f"lib={len(_existing_lib)}"
                                        )
                                        flush_logs(logs)
                                        inventory = (
                                            f"ALREADY WRITTEN — do NOT re-read or "
                                            f"re-create:\n"
                                            f"  templates ({len(_existing_j2)}): "
                                            f"{', '.join(_existing_j2)}\n"
                                            f"  tasks ({len(_existing_tasks)}): "
                                            f"{', '.join(_existing_tasks[:30])}\n"
                                            f"  library ({len(_existing_lib)}): "
                                            f"{', '.join(_existing_lib)}\n"
                                        )
                                        user = (
                                            "CONTINUE — STOP EXPLORING. Write ONLY "
                                            "the missing items below.\n"
                                            "FORBIDDEN: list_dir, search_files, "
                                            "run_python, reading parsed/, re-reading "
                                            "files that already exist.\n"
                                            "REQUIRED: write_file / append_file "
                                            "starting THIS step.\n"
                                            "Paths MUST be playbooks/roles/rhoso/ "
                                            "and playbooks/main.yml — never "
                                            "rhoso_deployment or site.yml.\n\n"
                                            f"{inventory}\n"
                                            f"MISSING ({len(missing)}):\n"
                                            f"{miss_list}\n\n"
                                            "Consult the RHOSO DE agent rule for the "
                                            "complete file list. Write 3-4 files per "
                                            "step until everything above is done.\n"
                                        )

                                    parts.append(
                                        run_tool_agent(
                                            workspace=workspace,
                                            system=system,
                                            user=user,
                                            logs=logs,
                                            on_log=lambda: flush_logs(logs),
                                            should_cancel=cancelled,
                                            max_steps=ANSIBLE_ROUND_STEPS,
                                            scope="ansible",
                                            write_only=use_fill_in,
                                        )
                                    )
                                    _ensure_ansible_schema_copy(workspace, logs)
                                    _sync_workspace_output(workspace, output_dir)

                                    missing_after = _ansible_missing(workspace)
                                    if not missing_after:
                                        logs.append(
                                            f"[ansible-gate] COMPLETE after round "
                                            f"{round_i}/{ANSIBLE_MAX_ROUNDS}"
                                        )
                                        flush_logs(logs)
                                        break
                                    prev_missing_n = len(missing_after)
                                else:
                                    still = _ansible_missing(workspace)
                                    logs.append(
                                        f"[ansible-gate] WARN hit max rounds "
                                        f"({ANSIBLE_MAX_ROUNDS}); still missing "
                                        f"{len(still)} file(s)"
                                    )
                                    flush_logs(logs)

                                # Cursor parity: validate → repair passes (up to 2)
                                ok_v, report = _validate_ansible_layer(workspace)
                                logs.append(
                                    f"[ansible-validate] "
                                    f"{'PASS' if ok_v else 'FAIL'}"
                                )
                                for ln in report.splitlines()[:40]:
                                    logs.append(f"[ansible-validate] {ln}")
                                flush_logs(logs)
                                repair_attempts = 0
                                max_repair = 2
                                while not ok_v and ANSIBLE_REPAIR and repair_attempts < max_repair:
                                    repair_attempts += 1
                                    logs.append(
                                        f"[ansible-repair] attempt {repair_attempts}/{max_repair}"
                                    )
                                    flush_logs(logs)
                                    try:
                                        parts.append(
                                            _ansible_repair_pass(
                                                workspace=workspace,
                                                system=system,
                                                report=report,
                                                logs=logs,
                                                flush_logs=lambda: flush_logs(logs),
                                                should_cancel=cancelled,
                                            )
                                        )
                                        _ensure_ansible_schema_copy(workspace, logs)
                                        _sync_workspace_output(workspace, output_dir)
                                        ok_v, report = _validate_ansible_layer(
                                            workspace
                                        )
                                        logs.append(
                                            f"[ansible-validate-post-repair-{repair_attempts}] "
                                            f"{'PASS' if ok_v else 'FAIL'}"
                                        )
                                        for ln in report.splitlines()[:30]:
                                            logs.append(
                                                f"[ansible-validate-post-repair-{repair_attempts}] {ln}"
                                            )
                                        flush_logs(logs)
                                    except Exception as repair_exc:
                                        logs.append(
                                            f"[ansible-repair] attempt {repair_attempts} FAILED "
                                            f"({type(repair_exc).__name__}: "
                                            f"{repair_exc})"
                                        )
                                        flush_logs(logs)
                                        break
                                part = "\n".join(parts)
                            else:
                                user = (
                                    f"Stage: {stage['abbrev']} {agent_name}\n"
                                    f"{sub['prompt']}\n"
                                    f"Expected overall deliverables: "
                                    f"{stage.get('output', '')}\n"
                                f"Input set id: {job.get('input_id') or '(none)'}\n"
                                f"{_format_cursor_prompt(job)}\n\n"
                                f"{follow_block}"
                                    "Workspace: input/, parsed/, context/, "
                                    ".cursor/skills/, output/.\n"
                                    "RDA already produced the CIQ schema "
                                    "(summary below).\n"
                                    "Write ONLY this sub-stage's files. "
                                    "Prefer many small files.\n"
                                    "Edit like Cursor: write_file → "
                                    "append_file/str_replace.\n"
                                    "FORBIDDEN: run_python(code=...), "
                                    "exploring parsed/.\n\n"
                                    f"RDA stage output (CIQ schema/analysis):\n"
                                    f"{rde_context}\n\n"
                            )
                            part = run_agent_loop(
                                workspace=workspace,
                                system=system,
                                user=user,
                                logs=logs,
                                on_log=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                            )
                        # Cursor run_pipeline.verify_outputs — same verify_paths
                        vp = list(sub.get("verify_paths") or [])
                        if vp:
                            vp_found, vp_miss = [], []
                            for rel in vp:
                                p = workspace / rel
                                if p.is_file() and p.stat().st_size > 0:
                                    vp_found.append(rel)
                                else:
                                    vp_miss.append(rel)
                            status = "OK" if not vp_miss else "WARN"
                            logs.append(
                                f"[verify_paths] {sub.get('abbrev', sub['name'])} "
                                f"{status} — {len(vp_found)} verified, "
                                f"{len(vp_miss)} missing"
                            )
                            for m in vp_miss:
                                logs.append(f"[verify_paths] MISSING: {m}")
                            flush_logs(logs)
                        summaries.append(f"### RDE-{sub['name']}\n\n{part}\n")
                        _sync_workspace_output(workspace, output_dir)

                        # ── Cursor-style validate→fix loop per layer ──
                        # Run real validators on the just-generated layer.
                        # If errors, feed them to the LLM and re-validate.
                        _LAYER_MAP = {
                            "Backend": "backend",
                            "Frontend": "frontend",
                            "Docker": "docker",
                        }
                        _layer = _LAYER_MAP.get(sub["name"])
                        if _layer:
                            logs.append(
                                f"[validate-fix] running {_layer} validators..."
                            )
                            flush_logs(logs)
                            _remaining = _cpat_validate_and_fix(
                                workspace=workspace,
                                layer=_layer,
                                system=system,
                                logs=logs,
                                flush_logs=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                            )
                            if _remaining:
                                summaries.append(
                                    f"### RDE-{sub['name']}-Validation\n\n"
                                    f"⚠ {len(_remaining)} issue(s) remain "
                                    f"after fix rounds:\n"
                                    + "\n".join(
                                        f"- {e}" for e in _remaining[:10]
                                    )
                                    + "\n"
                                )
                            _sync_workspace_output(workspace, output_dir)

                        # Re-seed goldens after LLM so placeholder logo SVGs
                        # cannot stick if the model overwrote them.
                        if golden:
                            _seed_golden_templates(workspace, golden, logs)
                            _sync_workspace_output(workspace, output_dir)

                        logs.append(f"[rde-pass] {sub['name']} — done")
                        flush_logs(logs)
                        follow_block = ""

                    # ── Final cross-layer validation (diagnostic only) ──
                    cpat = workspace / "output" / "cpat"
                    final_errors = _run_cpat_validators(cpat)
                    if final_errors:
                        logs.append(
                            f"[validate-final] {len(final_errors)} issue(s) "
                            "across all layers:"
                        )
                        for e in final_errors[:15]:
                            logs.append(f"[validate-final]   • {e}")
                    else:
                        logs.append(
                            "[validate-final] all layers passed validation ✓"
                        )
                    flush_logs(logs)

                    text = "\n".join(summaries)
                elif agent_name == "OCP Deployment Engineer":
                    # ODE needs ODA output + prior cpat files.
                    ode_context = previous[:15000] if previous else "(none)"
                    ode_subs = _filter_de_sub_stages(ODE_SUB_STAGES, stage)
                    if len(ode_subs) < len(ODE_SUB_STAGES):
                        logs.append(
                            f"[ode-pass] filtered to {[s.get('abbrev') for s in ode_subs]} "
                            f"(stage={stage.get('abbrev')})"
                        )
                        flush_logs(logs)
                    for sub in ode_subs:
                        if cancelled():
                            _mark_cancelled(
                                job, logs, workspace=workspace, output_dir=output_dir
                            )
                            return
                        logs.append(f"[ode-pass] {sub['name']} — starting")
                        flush_logs(logs)
                        golden = sub.get("golden_templates") or []
                        if golden:
                            _seed_golden_templates(workspace, golden, logs)
                            flush_logs(logs)
                        part = ""
                        used_single = False
                        force_tool_loop = sub.get("tool_loop", False)
                        if RDE_SINGLE_SHOT and not force_tool_loop:
                            try:
                                part = _run_rde_single_shot(
                                    workspace=workspace,
                                    sub=sub,
                                    rda_context=ode_context,
                                    logs=logs,
                                    flush_logs=lambda: flush_logs(logs),
                                    should_cancel=cancelled,
                                )
                                used_single = True
                            except Exception as ss_exc:
                                logs.append(
                                    f"[ode-single-shot] {sub['name']} failed "
                                    f"({type(ss_exc).__name__}) — falling back to tool loop"
                                )
                                flush_logs(logs)
                        elif force_tool_loop:
                            logs.append(
                                f"[ode-pass] {sub['name']} — using tool loop"
                            )
                            flush_logs(logs)
                        if not used_single:
                            user = (
                                f"Stage: {stage['abbrev']} {agent_name}\n"
                                f"{sub['prompt']}\n"
                                f"Expected overall deliverables: "
                                f"{stage.get('output', '')}\n"
                                f"Input set id: {job.get('input_id') or '(none)'}\n"
                                f"{_format_cursor_prompt(job)}\n\n"
                                f"{follow_block}"
                                "Workspace: input/, parsed/, context/, "
                                ".cursor/skills/, output/.\n"
                                "ODA already produced the OCP CIQ schema "
                                "(summary below).\n"
                                "Write ONLY this sub-stage's files. "
                                "Prefer many small files.\n"
                                "Edit like Cursor: write_file → "
                                "append_file/str_replace.\n"
                                "FORBIDDEN: run_python(code=...), "
                                "exploring parsed/.\n\n"
                                f"ODA stage output (OCP CIQ schema/analysis):\n"
                                f"{ode_context}\n\n"
                            )
                            part = run_agent_loop(
                                workspace=workspace,
                                system=system,
                                user=user,
                                logs=logs,
                                on_log=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                            )
                        # verify_paths
                        vp = list(sub.get("verify_paths") or [])
                        if vp:
                            vp_found, vp_miss = [], []
                            for rel in vp:
                                p = workspace / rel
                                if p.is_file() and p.stat().st_size > 0:
                                    vp_found.append(rel)
                                else:
                                    vp_miss.append(rel)
                            status = "OK" if not vp_miss else "WARN"
                            logs.append(
                                f"[verify_paths] {sub.get('abbrev', sub['name'])} "
                                f"{status} — {len(vp_found)} verified, "
                                f"{len(vp_miss)} missing"
                            )
                            for m in vp_miss:
                                logs.append(f"[verify_paths] MISSING: {m}")
                            flush_logs(logs)
                        summaries.append(f"### ODE-{sub['name']}\n\n{part}\n")
                        _sync_workspace_output(workspace, output_dir)

                        # Cursor-style validate→fix per layer
                        _LAYER_MAP_ODE = {
                            "Backend": "backend",
                            "Frontend": "frontend",
                            "Docker": "docker",
                        }
                        _layer = _LAYER_MAP_ODE.get(sub["name"])
                        if _layer:
                            logs.append(
                                f"[validate-fix] running {_layer} validators..."
                            )
                            flush_logs(logs)
                            _remaining = _cpat_validate_and_fix(
                                workspace=workspace,
                                layer=_layer,
                                system=system,
                                logs=logs,
                                flush_logs=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                            )
                            if _remaining:
                                summaries.append(
                                    f"### ODE-{sub['name']}-Validation\n\n"
                                    f"⚠ {len(_remaining)} issue(s) remain "
                                    f"after fix rounds:\n"
                                    + "\n".join(
                                        f"- {e}" for e in _remaining[:10]
                                    )
                                    + "\n"
                                )
                            _sync_workspace_output(workspace, output_dir)

                        if golden:
                            _seed_golden_templates(workspace, golden, logs)
                            _sync_workspace_output(workspace, output_dir)

                        logs.append(f"[ode-pass] {sub['name']} — done")
                        flush_logs(logs)
                        follow_block = ""

                    # Final cross-layer validation
                    cpat = workspace / "output" / "cpat"
                    final_errors = _run_cpat_validators(cpat)
                    if final_errors:
                        logs.append(
                            f"[validate-final] {len(final_errors)} issue(s) "
                            "across all layers:"
                        )
                        for e in final_errors[:15]:
                            logs.append(f"[validate-final]   • {e}")
                    else:
                        logs.append(
                            "[validate-final] all layers passed validation ✓"
                        )
                    flush_logs(logs)

                    text = "\n".join(summaries)
                else:
                    lab_mode = "lab" in (stage.get("output") or "").lower()
                    rda_is_rhoso = agent_name == "RHOSO DA"
                    is_custom = bool(
                        stage.get("custom") or stage.get("rule_file")
                    )
                    single_shot_ok = False

                    # --- Try single-shot (cheap, may fail on MaaS) ---
                    if lab_mode and LAB_SINGLE_SHOT and not is_custom:
                        try:
                            text = _run_lab_single_shot(
                                workspace=workspace,
                                sources=sources,
                                logs=logs,
                                flush_logs=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                            )
                            single_shot_ok = True
                        except Exception as ss_exc:
                            logs.append(
                                f"[lab-single-shot] failed ({type(ss_exc).__name__}) — "
                                "falling back to tool loop"
                            )
                            flush_logs(logs)

                    elif rda_is_rhoso and RDA_SINGLE_SHOT and not is_custom:
                        try:
                            rda_sub = str(stage.get("sub_stage") or "").strip()
                            if not rda_sub:
                                # Fallback when older jobs only have abbrev RDA-1/2/3
                                ab = str(stage.get("abbrev") or "").strip().upper()
                                rda_sub = {
                                    "RDA-1": "Schema",
                                    "RDA-2": "Generator",
                                    "RDA-3": "Workbooks",
                                }.get(ab, "")
                            logs.append(
                                f"[rda-single-shot] stage={stage.get('abbrev')} "
                                f"sub_stage={rda_sub or '(full)'}"
                            )
                            flush_logs(logs)
                            text = _run_rda_single_shot(
                                workspace=workspace,
                                sources=sources,
                                logs=logs,
                                flush_logs=lambda: flush_logs(logs),
                                should_cancel=cancelled,
                                sub_stage=rda_sub,
                            )
                            single_shot_ok = True
                        except Exception as ss_exc:
                            logs.append(
                                f"[rda-single-shot] failed ({type(ss_exc).__name__}) — "
                                "falling back to tool loop"
                            )
                            flush_logs(logs)

                    # --- Fallback: tool loop ---
                    if not single_shot_ok:
                        if is_custom:
                            vp = list(stage.get("verify_paths") or [])
                            if not vp:
                                rule_p, _ = _resolve_rule_path(
                                    agent_name, rule_file=stage_rule
                                )
                                vp = _rule_extract_verify_paths(rule_p)
                                if vp:
                                    logs.append(
                                        f"[verify] auto-extracted {len(vp)} verify_paths from rule"
                                    )
                                    flush_logs(logs)
                            vp_block = ""
                            if vp:
                                listing = "\n".join(f"  - `{p}`" for p in vp)
                                vp_block = (
                                    "\n## REQUIRED OUTPUT FILES (self-check)\n"
                                    "The following files MUST exist and be non-empty when done:\n"
                                    f"{listing}\n"
                                    "If any are missing, go back and create them before finishing.\n"
                                )
                            deliverable_block = (
                                "CUSTOM AGENT MODE:\n"
                                "Follow your agent rule (system prompt) exactly.\n"
                                f"Expected deliverables: {stage.get('output')}\n"
                                f"{vp_block}"
                                "Prefer parsed/*.md. Write all artifacts under output/.\n"
                                "Use tools to create real files; finish with a short path list.\n"
                            )
                            source_block = (
                                f"DOCUMENT CONTENT (excerpt):\n{sources[:20000]}\n\n"
                            )
                        elif lab_mode:
                            deliverable_block = (
                                "LAB REQUIREMENTS MODE (strict):\n"
                                "The FULL document content is provided below — do NOT read_file "
                                "or search_files or run_python to explore parsed/. You already "
                                "have everything.\n"
                                "1) Write output/lab-requirements/generate_lab_requirements_workbook.py "
                                "(complete openpyxl script — extract sizing from the document "
                                "content below).\n"
                                "2) write_file output/lab-requirements/requirements.txt with 'openpyxl'.\n"
                                "3) run_python(script_path="
                                "'output/lab-requirements/generate_lab_requirements_workbook.py') once.\n"
                                "4) Summarize files created. DONE.\n"
                                "FORBIDDEN: read_file, search_files, run_python(code=...), "
                                "list_dir, glossary.\n"
                            )
                            source_block = f"FULL DOCUMENT CONTENT (use this, do not read files):\n{sources[:30000]}\n\n"
                        else:
                            rda_sub = str(stage.get("sub_stage") or "").strip().lower()
                            if rda_sub == "schema":
                                deliverable_block = (
                                    "RHOSO DA MODE — Schema ONLY (RDA-1):\n"
                                    "Write output/ciq-generators/rhoso_ciq_schema.py and stop.\n"
                                    "Do NOT write the workbook generator or run it.\n"
                                    "FORBIDDEN: run_python(code=...) to dump parsed/*.md.\n"
                                )
                            elif rda_sub == "generator":
                                deliverable_block = (
                                    "RHOSO DA MODE — Generator ONLY (RDA-2):\n"
                                    "Schema already exists at output/ciq-generators/rhoso_ciq_schema.py.\n"
                                    "Write generate_rhoso_ciq_workbooks.py + requirements.txt only.\n"
                                    "Do NOT run the generator yet (RDA-3 does that).\n"
                                )
                            elif rda_sub == "workbooks":
                                deliverable_block = (
                                    "RHOSO DA MODE — Workbooks ONLY (RDA-3):\n"
                                    "Run generate_rhoso_ciq_workbooks.py once to produce .xlsx under "
                                    "output/ciq-workbooks/rhoso/. Write a short report under "
                                    "output/pipeline-reports/rda/.\n"
                                )
                            else:
                                deliverable_block = (
                                    "RHOSO DA MODE:\n"
                                    "The FULL document content is provided below — minimize read_file/"
                                    "search_files calls. You already have the content.\n"
                                    "1) Write CIQ schema to output/ciq-generators/rhoso_ciq_schema.py.\n"
                                    "2) Write workbook generator to output/ciq-generators/"
                                    "generate_rhoso_ciq_workbooks.py + requirements.txt.\n"
                                    "3) run_python(script_path='output/ciq-generators/"
                                    "generate_rhoso_ciq_workbooks.py') once → .xlsx.\n"
                                    "4) Write pipeline report to output/pipeline-reports/rda/.\n"
                                    "Edit with write_file skeleton → append_file/str_replace hunks.\n"
                                    "FORBIDDEN: run_python(code=...) to dump parsed/*.md.\n"
                                )
                            source_block = f"FULL DOCUMENT CONTENT:\n{sources[:30000]}\n\n"
                        user = (
                            f"Stage: {stage['abbrev']} {agent_name}\n"
                            f"Expected deliverables: {stage['output']}\n"
                            f"Input set id: {job.get('input_id') or '(none)'}\n"
                            f"{_format_cursor_prompt(job)}\n\n"
                            f"{follow_block}"
                            "Workspace layout: input/, parsed/, context/, .cursor/skills/, output/.\n"
                            f"{deliverable_block}\n"
                            f"{source_block}"
                            f"Previous stage summary:\n{previous or '(none)'}\n"
                        )
                        text = run_tool_agent(
                            workspace=workspace,
                            system=system,
                            user=user,
                            logs=logs,
                            on_log=lambda: flush_logs(logs),
                            should_cancel=cancelled,
                            scope="custom" if is_custom else "ansible",
                            verify_paths=vp if is_custom else None,
                            repair_prompt=str(stage.get("repair_prompt") or "") if is_custom else "",
                        )
                _sync_workspace_output(workspace, output_dir)
                files = _list_generated(workspace)
                if agent_name == "RHOSO DA":
                    rda_sub = str(stage.get("sub_stage") or "").strip().lower()
                    out = workspace / "output"
                    if rda_sub == "schema":
                        ok = any(out.rglob("*rhoso_ciq_schema.py"))
                        if not ok:
                            logs.append("[warn] RDA-1: missing rhoso_ciq_schema.py")
                    elif rda_sub == "generator":
                        ok = any(out.rglob("generate_rhoso_ciq_workbooks.py"))
                        if not ok:
                            logs.append("[warn] RDA-2: missing generate_rhoso_ciq_workbooks.py")
                    elif rda_sub == "workbooks":
                        ok = any(out.rglob("*.xlsx"))
                        if not ok:
                            logs.append("[warn] RDA-3: missing CIQ .xlsx under output/")
                    elif not _rda_soft_ok(workspace):
                        logs.append(
                            "[warn] RDA soft checks: missing schema/generator/xlsx/report under output/"
                        )
                if agent_name == "RHOSO Deployment Engineer" and not _rde_soft_ok(workspace):
                    logs.append(
                        "[warn] RDE soft checks: missing output/cpat or rde reports"
                    )
                text = _stage_summary(agent_name, stage["abbrev"], text, files)
                flush_logs(logs)
            else:
                if cancelled():
                    _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
                    return
                is_custom_stage = bool(stage.get("custom") or stage_rule)
                if is_custom_stage:
                    try:
                        text = _run_custom_single_shot(
                            workspace,
                            agent_name=agent_name,
                            stage=stage,
                            sources=sources,
                            previous=previous or "",
                            follow_block=follow_block,
                            cursor_prompt=_format_cursor_prompt(job),
                            logs=logs,
                            flush_logs=lambda: flush_logs(logs),
                            should_cancel=cancelled,
                        )
                    except Exception as ss_exc:
                        logs.append(
                            f"[custom-single-shot] failed ({type(ss_exc).__name__}: "
                            f"{ss_exc}) — falling back to chat completion"
                        )
                        flush_logs(logs)
                        system = _system_for_agent(
                            agent_name, tool_mode=False, rule_file=stage_rule
                        )
                        user = (
                            f"Stage: {stage['abbrev']} {agent_name}\n"
                            f"Expected output: {stage['output']}\n"
                            f"{_format_cursor_prompt(job)}\n\n"
                            f"{follow_block}"
                            f"Source files:\n{sources}\n\n"
                            f"Previous stage output:\n{previous or '(none)'}\n"
                        )
                        text = complete(system, user)
                    else:
                        _sync_workspace_output(workspace, output_dir)
                        files = _list_generated(workspace)
                        text = _stage_summary(
                            agent_name, stage["abbrev"], text, files
                        )
                else:
                    system = _system_for_agent(
                        agent_name, tool_mode=False, rule_file=stage_rule
                    )
                user = (
                    f"Stage: {stage['abbrev']} {agent_name}\n"
                    f"Expected output: {stage['output']}\n"
                    f"{_format_cursor_prompt(job)}\n\n"
                    f"{follow_block}"
                    f"Source files:\n{sources}\n\n"
                    f"Previous stage output:\n{previous or '(none)'}\n"
                )
                text = complete(system, user)

            if cancelled():
                _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
                return

            out_file = output_dir / f"{stage['abbrev']}.md"
            out_file.write_text(text, encoding="utf-8")
            previous = text
            entry = f"# {stage['abbrev']} {agent_name}\n\n{text}\n"
            if index < len(combined):
                combined[index] = entry
            else:
                combined.append(entry)
            logs[running_log_idx] = (
                f"[done] {stage['abbrev']} {agent_name} — {out_file}"
            )
            _close_stage_timing(job)
            flush_logs(logs)
            job["previous"] = previous
            job["_combined"] = list(combined)
            job["_sources"] = sources
            job["artifacts"] = _list_generated(workspace, limit=200)

            gates_on = job.get("gates_enabled", True)
            if gates_on and stage.get("gate"):
                job["status"] = "awaiting_approval"
                job["gate_stage_index"] = index
                job["gate_abbrev"] = stage["abbrev"]
                job["pending_artifact"] = text
                job["current_index"] = index + 1
                logs.append(
                    f"[gate] {stage['abbrev']} — review required before continuing"
                )
                flush_logs(logs)
                return

        _sync_workspace_output(workspace, output_dir)
        job["artifacts"] = _list_generated(workspace, limit=200)
        _finish_job(job, output_dir, combined, logs)
    except AgentCancelled:
        _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
    except Exception as exc:
        if cancelled() or job.get("status") == "cancelled":
            _mark_cancelled(job, logs, workspace=workspace, output_dir=output_dir)
            return
        job["status"] = "failed"
        _close_stage_timing(job)
        now = _utc_iso()
        job["finished_at"] = now
        job["updated_at"] = now
        logs.append(f"[failed] {exc}")
        flush_logs(logs)
        # Always sync so UI can download files even after crash mid-loop
        try:
            _sync_workspace_output(workspace, output_dir)
            job["artifacts"] = _list_generated(workspace, limit=200)
            save_job(job)
        except Exception:
            pass


def start_job_thread(job: dict, data_root: Path, start_index: int = 0) -> None:
    thread = threading.Thread(
        target=run_job,
        args=(job, data_root, start_index),
        daemon=True,
    )
    thread.start()
