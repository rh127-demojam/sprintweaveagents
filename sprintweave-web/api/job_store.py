"""Persist jobs to PVC so they survive API pod restarts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("SPRINTWEAVE_DATA_DIR", "/data"))
JOBS_DIR = DATA_DIR / "jobs"

# Keys that are huge / internal — keep short for disk, full in memory is fine
_SKIP_ON_DISK = {"_sources", "_combined"}
_MAX_LOG_LINES = int(os.environ.get("SPRINTWEAVE_JOB_LOG_MAX", "500"))
_MAX_PENDING_CHARS = int(os.environ.get("SPRINTWEAVE_JOB_PENDING_MAX", "50000"))


def job_meta_path(job_id: str) -> Path:
    return JOBS_DIR / job_id / "job.json"


def save_job(job: dict[str, Any]) -> None:
    """Write job metadata to /data/jobs/<id>/job.json (atomic replace)."""
    jid = job.get("id")
    if not jid:
        return
    job_dir = JOBS_DIR / str(jid)
    job_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    for key, value in job.items():
        if key in _SKIP_ON_DISK:
            continue
        if key == "logs" and isinstance(value, list) and len(value) > _MAX_LOG_LINES:
            payload[key] = value[-_MAX_LOG_LINES:]
            continue
        if key == "pending_artifact" and isinstance(value, str) and len(value) > _MAX_PENDING_CHARS:
            payload[key] = value[:_MAX_PENDING_CHARS] + "\n… truncated"
            continue
        if key == "artifact_md" and isinstance(value, str) and len(value) > _MAX_PENDING_CHARS:
            payload[key] = value[:_MAX_PENDING_CHARS] + "\n… truncated"
            continue
        payload[key] = value
    target = job_meta_path(str(jid))
    tmp = target.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(target)
    except OSError:
        # Best-effort — never crash the worker on disk issues
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def load_job(job_id: str) -> dict[str, Any] | None:
    path = job_meta_path(job_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("id") != job_id:
        data = data if isinstance(data, dict) else {}
        data["id"] = job_id
    return data


def load_all_jobs() -> dict[str, dict[str, Any]]:
    """Scan /data/jobs/*/job.json and return id → job dict."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    loaded: dict[str, dict[str, Any]] = {}
    try:
        entries = sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return loaded
    for entry in entries:
        if not entry.is_dir():
            continue
        job = load_job(entry.name)
        if not job:
            # Recover minimal stub from directory alone (old runs before persistence)
            out = entry / "output"
            ws_out = entry / "workspace" / "output"
            if not out.is_dir() and not ws_out.is_dir():
                continue
            input_id = ""
            tip = entry / "input_id.txt"
            if tip.is_file():
                input_id = tip.read_text(encoding="utf-8", errors="replace").strip()
            job = {
                "id": entry.name,
                "input_id": input_id,
                "pipeline_id": "unknown",
                "pipeline_name": "(recovered from PVC)",
                "filenames": [],
                "instructions": "",
                "stages": [],
                "status": "succeeded" if out.is_dir() and any(out.rglob("*")) else "failed",
                "current_index": 0,
                "logs": [
                    "[recovered] job metadata missing — loaded from PVC directory after restart"
                ],
                "artifact_md": "",
                "gates_enabled": True,
                "output_path": str(out),
                "workspace_path": str(entry / "workspace"),
            }
        # Mark interrupted in-flight jobs as failed after restart
        if job.get("status") in {"queued", "running"}:
            job["status"] = "failed"
            logs = list(job.get("logs") or [])
            logs.append(
                "[recovered] pod restarted while job was in progress — marked failed "
                "(files under workspace/output may still exist)"
            )
            job["logs"] = logs
            save_job(job)
        loaded[job["id"]] = job
    return loaded
