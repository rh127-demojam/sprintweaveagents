from __future__ import annotations

import io
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ui"))

from pipelines import get_pipeline, list_pipelines  # noqa: E402
from api.worker import (  # noqa: E402
    approve_and_continue,
    cancel_job,
    reject_job,
    resume_job_from_stage,
    skip_and_continue,
    start_job_thread,
)
from api.job_store import load_all_jobs, save_job  # noqa: E402
from api.custom_agents import (  # noqa: E402
    create_agent,
    delete_agent,
    list_agents,
    read_rule,
)
from api.cpat_deploy import (  # noqa: E402
    get_deploy_status,
    start_deploy,
)

DATA_DIR = Path(os.environ.get("SPRINTWEAVE_DATA_DIR", "/data"))
INPUTS_DIR = DATA_DIR / "inputs"
JOBS_DIR = DATA_DIR / "jobs"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

app = FastAPI(title="SprintWeave API")
# Load jobs from PVC so UI survives pod restarts
JOBS: dict[str, dict] = load_all_jobs()


@app.on_event("startup")
def _reload_jobs_on_startup() -> None:
    """Re-scan PVC in case jobs landed before import finished."""
    JOBS.update(load_all_jobs())


def _list_job_artifacts(job_id: str) -> list[str]:
    """Prefer output/; fall back to workspace/output/ if sync never ran (crash)."""
    roots = [
        JOBS_DIR / job_id / "output",
        JOBS_DIR / job_id / "workspace" / "output",
    ]
    seen: set[str] = set()
    files: list[str] = []
    for out in roots:
        if not out.is_dir():
            continue
        for p in sorted(out.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(out).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            files.append(rel)
    return files


def _safe_artifact_path(job_id: str, rel: str) -> Path:
    cleaned = Path(rel.replace("\\", "/").lstrip("/"))
    if ".." in cleaned.parts:
        raise HTTPException(status_code=400, detail="invalid artifact path")
    for root_name in ("output", "workspace/output"):
        out = (JOBS_DIR / job_id / Path(root_name)).resolve()
        if not out.is_dir():
            continue
        path = (out / cleaned).resolve()
        try:
            path.relative_to(out)
        except ValueError:
            continue
        if path.is_file():
            return path
    raise HTTPException(status_code=404, detail="artifact not found")


def _public(job: dict) -> dict:
    jid = job["id"]
    artifacts = job.get("artifacts") or _list_job_artifacts(jid)
    return {
        "id": jid,
        "input_id": job.get("input_id", ""),
        "pipeline_id": job["pipeline_id"],
        "pipeline_name": job["pipeline_name"],
        "filenames": job["filenames"],
        "instructions": job.get("instructions", ""),
        "stages": job["stages"],
        "status": job["status"],
        "current_index": job.get("current_index", 0),
        "logs": job.get("logs", []),
        "artifact_md": job.get("artifact_md", ""),
        "input_path": job.get("input_path", ""),
        "output_path": job.get("output_path", ""),
        "workspace_path": job.get("workspace_path", ""),
        "artifacts": artifacts,
        "gates_enabled": job.get("gates_enabled", True),
        "gate_stage_index": job.get("gate_stage_index"),
        "gate_abbrev": job.get("gate_abbrev", ""),
        "pending_artifact": job.get("pending_artifact", ""),
        "follow_up": job.get("follow_up", ""),
        "cancel_requested": bool(job.get("cancel_requested")),
        "created_at": job.get("created_at", ""),
        "started_at": job.get("started_at", ""),
        "updated_at": job.get("updated_at", ""),
        "finished_at": job.get("finished_at", ""),
        "duration": job.get("duration", ""),
        "duration_s": job.get("duration_s"),
        "stage_timings": job.get("stage_timings") or [],
        "cpat_deploy": job.get("cpat_deploy") or {},
    }


def _safe_id(raw: str, *, label: str = "id") -> str:
    value = (raw or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{label} is empty")
    if not _ID_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid {label}. Use letters, digits, dot, underscore, or hyphen "
                "(max 64 chars)."
            ),
        )
    return value


