"""RHOSO input-file uploads (kubeconfig, pull secret, keys, etc.)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

# Form field name -> (CIQ parameter name, stored filename)
INPUT_FILE_SPECS: dict[str, tuple[str, str]] = {
    "kubeconfig": ("Kubeconfig Path", "kubeconfig"),
    "pull_secret": ("Pull Secret Path", "pull-secret.json"),
    "mirror_pull_secret": ("Mirror Pull Secret Path", "mirror-pull-secret.json"),
    "mirror_ca": ("Mirror Registry CA Path", "mirror-ca.crt"),
    "dataplane_ssh_key": ("Data Plane SSH Private Key Path", "dataplane-ssh-key"),
    "netapp_config": ("Trident Secret Name", "netapp-config.json"),
    "multipath_config": ("Multipath Config Secret Name", "multipath-config.conf"),
    "ceph_keyring": ("Ceph Client Key Path", "ceph-keyring"),
}

PATH_PARAMETER_NAMES: frozenset[str] = frozenset(
    param for param, _filename in INPUT_FILE_SPECS.values()
)

MANIFEST_NAME = "manifest.json"


def secrets_dir_for_cluster(secrets_root: str, cluster_id: str) -> str:
    return os.path.join(secrets_root, cluster_id)


def load_manifest(cluster_dir: str) -> dict[str, Any]:
    path = os.path.join(cluster_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_manifest(cluster_dir: str, manifest: dict[str, Any]) -> None:
    os.makedirs(cluster_dir, exist_ok=True)
    path = os.path.join(cluster_dir, MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)


def path_overrides_from_parameters(parameters: dict[str, str]) -> dict[str, str]:
    """Return only path-type CIQ parameters that have non-empty values."""
    return {
        name: value
        for name, value in parameters.items()
        if name in PATH_PARAMETER_NAMES and isinstance(value, str) and value.strip()
    }


def list_input_file_status(
    secrets_root: str,
    cluster_id: str,
    parameters: dict[str, str],
) -> list[dict[str, Any]]:
    cluster_dir = secrets_dir_for_cluster(secrets_root, cluster_id)
    manifest = load_manifest(cluster_dir)
    rows: list[dict[str, Any]] = []
    for field, (param_name, stored_name) in INPUT_FILE_SPECS.items():
        stored_path = os.path.abspath(os.path.join(cluster_dir, stored_name))
        meta = manifest.get(param_name) or {}
        uploaded = os.path.isfile(stored_path)
        rows.append(
            {
                "field": field,
                "parameter": param_name,
                "uploaded": uploaded,
                "stored_path": stored_path if uploaded else None,
                "configured_path": (parameters.get(param_name) or "").strip() or None,
                "original_filename": meta.get("original_filename"),
                "uploaded_at": meta.get("uploaded_at"),
            }
        )
    return rows


def save_uploaded_input_files(
    secrets_root: str,
    cluster_id: str,
    files_by_field: dict[str, Any],
    parameters: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """
    Save uploaded files for a cluster and update CIQ path parameters.

    ``files_by_field`` maps form field names to Werkzeug FileStorage objects.
    Returns (updated_parameters, list of human-readable change messages).
    """
    if not files_by_field:
        return parameters, []

    cluster_dir = secrets_dir_for_cluster(secrets_root, cluster_id)
    os.makedirs(cluster_dir, exist_ok=True)
    manifest = load_manifest(cluster_dir)
    updated = dict(parameters)
    messages: list[str] = []

    for field, storage in files_by_field.items():
        if field not in INPUT_FILE_SPECS:
            continue
        if storage is None or not getattr(storage, "filename", None):
            continue

        param_name, stored_name = INPUT_FILE_SPECS[field]
        dest = os.path.abspath(os.path.join(cluster_dir, stored_name))
        storage.save(dest)
        # Restrictive permissions for secrets/keys
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass

        original = os.path.basename(storage.filename)
        uploaded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest[param_name] = {
            "field": field,
            "stored_filename": stored_name,
            "original_filename": original,
            "uploaded_at": uploaded_at,
        }
        updated[param_name] = dest
        messages.append(f"Stored {param_name} → {dest} (from {original})")

    save_manifest(cluster_dir, manifest)
    return updated, messages


def extract_input_files_from_request(request_files) -> dict[str, Any]:
    """Collect recognized input-file uploads from a Flask request.files multi-dict."""
    found: dict[str, Any] = {}
    for field in INPUT_FILE_SPECS:
        storage = request_files.get(field)
        if storage is not None and storage.filename:
            found[field] = storage
    return found


def copy_pending_uploads(
    secrets_root: str,
    pending_dir: str,
    cluster_id: str,
    parameters: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """
    Move files from a pending staging directory into the cluster secrets dir.
    Expects pending_dir to already contain canonical stored filenames + manifest.
    """
    if not pending_dir or not os.path.isdir(pending_dir):
        return parameters, []

    cluster_dir = secrets_dir_for_cluster(secrets_root, cluster_id)
    os.makedirs(cluster_dir, exist_ok=True)

    pending_manifest = load_manifest(pending_dir)
    updated = dict(parameters)
    messages: list[str] = []

    for param_name, meta in pending_manifest.items():
        stored_name = meta.get("stored_filename")
        if not stored_name:
            continue
        src = os.path.join(pending_dir, stored_name)
        if not os.path.isfile(src):
            continue
        dest = os.path.abspath(os.path.join(cluster_dir, stored_name))
        shutil.copy2(src, dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        updated[param_name] = dest
        messages.append(
            f"Stored {param_name} → {dest} "
            f"(from {meta.get('original_filename', stored_name)})"
        )

    if pending_manifest:
        # Remap paths in manifest to this cluster
        cluster_manifest = load_manifest(cluster_dir)
        for param_name, meta in pending_manifest.items():
            cluster_manifest[param_name] = dict(meta)
        save_manifest(cluster_dir, cluster_manifest)

    return updated, messages


def stage_uploads_to_pending(
    secrets_root: str,
    pending_id: str,
    files_by_field: dict[str, Any],
) -> str | None:
    """Save uploads to a temporary pending directory; return path or None if empty."""
    if not files_by_field:
        return None

    pending_dir = os.path.join(secrets_root, "_pending", pending_id)
    # Reuse save logic with a fake cluster id under _pending
    fake_root = os.path.join(secrets_root, "_pending")
    save_uploaded_input_files(fake_root, pending_id, files_by_field, {})
    return pending_dir


def cleanup_pending(pending_dir: str | None) -> None:
    if pending_dir and os.path.isdir(pending_dir):
        shutil.rmtree(pending_dir, ignore_errors=True)
