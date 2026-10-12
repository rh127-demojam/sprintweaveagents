"""Pipeline catalog shown in the UI.

Full catalog lives here. At runtime (or bake time via Dockerfile ENV), set
``SPRINTWEAVE_PIPELINES`` to a comma-separated list of pipeline ids to expose
only those. Empty / ``all`` / ``*`` = show every pipeline.

Examples:
  SPRINTWEAVE_PIPELINES=lab-requirements,rhoso
  docker build --build-arg PIPELINES=lab-requirements,rhoso ...
"""

from __future__ import annotations

import os

ALL_PIPELINES = [
    {
        "id": "standard",
        "name": "Standard",
        "blurb": "Stories, tests, runbook, sprint plan",
        "command": "Run Standard delivery pipeline on @input",
        "stages": [
            {
                "abbrev": "REQ",
                "agent": "Requirements Analyst",
                "output": "Stories, NFRs",
                "gate": True,
            },
            {"abbrev": "QA", "agent": "QA Architect", "output": "Test Cases"},
            {"abbrev": "OPS", "agent": "DevOps Engineer", "output": "Runbook"},
            {
                "abbrev": "SPR",
                "agent": "Sprint Coach",
                "output": "Sprint Plan",
                "gate": True,
            },
        ],
    },
    {
        "id": "lab-requirements",
        "name": "Lab Requirements",
        "blurb": "Sizing workbook from input docs (quick test)",
        "command": (
            "Run Lab Requirements pipeline on @input — produce lab sizing workbook. "
            "Read ONLY parsed/*.md (Docling already ran). Do NOT pip install or open PDFs. "
            "Build output/lab-requirements/generate_lab_requirements_workbook.py like Cursor: "
            "short write_file skeleton, then append_file/str_replace hunks, then one run_python. "
            "Do not rewrite the whole file repeatedly."
        ),
        "stages": [
            {
                "abbrev": "RDA",
                "agent": "RHOSO DA",
                "output": "Lab Requirements workbook",
                "gate": True,
            },
        ],
    },
    {
        "id": "rhoso",
        "name": "RHOSO",
        "blurb": "CIQ, MoP, optional automation / QA / docs",
        "command": (
            "Run RHOSO delivery pipeline on @cpat. "
            "Full document content is in the prompt — write deliverables immediately. "
            "Edit files in hunks (append_file/str_replace), not full rewrites. "
            "FORBIDDEN: run_python(code=...) to read parsed files."
        ),
        "stages": [
            {
                "abbrev": "RDA",
                "agent": "RHOSO DA",
                "output": "CIQ reference, topology, gaps",
                "gate": True,
            },
            {
                "abbrev": "RDE",
                "agent": "RHOSO Deployment Engineer",
                "output": "Workflow MoP, manifests",
                "gate": True,
            },
            {"abbrev": "AUTO", "agent": "Automation Engineer", "output": "Playbook (if requested)", "optional": True},
            {"abbrev": "QA", "agent": "QA Architect", "output": "Deployment tests (if requested)", "optional": True},
            {"abbrev": "DOC", "agent": "Technical Writer", "output": "Admin / user guides (if requested)", "optional": True},
        ],
    },
    {
        "id": "nrho",
        "name": "NRHO",
        "blurb": "NRHO DA + deployment engineer pack",
        "command": "Run NRHO pipeline on @input",
        "stages": [
            {
                "abbrev": "NDA",
                "agent": "NRHO DA",
                "output": "MoP / AIQ parameter pack",
                "gate": True,
            },
            {
                "abbrev": "NDE",
                "agent": "NRHO Deployment Engineer",
                "output": "Workflow MoP, coverage",
                "gate": True,
            },
            {"abbrev": "AUTO", "agent": "Automation Engineer", "output": "Ansible wrap (if requested)"},
            {"abbrev": "QA", "agent": "QA Architect", "output": "DVTS / ATP (if requested)"},
            {"abbrev": "DOC", "agent": "Technical Writer", "output": "Operator guide (if requested)"},
        ],
    },
    {
        "id": "nrho-delivery",
        "name": "NRHO Delivery",
        "blurb": "AIQ + CPAT-style delivery tree",
        "command": "Run NRHO delivery pipeline on @cpat",
        "stages": [
            {
                "abbrev": "NDA",
                "agent": "NRHO DA",
                "output": "Parameter pack, gaps",
                "gate": True,
            },
            {
                "abbrev": "AIQ",
                "agent": "NRHO DA",
                "output": "AIQ schema + workbooks",
                "gate": True,
            },
            {
                "abbrev": "NDE",
                "agent": "NRHO Deployment Engineer",
                "output": "Coverage, Delta backlog, MoP",
            },
            {
                "abbrev": "CPAT",
                "agent": "NRHO Deployment Engineer",
                "output": "CPAT tree under output",
                "gate": True,
            },
        ],
    },
    {
        "id": "governance",
        "name": "Governance",
        "blurb": "Risk, compliance, status update",
        "command": "Run Governance pipeline on @input",
        "stages": [
            {
                "abbrev": "GOV",
                "agent": "Governance Specialist",
                "output": "Risk, Compliance",
                "gate": True,
            },
            {
                "abbrev": "PM",
                "agent": "Project Manager",
                "output": "Status Update",
                "gate": True,
            },
        ],
    },
]