def _input_dir(input_id: str) -> Path:
    return INPUTS_DIR / input_id


def _list_input_files(input_dir: Path) -> list[str]:
    if not input_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in input_dir.iterdir()
        if p.is_file() and p.name != "meta.json"
    )


def _write_input_meta(input_id: str, filenames: list[str], *, created: bool) -> dict:
    input_dir = _input_dir(input_id)
    meta_path = input_dir / "meta.json"
    now = datetime.now(timezone.utc).isoformat()
    meta: dict = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    if created or "created_at" not in meta:
        meta["created_at"] = now
    meta["updated_at"] = now
    meta["input_id"] = input_id
    meta["filenames"] = filenames
    meta["path"] = str(input_dir)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def _public_input(input_id: str) -> dict:
    input_dir = _input_dir(input_id)
    if not input_dir.is_dir():
        raise HTTPException(status_code=404, detail="input set not found")
    filenames = _list_input_files(input_dir)
    meta_path = input_dir / "meta.json"
    meta: dict = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    return {
        "input_id": input_id,
        "filenames": filenames,
        "path": str(input_dir),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "job_ids": [
            jid
            for jid, job in JOBS.items()
            if job.get("input_id") == input_id
        ],
    }


async def _save_uploads(input_dir: Path, files: list[UploadFile] | None) -> list[str]:
    input_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for upload in files or []:
        if not upload.filename:
            continue
        safe = Path(upload.filename).name
        dest = input_dir / safe
        dest.write_bytes(await upload.read())
        saved.append(safe)
    return saved


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/v1/pipelines")
def api_list_pipelines() -> dict:
    """Baked pipelines + PVC custom agents (refreshed each call)."""
    return {"pipelines": list_pipelines()}


@app.get("/v1/agents")
def api_list_agents() -> dict:
    return {"agents": list_agents()}


@app.get("/v1/agents/{agent_id}")
def api_get_agent(agent_id: str) -> dict:
    from api.custom_agents import get_agent

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    try:
        rule = read_rule(agent_id)
    except ValueError:
        rule = ""
    return {"agent": agent, "rule": rule}


