"""PVC-backed custom agents — create once, no image rebuild.

Layout under SPRINTWEAVE_DATA_DIR (default /data):

  custom-agents/
    catalog.json
    rules/agent-<id>.md
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("SPRINTWEAVE_DATA_DIR", "/data"))
CUSTOM_ROOT = DATA_DIR / "custom-agents"
RULES_DIR = CUSTOM_ROOT / "rules"
CATALOG_PATH = CUSTOM_ROOT / "catalog.json"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_ABBREV_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,11}$")


def ensure_dirs() -> None:
    """Create PVC folders only — never write catalog here (avoids recursion)."""
    RULES_DIR.mkdir(parents=True, exist_ok=True)


def _write_catalog(catalog: dict[str, Any]) -> None:
    ensure_dirs()
    tmp = CATALOG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    tmp.replace(CATALOG_PATH)


def load_catalog() -> dict[str, Any]:
    ensure_dirs()
    if not CATALOG_PATH.is_file():
        empty = {"version": 1, "agents": [], "pipelines": []}
        _write_catalog(empty)
        return dict(empty)
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("agents", [])
    data.setdefault("pipelines", [])
    if not isinstance(data["agents"], list):
        data["agents"] = []
    if not isinstance(data["pipelines"], list):
        data["pipelines"] = []
    return data


def list_agents() -> list[dict[str, Any]]:
    return list(load_catalog().get("agents") or [])


def list_custom_pipelines() -> list[dict[str, Any]]:
    """Pipelines suitable for ui/pipelines merge (custom flag set)."""
    out: list[dict[str, Any]] = []
    for p in load_catalog().get("pipelines") or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        item = dict(p)
        item["custom"] = True
        out.append(item)
    return out


def get_agent(agent_id: str) -> dict[str, Any] | None:
    aid = (agent_id or "").strip().lower()
    for a in list_agents():
        if str(a.get("id", "")).lower() == aid:
            return a
    return None


def rule_path_for(agent: dict[str, Any]) -> Path:
    name = agent.get("rule_file") or f"agent-{agent.get('id', 'unknown')}.md"
    return RULES_DIR / Path(str(name)).name


def resolve_rule_file(
    *,
    agent_name: str = "",
    rule_file: str = "",
) -> Path | None:
    """Find a custom rule on PVC by explicit filename or agent display name."""
    ensure_dirs()
    rf = (rule_file or "").strip()
    if rf:
        path = RULES_DIR / Path(rf).name
        if path.is_file():
            return path
    name = (agent_name or "").strip()
    if not name:
        return None
    for a in list_agents():
        if str(a.get("name", "")).strip() == name:
            path = rule_path_for(a)
            if path.is_file():
                return path
    return None


def _slugify(raw: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (raw or "").strip().lower()).strip("-")
    return s[:48] or "agent"


def _default_rule_markdown(
    *,
    name: str,
    abbrev: str,
    goal: str,
    output_hint: str,
    verify_paths: list[str] | None = None,
) -> str:
    verify_block = ""
    if verify_paths:
        listing = "\n".join(f"- `{p}`" for p in verify_paths)
        verify_block = (
            f"\n## Required output files (verify_paths)\n"
            f"The following files MUST exist and be non-empty when you are done:\n"
            f"{listing}\n"
            "If any are missing after your main pass, go back and create them.\n"
        )
    return f"""# {name} ({abbrev})

You are the **{name}** agent running in SprintWeave on OpenShift.

## Goal
{goal.strip() or "Produce delivery artifacts from the uploaded input documents."}

## Inputs
- Prefer `parsed/*.md` (Docling markdown). Do not re-parse PDFs.
- Honour `@input` / `@cpat` / `@context` references in the user prompt.

