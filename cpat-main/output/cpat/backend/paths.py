"""Runtime data paths — kept outside application source code.

Layout (default local: <repo>/data, container: /cpat-data via CPAT_DATA_DIR):

  data/
    cpat.db
    uploads/          # registered CIQ workbooks
    secrets/          # kubeconfig, pull secrets, SSH keys per cluster
    logs/
      registrations/  # registration execution logs
      installations/  # RHOSO task execution logs
    artifacts/        # generated OpenStack CRs / manifests per cluster
"""

from __future__ import annotations

import os
import re

# backend/ or /app (container copies backend flat into /app)
_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:[/\\]")


def _is_windows_or_msys_path(path: str) -> bool:
    """Detect Windows drive paths and Git-Bash MSYS rewrites."""
    if not path:
        return False
    normalized = path.replace("\\", "/")
    if _WIN_DRIVE_RE.match(normalized):
        return True
    # Linux abspath of C:/... under cwd /app → /app/C:/...
    if "/app/C:" in normalized or normalized.startswith("/app/C:"):
        return True
    if "Program Files/Git" in normalized:
        return True
    return False


def _running_in_container() -> bool:
    if os.environ.get("CPAT_ROOT") == "/app":
        return True
    if os.path.isfile("/.dockerenv"):
        return True
    # Flat layout in the image: backend modules live directly under /app
    return os.path.basename(_SOURCE_DIR) != "backend"


def _default_data_dir() -> str:
    """Prefer sibling repo ``data/`` when running from ``backend/``; else ``/cpat-data``."""
    if _running_in_container():
        return "/cpat-data"
    sibling = os.path.abspath(os.path.join(_SOURCE_DIR, "..", "data"))
    if os.path.basename(_SOURCE_DIR) == "backend":
        return sibling
    return "/cpat-data"


def _resolve_data_dir() -> str:
    raw = (os.environ.get("CPAT_DATA_DIR") or "").strip()
    if _running_in_container():
        # Ignore empty / Windows / MSYS-mangled values from the host shell
        if not raw or _is_windows_or_msys_path(raw) or raw.startswith("/app/"):
            return "/cpat-data"
        return raw if raw.startswith("/") else "/cpat-data"

    if not raw:
        return _default_data_dir()
    if _is_windows_or_msys_path(raw):
        # Local Windows checkout may legitimately use C:\...\data
        return os.path.abspath(raw)
    return os.path.abspath(raw)


DATA_DIR = _resolve_data_dir()
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
SECRETS_DIR = os.path.join(DATA_DIR, "secrets")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
REGISTRATION_LOGS_DIR = os.path.join(LOGS_DIR, "registrations")
INSTALLATION_LOGS_DIR = os.path.join(LOGS_DIR, "installations")
ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
DATABASE_PATH = os.environ.get("CPAT_DATABASE", os.path.join(DATA_DIR, "cpat.db"))
if _running_in_container() and _is_windows_or_msys_path(DATABASE_PATH):
    DATABASE_PATH = os.path.join(DATA_DIR, "cpat.db")


def ensure_data_dirs() -> None:
    """Create the runtime data tree (never under source packages)."""
    for path in (
        DATA_DIR,
        UPLOAD_DIR,
        SECRETS_DIR,
        LOGS_DIR,
        REGISTRATION_LOGS_DIR,
        INSTALLATION_LOGS_DIR,
        ARTIFACTS_DIR,
    ):
        os.makedirs(path, exist_ok=True)


def cluster_artifacts_dir(cluster_name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in cluster_name)
    path = os.path.join(ARTIFACTS_DIR, safe or "rhoso")
    os.makedirs(path, exist_ok=True)
    return path


def _safe_artifact_name(filename: str) -> str:
    """Basename only; reject path traversal."""
    raw = (filename or "").strip().replace("\\", "/")
    if not raw or ".." in raw.split("/") or raw.startswith("/"):
        raise ValueError("Invalid artifact filename")
    name = os.path.basename(raw)
    if not name or name in (".", ".."):
        raise ValueError("Invalid artifact filename")
    return name


def list_cluster_artifacts(cluster_name: str) -> list[dict]:
    """List reviewable files under the cluster artifacts directory."""
    root = cluster_artifacts_dir(cluster_name)
    entries: list[dict] = []
    if not os.path.isdir(root):
        return entries
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        lower = name.lower()
        if not lower.endswith((".yaml", ".yml", ".j2", ".md", ".txt", ".cfg", ".db", ".backup", ".conf", ".json")):
            continue
        st = os.stat(path)
        entries.append(
            {
                "name": name,
                "size": st.st_size,
                "modified_at": st.st_mtime,
            }
        )
    return entries


def read_cluster_artifact(cluster_name: str, filename: str) -> tuple[str, str]:
    """Return (absolute_path, utf-8 text) for a cluster artifact file."""
    name = _safe_artifact_name(filename)
    root = os.path.realpath(cluster_artifacts_dir(cluster_name))
    path = os.path.realpath(os.path.join(root, name))
    if not path.startswith(root + os.sep) and path != root:
        raise ValueError("Invalid artifact path")
    if not os.path.isfile(path):
        raise FileNotFoundError(name)
    with open(path, encoding="utf-8", errors="replace") as handle:
        return path, handle.read()


def write_text_log(directory: str, filename: str, content: str) -> str:
    """Write a UTF-8 log file under the data logs tree; return absolute path."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path