@app.post("/v1/agents")
async def api_create_agent(
    name: str = Form(...),
    abbrev: str = Form(...),
    goal: str = Form(...),
    output_hint: str = Form(""),
    blurb: str = Form(""),
    agent_id: str = Form(""),
    mode: str = Form("tool_loop"),
    tool_loop: str = Form(""),
    gate: str = Form("true"),
    generate_llm: str = Form("false"),
    rule_markdown: str = Form(""),
    stages_json: str = Form(""),
    verify_paths_json: str = Form(""),
    repair_prompt: str = Form(""),
) -> dict:
    """
    Create a custom agent on the PVC (no image rebuild).

    mode: ``tool_loop`` (Cursor-like tools) or ``single_shot`` (### FILE bundle).
    stages_json (optional): multi-stage pipeline like RDE Ansible+Backend::

        [{"abbrev":"ANS","mode":"tool_loop","output":"...","gate":true},
         {"abbrev":"BE","mode":"single_shot","output":"...","gate":false}]
    """
    stages = None
    raw_stages = (stages_json or "").strip()
    if raw_stages:
        try:
            parsed = json.loads(raw_stages)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"stages_json invalid: {exc}"
            ) from exc
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="stages_json must be a list")
        stages = parsed

    # Prefer explicit mode; fall back to tool_loop bool for older clients
    mode_val = (mode or "").strip()
    if not mode_val and tool_loop.strip():
        mode_val = (
            "tool_loop"
            if str(tool_loop).strip().lower() in {"1", "true", "yes", "on"}
            else "single_shot"
        )
    if not mode_val:
        mode_val = "tool_loop"

    # Parse verify_paths (JSON list of relative paths)
    verify_paths: list[str] | None = None
    raw_vp = (verify_paths_json or "").strip()
    if raw_vp:
        try:
            vp_parsed = json.loads(raw_vp)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"verify_paths_json invalid: {exc}"
            ) from exc
        if not isinstance(vp_parsed, list):
            raise HTTPException(
                status_code=400, detail="verify_paths_json must be a list"
            )
        verify_paths = [str(p).strip() for p in vp_parsed if str(p).strip()]

    try:
        result = create_agent(
            name=name,
            abbrev=abbrev,
            goal=goal,
            output_hint=output_hint,
            blurb=blurb,
            agent_id=agent_id,
            mode=mode_val,
            gate=str(gate).strip().lower() in {"1", "true", "yes", "on"},
            generate_llm=str(generate_llm).strip().lower()
            in {"1", "true", "yes", "on"},
            rule_markdown=rule_markdown,
            stages=stages,
            verify_paths=verify_paths,
            repair_prompt=(repair_prompt or "").strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@app.delete("/v1/agents/{agent_id}")
def api_delete_agent(agent_id: str) -> dict:
    try:
        return delete_agent(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/inputs")
def list_inputs() -> dict:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(INPUTS_DIR.iterdir()):
        if path.is_dir():
            try:
                items.append(_public_input(path.name))
            except HTTPException:
                continue
    return {"inputs": items}


@app.get("/v1/inputs/{input_id}")
def get_input(input_id: str) -> dict:
    return _public_input(_safe_id(input_id, label="input_id"))


@app.post("/v1/inputs")
async def create_or_update_input(
    input_id: str = Form(""),
    files: list[UploadFile] | None = File(None),
) -> dict:
    """Create or update an input set on the PVC. Multiple files allowed."""
    if input_id.strip():
        iid = _safe_id(input_id, label="input_id")
        created = not _input_dir(iid).is_dir()
    else:
        iid = str(uuid.uuid4())[:8]
        created = True
    saved = await _save_uploads(_input_dir(iid), files)
    filenames = _list_input_files(_input_dir(iid))
    if not filenames:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one file, or reuse an existing input_id that already has files.",
        )
    _write_input_meta(iid, filenames, created=created)
    result = _public_input(iid)
    result["uploaded"] = saved
    return result


@app.delete("/v1/inputs/{input_id}/files/{name}")
def delete_input_file(input_id: str, name: str) -> dict:
    iid = _safe_id(input_id, label="input_id")
    safe = Path(name).name
    path = _input_dir(iid) / safe
    if safe == "meta.json" or not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    path.unlink()
    filenames = _list_input_files(_input_dir(iid))
    if filenames:
        _write_input_meta(iid, filenames, created=False)
        return {"ok": True, "input_id": iid, "deleted": safe, "filenames": filenames}
    # Last file removed — drop the empty set
    meta = _input_dir(iid) / "meta.json"
    if meta.is_file():
        meta.unlink()
    try:
        _input_dir(iid).rmdir()
    except OSError:
        pass
    return {"ok": True, "input_id": iid, "deleted": safe, "filenames": [], "removed_set": True}


@app.delete("/v1/inputs/{input_id}")
def delete_input_set(input_id: str) -> dict:
    import shutil

    iid = _safe_id(input_id, label="input_id")
    path = _input_dir(iid)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="input set not found")
    shutil.rmtree(path)
    return {"ok": True, "input_id": iid, "deleted_set": True}