## Outputs
Write all deliverables under `output/`.
{output_hint.strip() or "Create a clear folder under output/ for your artifacts and a short summary markdown report."}
{verify_block}
## Working style
- Use tools: list_dir, read_file, write_file, append_file, str_replace, run_python.
- Write real files; do not only describe what you would write.
- Prefer small focused files; edit with append_file/str_replace for large files.
- When done, leave a short quality summary listing paths written.
"""


def generate_rule_with_llm(
    *,
    name: str,
    abbrev: str,
    goal: str,
    output_hint: str,
) -> str:
    """Optional: ask the configured LLM to draft a richer agent rule (~$0.50–2)."""
    from llm.client import complete

    system = (
        "You write Cursor-style agent rule markdown for SprintWeave. "
        "Output ONLY the markdown rule file body — no code fences, no preamble."
    )
    user = (
        f"Create an agent rule for:\n"
        f"- Name: {name}\n"
        f"- Abbrev: {abbrev}\n"
        f"- Goal: {goal}\n"
        f"- Output hint: {output_hint or 'output/ artifacts + summary report'}\n\n"
        "Include: role, inputs (parsed/*.md), required output paths under output/, "
        "tooling style, and a short completeness checklist. Keep under 600 lines."
    )
    text = (complete(system, user) or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if len(text) < 80:
        raise RuntimeError("LLM returned an empty/short agent rule")
    return text


def _normalize_mode(raw: str | bool | None, *, default_tool_loop: bool = True) -> bool:
    """Return True for tool_loop, False for single_shot."""
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return default_tool_loop
    s = str(raw).strip().lower()
    if s in {"tool_loop", "tools", "loop", "1", "true", "yes", "on"}:
        return True
    if s in {"single_shot", "singleshot", "one_shot", "oneshot", "0", "false", "no", "off"}:
        return False
    return default_tool_loop


def _build_stages(
    *,
    display: str,
    abbrev: str,
    output_hint: str,
    gate: bool,
    tool_loop: bool,
    rule_file: str,
    stages_spec: list[dict[str, Any]] | None,
    verify_paths: list[str] | None = None,
    repair_prompt: str = "",
) -> list[dict[str, Any]]:
    """
    Build pipeline stages. Each stage can set mode independently:

      {"abbrev": "ANS", "output": "...", "mode": "tool_loop", "gate": true}
      {"abbrev": "BE",  "output": "...", "mode": "single_shot", "gate": false}

    Same agent rule is shared (like RDE sub-stages sharing RHOSO DE).
    """
    if not stages_spec:
        return [
            {
                "abbrev": abbrev,
                "agent": display,
                "output": output_hint,
                "gate": bool(gate),
                "tool_loop": bool(tool_loop),
                "mode": "tool_loop" if tool_loop else "single_shot",
                "rule_file": rule_file,
                "custom": True,
                "verify_paths": verify_paths or [],
                "repair_prompt": repair_prompt,
            }
        ]

    stages: list[dict[str, Any]] = []
    seen_abbrev: set[str] = set()
    for i, raw in enumerate(stages_spec):
        if not isinstance(raw, dict):
            raise ValueError(f"stages[{i}] must be an object")
        sab = str(raw.get("abbrev") or f"S{i+1}").strip().upper()
        if not _ABBREV_RE.match(sab):
            raise ValueError(f"stages[{i}].abbrev invalid: {sab}")
        if sab in seen_abbrev:
            raise ValueError(f"duplicate stage abbrev '{sab}'")
        seen_abbrev.add(sab)
        use_tools = _normalize_mode(
            raw.get("mode", raw.get("tool_loop")),
            default_tool_loop=tool_loop,
        )
        raw_vp = raw.get("verify_paths")
        stage_vp = list(raw_vp) if isinstance(raw_vp, list) else (verify_paths or [])
        stages.append(
            {
                "abbrev": sab,
                "agent": str(raw.get("agent") or display).strip() or display,
                "output": str(raw.get("output") or output_hint).strip()[:240],
                "gate": bool(raw["gate"]) if "gate" in raw else bool(gate),
                "tool_loop": use_tools,
                "mode": "tool_loop" if use_tools else "single_shot",
                "rule_file": str(raw.get("rule_file") or rule_file),
                "custom": True,
                "verify_paths": stage_vp,
                "repair_prompt": str(raw.get("repair_prompt") or repair_prompt),
            }
        )
    return stages


def create_agent(
    *,
    name: str,
    abbrev: str,
    goal: str,
    output_hint: str = "",
    blurb: str = "",
    tool_loop: bool = True,
    mode: str = "",
    gate: bool = True,
    agent_id: str = "",
    rule_markdown: str = "",
    generate_llm: bool = False,
    stages: list[dict[str, Any]] | None = None,
    verify_paths: list[str] | None = None,
    repair_prompt: str = "",
) -> dict[str, Any]:
    ensure_dirs()
    display = (name or "").strip()
    if not display:
        raise ValueError("name is required")
    ab = (abbrev or "").strip().upper()
    if not _ABBREV_RE.match(ab):
        raise ValueError(
            "abbrev must be 1–12 alphanumeric chars starting with a letter"
        )
    aid = _slugify(agent_id or display)
    if not _ID_RE.match(aid):
        raise ValueError("invalid agent id")

    use_tools = _normalize_mode(mode or tool_loop, default_tool_loop=bool(tool_loop))

    catalog = load_catalog()
    for a in catalog["agents"]:
        if str(a.get("id", "")).lower() == aid:
            raise ValueError(f"agent id '{aid}' already exists")
        if str(a.get("name", "")).strip() == display:
            raise ValueError(f"agent name '{display}' already exists")
        if str(a.get("abbrev", "")).upper() == ab:
            raise ValueError(f"abbrev '{ab}' already in use")

    rule_file = f"agent-{aid}.md"
    if generate_llm and not (rule_markdown or "").strip():
        body = generate_rule_with_llm(
            name=display,
            abbrev=ab,
            goal=goal,
            output_hint=output_hint,
        )
        generated = "llm"
    elif (rule_markdown or "").strip():
        body = rule_markdown.strip()
        generated = "paste"
    else:
        body = _default_rule_markdown(
            name=display,
            abbrev=ab,
            goal=goal,
            output_hint=output_hint,
            verify_paths=verify_paths,
        )
        generated = "template"

    path = RULES_DIR / rule_file
    path.write_text(body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_label = (output_hint or "Custom artifacts under output/").strip()
    pipe_stages = _build_stages(
        display=display,
        abbrev=ab,
        output_hint=out_label[:240],
        gate=gate,
        tool_loop=use_tools,
        rule_file=rule_file,
        stages_spec=stages,
        verify_paths=verify_paths,
        repair_prompt=repair_prompt,
    )
    agent = {
        "id": aid,
        "name": display,
        "abbrev": ab,
        "blurb": (blurb or goal or "Custom agent").strip()[:240],
        "goal": (goal or "").strip(),
        "output": out_label[:240],
        "rule_file": rule_file,
        "tool_loop": bool(use_tools),
        "mode": "tool_loop" if use_tools else "single_shot",
        "gate": bool(gate),
        "stages": pipe_stages,
        "generated": generated,
        "verify_paths": verify_paths or [],
        "repair_prompt": repair_prompt,
        "created_at": now,
        "updated_at": now,
    }
    pipeline = {
        "id": f"custom-{aid}",
        "name": display,
        "blurb": agent["blurb"],
        "command": f"Run {display} pipeline on @input",
        "custom": True,
        "stages": pipe_stages,
    }

    catalog["agents"].append(agent)
    # Replace pipeline with same id if somehow present
    catalog["pipelines"] = [
        p for p in catalog["pipelines"] if str(p.get("id")) != pipeline["id"]
    ]
    catalog["pipelines"].append(pipeline)
    _write_catalog(catalog)

    return {
        "agent": agent,
        "pipeline": pipeline,
        "rule_path": str(path),
        "generated": generated,
    }


def delete_agent(agent_id: str) -> dict[str, Any]:
    ensure_dirs()
    aid = (agent_id or "").strip().lower()
    catalog = load_catalog()
    agent = None
    kept: list[dict[str, Any]] = []
    for a in catalog["agents"]:
        if str(a.get("id", "")).lower() == aid:
            agent = a
        else:
            kept.append(a)
    if agent is None:
        raise ValueError(f"agent '{agent_id}' not found")

    pipe_id = f"custom-{aid}"
    catalog["agents"] = kept
    catalog["pipelines"] = [
        p for p in catalog["pipelines"] if str(p.get("id", "")).lower() != pipe_id
    ]
    _write_catalog(catalog)

    path = rule_path_for(agent)
    if path.is_file():
        path.unlink()

    return {"ok": True, "deleted": aid, "pipeline_id": pipe_id}


def read_rule(agent_id: str) -> str:
    agent = get_agent(agent_id)
    if not agent:
        raise ValueError(f"agent '{agent_id}' not found")
    path = rule_path_for(agent)
    if not path.is_file():
        raise ValueError(f"rule file missing for '{agent_id}'")
    return path.read_text(encoding="utf-8")
