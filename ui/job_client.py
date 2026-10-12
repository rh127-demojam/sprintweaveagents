"""Job backend: in-memory fake jobs, or HTTP API when SPRINTWEAVE_API_URL is set."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import requests

from pipelines import list_pipelines as local_list_pipelines

API_URL = os.environ.get("SPRINTWEAVE_API_URL", "").rstrip("/")
STAGE_SECONDS = float(os.environ.get("SPRINTWEAVE_FAKE_STAGE_SECONDS", "2"))


def using_api() -> bool:
    return bool(API_URL)


def list_pipelines(session_state: dict | None = None) -> list[dict[str, Any]]:
    """Baked + PVC custom pipelines. Prefer API so UI without PVC still sees customs."""
    _ = session_state
    if using_api():
        try:
            response = requests.get(f"{API_URL}/v1/pipelines", timeout=15)
            response.raise_for_status()
            items = response.json().get("pipelines") or []
            if items:
                return items
        except requests.RequestException:
            pass
    return local_list_pipelines()


def list_custom_agents(session_state: dict | None = None) -> list[dict[str, Any]]:
    _ = session_state
    if using_api():
        response = requests.get(f"{API_URL}/v1/agents", timeout=15)
        response.raise_for_status()
        return list(response.json().get("agents") or [])
    return []


def create_custom_agent(
    session_state: dict | None,
    *,
    name: str,
    abbrev: str,
    goal: str,
    output_hint: str = "",
    blurb: str = "",
    agent_id: str = "",
    mode: str = "tool_loop",
    tool_loop: bool | None = None,
    gate: bool = True,
    generate_llm: bool = False,
    rule_markdown: str = "",
    stages: list[dict[str, Any]] | None = None,
    verify_paths: list[str] | None = None,
    repair_prompt: str = "",
) -> dict[str, Any]:
    _ = session_state
    if not using_api():
        raise RuntimeError("create agent requires API mode")
    mode_val = (mode or "").strip() or (
        "tool_loop" if tool_loop is not False else "single_shot"
    )
    data = {
        "name": name,
        "abbrev": abbrev,
        "goal": goal,
        "output_hint": output_hint,
        "blurb": blurb,
        "agent_id": agent_id,
        "mode": mode_val,
        "gate": "true" if gate else "false",
        "generate_llm": "true" if generate_llm else "false",
        "rule_markdown": rule_markdown,
        "repair_prompt": repair_prompt,
    }
    if stages:
        import json as _json

        data["stages_json"] = _json.dumps(stages)
    if verify_paths:
        import json as _json2

        data["verify_paths_json"] = _json2.dumps(verify_paths)
    response = requests.post(
        f"{API_URL}/v1/agents",
        data=data,
        timeout=180 if generate_llm else 30,
    )
    if not response.ok:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(str(detail))
    return response.json()


def delete_custom_agent(session_state: dict | None, agent_id: str) -> dict[str, Any]:
    _ = session_state
    if not using_api():
        raise RuntimeError("delete agent requires API mode")
    response = requests.delete(f"{API_URL}/v1/agents/{agent_id}", timeout=30)
    if not response.ok:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(str(detail))
    return response.json()


def resolve_pipeline(pipeline_id: str, session_state: dict | None = None) -> dict[str, Any]:
    for item in list_pipelines(session_state):
        if item.get("id") == pipeline_id:
            return item
    raise KeyError(f"pipeline '{pipeline_id}' not found")


def api_reachable() -> tuple[bool, str]:
    if not API_URL:
        return False, "SPRINTWEAVE_API_URL is not set (using fake jobs)."
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        if response.ok:
            return True, "API reachable."
        return False, f"API returned HTTP {response.status_code}."
    except requests.RequestException as exc:
        return False, f"API unreachable: {exc}"


def _fake_store(session_state: dict) -> list[dict[str, Any]]:
    if "jobs" not in session_state:
        session_state["jobs"] = []
    return session_state["jobs"]


def _fake_inputs(session_state: dict) -> dict[str, dict[str, Any]]:
    if "inputs" not in session_state:
        session_state["inputs"] = {}
    return session_state["inputs"]


def _fake_finish(job: dict[str, Any]) -> None:
    stages = job["stages"]
    job["status"] = "succeeded"
    job["current_index"] = len(stages)
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)
    job["artifact_md"] = (
        f"# {job['pipeline_name']} (fake artifact)\n\n"
        f"Files: {', '.join(job['filenames']) or '(none)'}\n\n"
        f"Extra instructions:\n{job.get('instructions') or '(none)'}\n\n"
        "API is not configured; files were not saved.\n"
    )
    logs = list(job.get("logs") or [])
    logs.append("[done] fake pipeline complete")
    job["logs"] = logs


def _advance_fake(job: dict[str, Any]) -> None:
    if job.get("cancel_requested") or job.get("status") == "cancelled":
        if job.get("status") != "cancelled":
            logs = list(job.get("logs") or [])
            logs.append("[cancelled] stopped by user")
            job["logs"] = logs
            job["status"] = "cancelled"
        return
    if job["status"] in {"succeeded", "failed", "rejected", "cancelled", "awaiting_approval"}:
        return
    stages = job["stages"]
    elapsed = time.time() - job["started_at"]
    # Count completed non-gated progress from start_index
    start = int(job.get("_fake_start", 0))
    done_from_start = min(int(elapsed / STAGE_SECONDS), len(stages) - start)
    absolute_done = start + done_from_start

    logs: list[str] = list(job.get("_base_logs") or [])
    for i, stage in enumerate(stages):
        if i < absolute_done:
            logs.append(f"[done] {stage['abbrev']} {stage['agent']} — {stage['output']}")
        elif i == absolute_done and absolute_done < len(stages):
            logs.append(f"[running] {stage['abbrev']} {stage['agent']} — {stage['output']}")
        elif i > absolute_done:
            logs.append(f"[queued] {stage['abbrev']} {stage['agent']}")

    # Just finished a stage?
    if done_from_start > 0:
        finished_idx = absolute_done - 1
        if (
            job.get("gates_enabled", True)
            and 0 <= finished_idx < len(stages)
            and stages[finished_idx].get("gate")
        ):
            stage = stages[finished_idx]
            job["status"] = "awaiting_approval"
            job["gate_stage_index"] = finished_idx
            job["gate_abbrev"] = stage["abbrev"]
            job["pending_artifact"] = (
                f"# {stage['abbrev']} {stage['agent']} (fake)\n\n"
                f"Expected: {stage['output']}\n\n"
                "Review and approve to continue.\n"
            )
            job["current_index"] = finished_idx + 1
            logs = [line for line in logs if not line.startswith("[running]") and not line.startswith("[queued]")]
            for i, stage_i in enumerate(stages):
                if i <= finished_idx:
                    if f"[done] {stage_i['abbrev']}" not in "\n".join(logs):
                        logs.append(
                            f"[done] {stage_i['abbrev']} {stage_i['agent']} — {stage_i['output']}"
                        )
            logs.append(f"[gate] {stage['abbrev']} — review required before continuing")
            job["logs"] = logs
            job["_base_logs"] = [
                line for line in logs if line.startswith("[done]") or line.startswith("[approved]")
                or line.startswith("[edited]") or line.startswith("[info]")
            ]
            return

    job["logs"] = logs
    job["current_index"] = absolute_done
    if absolute_done >= len(stages):
        _fake_finish(job)
    else:
        job["status"] = "running"


def list_inputs(session_state: dict) -> list[dict[str, Any]]:
    if using_api():
        response = requests.get(f"{API_URL}/v1/inputs", timeout=15)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else data.get("inputs", [])
    return list(_fake_inputs(session_state).values())


def list_artifacts(session_state: dict, job_id: str) -> list[str]:
    if using_api():
        response = requests.get(f"{API_URL}/v1/jobs/{job_id}/artifacts", timeout=30)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return data.get("files") or []
    job = get_job(session_state, job_id)
    return list((job or {}).get("artifacts") or [])


def artifact_download_url(job_id: str, rel_path: str) -> str:
    from urllib.parse import quote

    return f"{API_URL}/v1/jobs/{job_id}/artifacts/{quote(rel_path, safe='/')}"


def artifacts_zip_url(job_id: str) -> str:
    return f"{API_URL}/v1/jobs/{job_id}/artifacts.zip"


def fetch_artifact_bytes(job_id: str, rel_path: str) -> bytes:
    """Pull artifact via in-cluster API (browser cannot reach sprintweave-api DNS)."""
    response = requests.get(artifact_download_url(job_id, rel_path), timeout=120)
    response.raise_for_status()
    return response.content


def fetch_artifacts_zip_bytes(job_id: str) -> bytes:
    response = requests.get(artifacts_zip_url(job_id), timeout=300)
    response.raise_for_status()
    return response.content


def upload_inputs(
    session_state: dict,
    input_id: str = "",
    uploads: list | None = None,
) -> dict[str, Any]:
    """Create/update an input set without starting a job."""
    if using_api():
        data = {"input_id": input_id or ""}
        files = []
        if uploads:
            for item in uploads:
                item.seek(0)
                files.append(
                    (
                        "files",
                        (item.name, item.getvalue(), item.type or "application/octet-stream"),
                    )
                )
        if not files:
            raise ValueError("Upload at least one file.")
        response = requests.post(
            f"{API_URL}/v1/inputs",
            data=data,
            files=files,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    store = _fake_inputs(session_state)
    iid = (input_id or "").strip() or str(uuid.uuid4())[:8]
    names = [f.name for f in (uploads or [])]
    if not names:
        raise ValueError("Upload at least one file.")
    existing = list(store.get(iid, {}).get("filenames") or [])
    for name in names:
        if name not in existing:
            existing.append(name)
    store[iid] = {
        "input_id": iid,
        "filenames": existing,
        "path": f"(fake)/inputs/{iid}",
        "job_ids": list(store.get(iid, {}).get("job_ids") or []),
        "uploaded": names,
    }
    return store[iid]


def delete_input_file(session_state: dict, input_id: str, filename: str) -> dict[str, Any]:
    if using_api():
        response = requests.delete(
            f"{API_URL}/v1/inputs/{input_id}/files/{filename}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    store = _fake_inputs(session_state)
    item = store.get(input_id)
    if not item:
        raise LookupError("input set not found")
    names = [n for n in (item.get("filenames") or []) if n != filename]
    if not names:
        store.pop(input_id, None)
        return {
            "ok": True,
            "input_id": input_id,
            "deleted": filename,
            "filenames": [],
            "removed_set": True,
        }
    item["filenames"] = names
    return {"ok": True, "input_id": input_id, "deleted": filename, "filenames": names}


def delete_input_set(session_state: dict, input_id: str) -> dict[str, Any]:
    if using_api():
        response = requests.delete(f"{API_URL}/v1/inputs/{input_id}", timeout=30)
        response.raise_for_status()
        return response.json()
    store = _fake_inputs(session_state)
    if input_id not in store:
        raise LookupError("input set not found")
    store.pop(input_id, None)
    return {"ok": True, "input_id": input_id, "deleted_set": True}


def create_job(
    session_state: dict,
    pipeline_id: str,
    filenames: list[str],
    instructions: str,
    uploads: list | None = None,
    gates_enabled: bool = True,
    input_id: str = "",
) -> dict[str, Any]:
    pipeline = resolve_pipeline(pipeline_id, session_state)
    if using_api():
        data = {
            "pipeline_id": pipeline_id,
            "instructions": instructions or "",
            "gates_enabled": "true" if gates_enabled else "false",
            "input_id": input_id or "",
        }
        files = []
        if uploads:
            for item in uploads:
                item.seek(0)
                files.append(
                    (
                        "files",
                        (item.name, item.getvalue(), item.type or "application/octet-stream"),
                    )
                )
        response = requests.post(
            f"{API_URL}/v1/jobs",
            data=data,
            files=files or None,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    store = _fake_inputs(session_state)
    iid = (input_id or "").strip() or str(uuid.uuid4())[:8]
    names = list(filenames or [])
    if uploads:
        names = [f.name for f in uploads]
    if iid in store:
        existing = list(store[iid].get("filenames") or [])
        for name in names:
            if name not in existing:
                existing.append(name)
        names = existing or names
    if not names:
        raise ValueError(
            "Provide input_id with existing files, and/or upload one or more files."
        )
    store[iid] = {
        "input_id": iid,
        "filenames": names,
        "path": f"(fake)/inputs/{iid}",
        "job_ids": list(store.get(iid, {}).get("job_ids") or []),
    }

    job = {
        "id": str(uuid.uuid4())[:8],
        "input_id": iid,
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline["name"],
        "filenames": names,
        "instructions": instructions,
        "gates_enabled": gates_enabled,
        "stages": pipeline["stages"],
        "status": "queued",
        "current_index": 0,
        "started_at": time.time(),
        "_fake_start": 0,
        "_base_logs": [],
        "logs": [
            f"[input] set={iid} files={', '.join(names)}",
        ],
        "artifact_md": "",
        "input_path": f"(fake)/inputs/{iid}",
        "output_path": "",
    }
    if not gates_enabled:
        job["logs"].append("[info] gates disabled for this run — stages will not pause")
    store[iid]["job_ids"] = list(store[iid].get("job_ids") or []) + [job["id"]]
    _advance_fake(job)
    _fake_store(session_state).insert(0, job)
    return job


def get_job(session_state: dict, job_id: str) -> dict[str, Any] | None:
    if using_api():
        response = requests.get(f"{API_URL}/v1/jobs/{job_id}", timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    for job in _fake_store(session_state):
        if job["id"] == job_id:
            _advance_fake(job)
            return job
    return None


def list_jobs(session_state: dict) -> list[dict[str, Any]]:
    if using_api():
        response = requests.get(f"{API_URL}/v1/jobs", timeout=15)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else data.get("jobs", [])
    for job in _fake_store(session_state):
        _advance_fake(job)
    return list(_fake_store(session_state))


def approve_job(
    session_state: dict,
    job_id: str,
    edited_text: str | None = None,
    follow_up: str = "",
) -> dict[str, Any]:
    if using_api():
        data: dict[str, str] = {"follow_up": follow_up or ""}
        if edited_text is not None:
            data["edited_text"] = edited_text
        response = requests.post(
            f"{API_URL}/v1/jobs/{job_id}/approve",
            data=data,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    job = get_job(session_state, job_id)
    if not job:
        raise LookupError("job not found")
    if job.get("status") != "awaiting_approval":
        raise ValueError("job is not awaiting approval")

    idx = int(job["gate_stage_index"])
    stage = job["stages"][idx]
    if edited_text is not None and edited_text != job.get("pending_artifact"):
        job["pending_artifact"] = edited_text
        logs = list(job.get("logs") or [])
        logs.append(f"[edited] {stage['abbrev']} artifact updated before approval")
        job["logs"] = logs

    logs = list(job.get("logs") or [])
    follow = (follow_up or "").strip()
    if follow:
        job["follow_up"] = follow
        logs.append(f"[follow-up] queued for next stage ({len(follow)} chars)")
    else:
        job.pop("follow_up", None)
    logs.append(f"[approved] {stage['abbrev']} — continuing")
    job["logs"] = logs
    job["_base_logs"] = [
        line
        for line in logs
        if line.startswith("[done]")
        or line.startswith("[approved]")
        or line.startswith("[edited]")
        or line.startswith("[info]")
        or line.startswith("[gate]")
        or line.startswith("[follow-up]")
    ]
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    job.pop("pending_artifact", None)

    next_index = idx + 1
    if next_index >= len(job["stages"]):
        _fake_finish(job)
        return job

    job["status"] = "running"
    job["_fake_start"] = next_index
    job["started_at"] = time.time()
    job["current_index"] = next_index
    if job.get("follow_up"):
        logs = list(job.get("logs") or [])
        logs.append(f"[follow-up] applied to {job['stages'][next_index]['abbrev']} (fake)")
        job["logs"] = logs
        job.pop("follow_up", None)
    _advance_fake(job)
    return job


def reject_job(session_state: dict, job_id: str, reason: str = "") -> dict[str, Any]:
    if using_api():
        response = requests.post(
            f"{API_URL}/v1/jobs/{job_id}/reject",
            data={"reason": reason or ""},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    job = get_job(session_state, job_id)
    if not job:
        raise LookupError("job not found")
    if job.get("status") != "awaiting_approval":
        raise ValueError("job is not awaiting approval")
    logs = list(job.get("logs") or [])
    detail = reason.strip() or "no reason given"
    logs.append(f"[rejected] {job.get('gate_abbrev', '?')}: {detail}")
    job["status"] = "rejected"
    job["logs"] = logs
    job.pop("pending_artifact", None)
    return job


def cancel_job(session_state: dict, job_id: str) -> dict[str, Any]:
    """Stop a running job (Cursor-like Stop)."""
    if using_api():
        response = requests.post(
            f"{API_URL}/v1/jobs/{job_id}/cancel",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    job = get_job(session_state, job_id)
    if not job:
        raise LookupError("job not found")
    if job.get("status") not in {"queued", "running", "awaiting_approval"}:
        raise ValueError(f"job cannot be cancelled from status={job.get('status')}")
    job["cancel_requested"] = True
    logs = list(job.get("logs") or [])
    logs.append("[cancel] stop requested")
    logs.append("[cancelled] stopped by user")
    job["logs"] = logs
    job["status"] = "cancelled"
    job.pop("pending_artifact", None)
    job.pop("gate_stage_index", None)
    job.pop("gate_abbrev", None)
    return job


def resume_job(
    session_state: dict,
    job_id: str,
    stage: str = "RDE",
) -> dict[str, Any]:
    """Resume from a stage (default RDE) without re-running Docling/RDA."""
    if using_api():
        response = requests.post(
            f"{API_URL}/v1/jobs/{job_id}/resume",
            data={"stage": stage or "RDE"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    raise RuntimeError("resume requires API mode")


def skip_job(
    session_state: dict,
    job_id: str,
    *,
    skip_rest: bool = False,
) -> dict[str, Any]:
    """Skip current gated agent (or all remaining) and continue."""
    if using_api():
        response = requests.post(
            f"{API_URL}/v1/jobs/{job_id}/skip",
            data={"skip_rest": "true" if skip_rest else "false"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    raise RuntimeError("skip requires API mode")


def get_cpat_deploy(session_state: dict | None, job_id: str) -> dict[str, Any]:
    _ = session_state
    if not using_api():
        raise RuntimeError("CPAT deploy requires API mode")
    response = requests.get(f"{API_URL}/v1/jobs/{job_id}/cpat/deploy", timeout=30)
    response.raise_for_status()
    return response.json()


def start_cpat_deploy(session_state: dict | None, job_id: str) -> dict[str, Any]:
    _ = session_state
    if not using_api():
        raise RuntimeError("CPAT deploy requires API mode")
    response = requests.post(f"{API_URL}/v1/jobs/{job_id}/cpat/deploy", timeout=60)
    if not response.ok:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(str(detail))
    return response.json()