@app.post("/v1/jobs")
async def create_job(
    pipeline_id: str = Form(...),
    instructions: str = Form(""),
    gates_enabled: str = Form("true"),
    input_id: str = Form(""),
    files: list[UploadFile] | None = File(None),
) -> dict:
    """
    Start a job against an input set.

    - Provide ``input_id`` to reuse files already on the PVC.
    - Provide ``files`` (one or many) to create/update that input set.
    - Omit ``input_id`` to auto-generate one when uploading files.
    """
    try:
        pipeline = get_pipeline(pipeline_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    has_files = bool(files and any(f.filename for f in files))

    if input_id.strip():
        iid = _safe_id(input_id, label="input_id")
    elif has_files:
        iid = str(uuid.uuid4())[:8]
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide input_id to reuse files, and/or upload files for a new input set.",
        )

    input_dir = _input_dir(iid)
    created = not input_dir.is_dir()
    if has_files:
        await _save_uploads(input_dir, files)
    filenames = _list_input_files(input_dir)
    if not filenames:
        raise HTTPException(
            status_code=400,
            detail=f"Input set '{iid}' has no files. Upload files or pick another input_id.",
        )
    _write_input_meta(iid, filenames, created=created or has_files)

    job_id = str(uuid.uuid4())[:8]
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "output").mkdir(parents=True, exist_ok=True)

    # Small pointer so PVC shows job ↔ input linkage without copying files
    (job_dir / "input_id.txt").write_text(iid + "\n", encoding="utf-8")

    gates_on = str(gates_enabled).strip().lower() in {"1", "true", "yes", "on"}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job = {
        "id": job_id,
        "input_id": iid,
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline["name"],
        "filenames": filenames,
        "instructions": instructions,
        "gates_enabled": gates_on,
        "stages": pipeline["stages"],
        "status": "queued",
        "current_index": 0,
        "created_at": now,
        "started_at": now,
        "updated_at": now,
        "stage_timings": [],
        "logs": [
            "[queued] waiting for worker",
            f"[input] set={iid} files={', '.join(filenames)} path={input_dir}",
        ],
        "artifact_md": "",
        "input_path": str(input_dir),
        "output_path": str(job_dir / "output"),
    }
    if not gates_on:
        job["logs"].append("[info] gates disabled for this run — stages will not pause")
    JOBS[job_id] = job
    save_job(job)
    start_job_thread(job, DATA_DIR)
    return _public(job)