def _selected_ids() -> list[str] | None:
    raw = os.environ.get("SPRINTWEAVE_PIPELINES", "").strip()
    if not raw or raw.lower() in {"all", "*", "full"}:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_custom_pipelines() -> list[dict]:
    """Merge PVC custom agents (no rebuild). Safe if api package unavailable."""
    try:
        from api.custom_agents import list_custom_pipelines  # type: ignore

        return list_custom_pipelines()
    except Exception:
        # UI container may not share api package path; try DATA_DIR directly
        pass
    try:
        import json
        from pathlib import Path

        root = Path(os.environ.get("SPRINTWEAVE_DATA_DIR", "/data"))
        catalog = root / "custom-agents" / "catalog.json"
        if not catalog.is_file():
            return []
        data = json.loads(catalog.read_text(encoding="utf-8"))
        out = []
        for p in data.get("pipelines") or []:
            if isinstance(p, dict) and p.get("id"):
                item = dict(p)
                item["custom"] = True
                out.append(item)
        return out
    except Exception:
        return []


def _active_pipelines() -> list[dict]:
    ids = _selected_ids()
    baked = list(ALL_PIPELINES)
    custom = _load_custom_pipelines()
    # Custom always visible (created at runtime); baked filtered by ENV
    if ids is None:
        base = baked
    else:
        by_id = {p["id"]: p for p in baked}
        base = [by_id[i] for i in ids if i in by_id] or baked
    # Avoid id collisions — custom wins
    custom_ids = {p["id"] for p in custom}
    merged = [p for p in base if p["id"] not in custom_ids] + custom
    return merged


def list_pipelines() -> list[dict]:
    """Fresh merge of baked + PVC custom pipelines (call each request)."""
    return _active_pipelines()


# Backward-compatible snapshot (may be stale for custom agents — prefer list_pipelines()).
PIPELINES = _active_pipelines()


def get_pipeline(pipeline_id: str) -> dict:
    pipelines = list_pipelines()
    for item in pipelines:
        if item["id"] == pipeline_id:
            return item
    if not pipelines:
        raise KeyError(f"pipeline '{pipeline_id}' not found (empty catalog)")
    # Unknown id: do not silently run the wrong pipeline
    raise KeyError(f"pipeline '{pipeline_id}' not found")


def default_command(pipeline: dict, input_id: str = "") -> str:
    """Cursor-style run prompt (statement + @ refs), like colleague dashboard commands."""
    base = (pipeline.get("command") or f"Run {pipeline.get('name', 'pipeline')} on @input").strip()
    iid = (input_id or "").strip()
    if not iid:
        return base
    # Attach input set mention if not already present
    if f"@input:{iid}" in base or f"@{iid}" in base:
        return base
    if "@input" in base:
        return base.replace("@input", f"@input:{iid}", 1)
    return f"{base} using @input:{iid}"