@app.get("/v1/jobs")
def list_jobs() -> dict:
    # Pick up any job.json written by other processes / recovered dirs
    for jid, job in load_all_jobs().items():
        if jid not in JOBS:
            JOBS[jid] = job
    return {"jobs": [_public(job) for job in JOBS.values()]}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        job = load_all_jobs().get(job_id)
        if job:
            JOBS[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return _public(job)


@app.post("/v1/jobs/{job_id}/approve")
async def approve_job_endpoint(
    job_id: str,
    edited_text: str | None = Form(None),
    follow_up: str = Form(""),
) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="job is not awaiting approval")
    try:
        text = edited_text if edited_text is not None else None
        if text is not None and text == job.get("pending_artifact"):
            text = None
        approve_and_continue(
            job,
            DATA_DIR,
            edited_text=text,
            follow_up=follow_up or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_job(job)
    return _public(job)


@app.post("/v1/jobs/{job_id}/reject")
async def reject_job_endpoint(
    job_id: str,
    reason: str = Form(""),
) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="job is not awaiting approval")
    try:
        reject_job(job, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_job(job)
    return _public(job)


@app.post("/v1/jobs/{job_id}/resume")
async def resume_job_endpoint(
    job_id: str,
    stage: str = Form("RDE"),
) -> dict:
    """
    Resume from a stage (RDA/RDE/AUTO/…) using existing Docling parse + prior outputs.
    Skips Docling and earlier stages.
    """
    job = JOBS.get(job_id)
    if not job:
        job = load_all_jobs().get(job_id)
        if job:
            JOBS[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    try:
        resume_job_from_stage(job, DATA_DIR, stage_abbrev=stage or "RDE")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_job(job)
    return _public(job)


@app.post("/v1/jobs/{job_id}/skip")
async def skip_job_endpoint(
    job_id: str,
    skip_rest: str = Form("false"),
) -> dict:
    """
    At a gate: skip the current agent and continue to the next.
    Set skip_rest=true to skip all remaining agents and finish the job.
    """
    job = JOBS.get(job_id)
    if not job:
        job = load_all_jobs().get(job_id)
        if job:
            JOBS[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    rest = str(skip_rest).strip().lower() in {"1", "true", "yes", "on"}
    try:
        skip_and_continue(job, DATA_DIR, skip_rest=rest)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_job(job)
    return _public(job)


@app.post("/v1/jobs/{job_id}/cancel")
def cancel_job_endpoint(job_id: str) -> dict:
    """Stop a running/queued job (Cursor-like Stop). Halts between agent steps."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    try:
        cancel_job(job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_job(job)
    return _public(job)


def _load_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        job = load_all_jobs().get(job_id)
        if job:
            JOBS[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/v1/jobs/{job_id}/cpat/deploy")
def cpat_deploy_status(job_id: str) -> dict:
    """CPAT deploy readiness + current status for a job."""
    return get_deploy_status(_load_job(job_id))


@app.post("/v1/jobs/{job_id}/cpat/deploy")
def cpat_deploy_start(job_id: str) -> dict:
    """
    Build & run the generated CPAT for this job.

    OpenShift (default when ``oc`` works): binary BuildConfig + Deployment + Route.
    Bastion: ``bringup.sh`` via podman/docker if SPRINTWEAVE_CPAT_DEPLOY_MODE=bringup.
    Otherwise writes manifests under output/cpat-openshift/ for manual ``oc`` apply.
    """
    job = _load_job(job_id)
    try:
        return start_deploy(job, DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/jobs/{job_id}/files/{name}")
def download_output(job_id: str, name: str) -> FileResponse:
    """Legacy single-segment download (basename only). Prefer /artifacts/."""
    if job_id not in JOBS and not (JOBS_DIR / job_id / "output").is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    path = JOBS_DIR / job_id / "output" / Path(name).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.get("/v1/jobs/{job_id}/artifacts")
def list_artifacts(job_id: str) -> dict:
    if (
        job_id not in JOBS
        and not (JOBS_DIR / job_id / "output").is_dir()
        and not (JOBS_DIR / job_id / "workspace" / "output").is_dir()
    ):
        raise HTTPException(status_code=404, detail="job not found")
    files = _list_job_artifacts(job_id)
    if job_id in JOBS:
        JOBS[job_id]["artifacts"] = files
        save_job(JOBS[job_id])
    return {
        "job_id": job_id,
        "output_path": str(JOBS_DIR / job_id / "output"),
        "files": files,
    }


@app.get("/v1/jobs/{job_id}/artifacts/{file_path:path}")
def download_artifact(job_id: str, file_path: str) -> FileResponse:
    if job_id not in JOBS and not (JOBS_DIR / job_id / "output").is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    path = _safe_artifact_path(job_id, file_path)
    return FileResponse(path, filename=path.name)


@app.get("/v1/jobs/{job_id}/artifacts.zip")
def download_artifacts_zip(job_id: str) -> StreamingResponse:
    if job_id not in JOBS and not (JOBS_DIR / job_id / "output").is_dir() and not (
        JOBS_DIR / job_id / "workspace" / "output"
    ).is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    roots = [
        JOBS_DIR / job_id / "output",
        JOBS_DIR / job_id / "workspace" / "output",
    ]
    buf = io.BytesIO()
    written = 0
    seen: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for out in roots:
            if not out.is_dir():
                continue
            for path in out.rglob("*"):
                if not path.is_file():
                    continue
                arc = path.relative_to(out).as_posix()
                if arc in seen:
                    continue
                seen.add(arc)
                zf.write(path, arcname=arc)
                written += 1
    if written == 0:
        raise HTTPException(status_code=404, detail="no artifacts")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="sprintweave-{job_id}-artifacts.zip"'
        },
    )
