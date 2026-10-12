"""LangGraph tool-agent runtime (optional).

LLM calls go through ``llm.client.complete_tools`` (SSE streaming keep-alive),
same as the legacy loop — not non-streaming ChatOpenAI.

Feature flags:
  SPRINTWEAVE_USE_LANGGRAPH=true|false
  SPRINTWEAVE_LANGGRAPH_SCOPE=ansible|custom|all
  SPRINTWEAVE_LANGGRAPH_KEEPALIVE=true  (always uses complete_tools when true)

On failure → legacy agent_runtime in RESUME mode (avoid full rewrite).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, TypedDict

from api.agent_runtime import (
    TOOL_SCHEMAS,
    AgentCancelled,
    TOOL_RESULT_MAX,
    WorkspaceTools,
    compact_messages,
    reject_if_write_only,
    run_agent_loop,
    tool_schemas,
    COMPACT_KEEP_TURNS,
    FORCE_WRITE_AFTER_STEP,
    MAX_STEPS,
)
from llm.client import complete_tools

USE_LANGGRAPH = os.environ.get("SPRINTWEAVE_USE_LANGGRAPH", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LANGGRAPH_SCOPE = os.environ.get("SPRINTWEAVE_LANGGRAPH_SCOPE", "ansible").strip().lower()


def langgraph_enabled_for(scope: str) -> bool:
    """``scope`` is one of: ansible | custom | rde | rda | all."""
    if not USE_LANGGRAPH:
        return False
    want = (scope or "").strip().lower()
    raw = LANGGRAPH_SCOPE.strip().lower()
    if raw in {"all", "*"}:
        return True
    allowed = {p.strip() for p in raw.split(",") if p.strip()}
    return want in allowed


def langgraph_importable() -> bool:
    try:
        import langgraph  # noqa: F401
        from langgraph.graph import StateGraph  # noqa: F401
    except ImportError:
        return False
    return True


def _output_file_count(workspace: Path) -> int:
    root = workspace / "output"
    if not root.is_dir():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def _resume_user_suffix(workspace: Path) -> str:
    n = _output_file_count(workspace)
    if n <= 0:
        return ""
    sample: list[str] = []
    root = workspace / "output"
    for p in sorted(root.rglob("*")):
        if p.is_file():
            sample.append(p.relative_to(workspace).as_posix())
        if len(sample) >= 40:
            break
    listing = "\n".join(f"- {s}" for s in sample)
    return (
        "\n\n---\nRESUME MODE (previous engine failed mid-run):\n"
        f"There are already ~{n} files under output/. Examples:\n{listing}\n"
        "Do NOT rewrite complete existing files.\n"
        "Only create MISSING paths; use append_file/str_replace for edits.\n"
    )


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    step: int
    final_text: str
    done: bool
    force_write_nudged: bool


# ── Verify + Repair (Cursor parity) ──────────────────────────

REPAIR_MAX_STEPS = max(1, int(os.environ.get("SPRINTWEAVE_REPAIR_MAX_STEPS", "8")))


def _verify_paths(workspace: Path, paths: list[str]) -> tuple[list[str], list[str]]:
    """Check which verify_paths exist and are non-empty. Returns (found, missing)."""
    found: list[str] = []
    missing: list[str] = []
    for rel in paths:
        p = workspace / rel
        if p.is_file() and p.stat().st_size > 0:
            found.append(rel)
        else:
            missing.append(rel)
    return found, missing


def _build_repair_prompt(
    missing: list[str],
    repair_prompt: str = "",
) -> str:
    """Build a repair prompt listing missing files — like Cursor's validate+fix loop."""
    listing = "\n".join(f"- `{p}` — MISSING or empty" for p in missing)
    base = (
        "SELF-CHECK FAILED — the following required output files are missing:\n"
        f"{listing}\n\n"
        "You MUST create these files now. Use read_file to check what exists, "
        "then write_file to create the missing ones. "
        "Do NOT recreate files that already exist and are correct.\n"
    )
    if repair_prompt:
        base += f"\nAdditional repair instructions:\n{repair_prompt}\n"
    return base


def run_langgraph_agent_loop(
    *,
    workspace: Path,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    max_steps: int | None = None,
    should_cancel: Callable[[], bool] | None = None,
    verify_paths: list[str] | None = None,
    repair_prompt: str = "",
    write_only: bool = False,
) -> str:
    """
    LangGraph StateGraph tool loop using MaaS streaming keep-alive
    (llm.client.complete_tools).
    """
    from langgraph.graph import END, StateGraph

    steps = max_steps if max_steps is not None else MAX_STEPS
    tools = WorkspaceTools(workspace)
    # If output already has files (resume / prior round), don't force-write nudge
    if _output_file_count(workspace) > 0:
        tools.wrote_deliverable = True

    schemas = tool_schemas(write_only=write_only)
    mode = "write_only" if write_only else "full"
    logs.append(
        f"[langgraph] start keepalive-graph max_steps={steps} tools={mode} "
        "(llm.client.complete_tools stream)"
    )
    if on_log:
        on_log()

    def llm_node(state: AgentState) -> AgentState:
        if should_cancel and should_cancel():
            raise AgentCancelled("cancelled during langgraph llm node")
        step = int(state.get("step") or 0) + 1
        messages = list(state.get("messages") or [])
        messages, n_compact = compact_messages(messages)
        if n_compact:
            logs.append(
                f"[langgraph] compacted {n_compact} older tool result(s) "
                f"(keep last {COMPACT_KEEP_TURNS} turns)"
            )
        logs.append(f"[langgraph] step {step}/{steps}")
        if on_log:
            on_log()

        result = complete_tools(messages, schemas, tool_choice="auto")
        content = result.get("content") or ""
        tool_calls = result.get("tool_calls") or []
        raw_message = result.get("raw_message") or {
            "role": "assistant",
            "content": content,
        }
        messages.append(raw_message)
        final_text = content or state.get("final_text") or ""

        if not tool_calls:
            logs.append(f"[langgraph] finished at step {step} (no more tools)")
            if on_log:
                on_log()
            return {
                "messages": messages,
                "step": step,
                "final_text": final_text,
                "done": True,
                "force_write_nudged": bool(state.get("force_write_nudged")),
            }

        for call in tool_calls:
            if should_cancel and should_cancel():
                raise AgentCancelled("cancelled during langgraph tools")
            name = call.get("name") or ""
            args = call.get("arguments") or {}
            call_id = call.get("id") or f"call_{step}"
            arg_preview = json.dumps(args)[:200]
            logs.append(f"[lg-tool] {name}({arg_preview})")
            if on_log:
                on_log()
            banned = reject_if_write_only(name, write_only=write_only)
            tool_result = banned if banned else tools.dispatch(name, args)
            if len(tool_result) > TOOL_RESULT_MAX:
                tool_result = tool_result[:TOOL_RESULT_MAX] + "\n... truncated"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_result,
                }
            )

        force_nudged = bool(state.get("force_write_nudged"))
        if (
            FORCE_WRITE_AFTER_STEP
            and step >= FORCE_WRITE_AFTER_STEP
            and not tools.wrote_deliverable
            and not force_nudged
        ):
            force_nudged = True
            logs.append(
                f"[langgraph] force-write nudge after step {step} "
                "(no output/ files yet)"
            )
            if on_log:
                on_log()
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "STOP exploring. You have not written any file under output/. "
                        "Next actions MUST write under output/cpat/ansible/ "
                        "(write_file / append_file), not only read_file."
                    ),
                }
            )

        done = step >= steps
        if done:
            logs.append(f"[langgraph] hit max_steps={steps}")
            if on_log:
                on_log()

        return {
            "messages": messages,
            "step": step,
            "final_text": final_text,
            "done": done,
            "force_write_nudged": force_nudged,
        }

    def route(state: AgentState) -> str:
        if state.get("done"):
            return END
        return "agent"

    graph = StateGraph(AgentState)
    graph.add_node("agent", llm_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route)

    app = graph.compile()
    initial: AgentState = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "step": 0,
        "final_text": "",
        "done": False,
        "force_write_nudged": False,
    }
    # LangGraph may cap recursion; allow 2x steps
    final_state = app.invoke(initial, config={"recursion_limit": max(10, steps * 2 + 5)})
    final_text = (final_state or {}).get("final_text") or ""
    step = int((final_state or {}).get("step") or 0)
    logs.append(f"[langgraph] finished steps≈{step} keepalive=maas-stream")
    if on_log:
        on_log()

    # ── Verify + Repair loop (Cursor parity) ──────────────────
    if verify_paths:
        found, missing = _verify_paths(workspace, verify_paths)
        logs.append(
            f"[verify] {len(found)}/{len(verify_paths)} paths present, "
            f"{len(missing)} missing"
        )
        if on_log:
            on_log()
        if missing:
            repair_msg = _build_repair_prompt(missing, repair_prompt)
            logs.append(
                f"[repair] starting repair pass ({len(missing)} missing files, "
                f"max {REPAIR_MAX_STEPS} steps)"
            )
            if on_log:
                on_log()
            repair_state: AgentState = {
                "messages": list((final_state or {}).get("messages") or []) + [
                    {"role": "user", "content": repair_msg},
                ],
                "step": 0,
                "final_text": final_text,
                "done": False,
                "force_write_nudged": True,
            }
            repair_graph = StateGraph(AgentState)
            repair_graph.add_node("agent", llm_node)
            repair_graph.set_entry_point("agent")
            repair_graph.add_conditional_edges("agent", route)
            repair_app = repair_graph.compile()
            try:
                repair_final = repair_app.invoke(
                    repair_state,
                    config={"recursion_limit": max(10, REPAIR_MAX_STEPS * 2 + 5)},
                )
                repair_step = int((repair_final or {}).get("step") or 0)
                final_text = (repair_final or {}).get("final_text") or final_text
                logs.append(f"[repair] completed {repair_step} step(s)")
            except Exception as repair_exc:
                logs.append(
                    f"[repair] FAILED ({type(repair_exc).__name__}: {repair_exc})"
                )
            if on_log:
                on_log()
            found2, missing2 = _verify_paths(workspace, verify_paths)
            logs.append(
                f"[verify-post-repair] {len(found2)}/{len(verify_paths)} present, "
                f"{len(missing2)} still missing"
            )
            if on_log:
                on_log()

    if not str(final_text).strip():
        final_text = (
            f"LangGraph agent completed {step} step(s). "
            "See workspace/output for generated files."
        )
    return str(final_text)


def run_langgraph_complete_bundle(
    *,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    label: str = "bundle",
) -> list[tuple[str, str]]:
    """
    One LangGraph node: streaming ``complete()`` → parse ### FILE blocks.
    Does not write files (caller writes). Used by RDE Backend/Frontend/Docker.
    """
    from langgraph.graph import END, StateGraph
    from llm.client import complete
    from api.worker import _parse_file_bundle

    class BundleState(TypedDict, total=False):
        files: list[tuple[str, str]]

    def generate(_state: BundleState) -> BundleState:
        if should_cancel and should_cancel():
            raise AgentCancelled("cancelled during langgraph bundle")
        logs.append(f"[langgraph] {label} single-shot complete() stream")
        if on_log:
            on_log()
        text = complete(system, user)
        return {"files": _parse_file_bundle(text)}

    graph = StateGraph(BundleState)
    graph.add_node("generate", generate)
    graph.set_entry_point("generate")
    graph.add_edge("generate", END)
    app = graph.compile()
    final = app.invoke({"files": []}, config={"recursion_limit": 4})
    return list((final or {}).get("files") or [])


def run_langgraph_single_shot(
    *,
    workspace: Path,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    label: str = "single-shot",
    max_retries: int = 1,
) -> str:
    """
    LangGraph one-shot: ``complete()`` (streaming keep-alive) → parse ### FILE → write.
    Optional one retry if the model returns no file blocks.
    """
    from langgraph.graph import END, StateGraph
    from llm.client import complete

    # Lazy import avoids circular import at module load (worker imports us).
    from api.worker import _parse_file_bundle

    tools = WorkspaceTools(workspace)

    class ShotState(TypedDict, total=False):
        system: str
        user: str
        attempt: int
        files: list[tuple[str, str]]
        written: list[str]
        done: bool

    logs.append(f"[langgraph] {label} single-shot start (complete() stream)")
    if on_log:
        on_log()

    def generate(state: ShotState) -> ShotState:
        if should_cancel and should_cancel():
            raise AgentCancelled("cancelled during langgraph single-shot")
        attempt = int(state.get("attempt") or 0) + 1
        extra = ""
        if attempt > 1:
            extra = (
                "\n\nRETRY: Previous reply had no ### FILE blocks. "
                "Emit the file bundle now using ### FILE: output/...\n"
            )
            logs.append(f"[langgraph] {label} single-shot retry {attempt}")
            if on_log:
                on_log()
        text = complete(state["system"], state["user"] + extra)
        files = _parse_file_bundle(text)
        return {
            "attempt": attempt,
            "files": files,
            "written": list(state.get("written") or []),
            "done": False,
            "system": state["system"],
            "user": state["user"],
        }

    def write_files(state: ShotState) -> ShotState:
        files = list(state.get("files") or [])
        written = list(state.get("written") or [])
        for path, content in files:
            tools._write_counts.pop(path, None)
            tools.write_file(path, content)
            written.append(path)
        logs.append(f"[langgraph] {label} wrote {len(files)} file(s)")
        if on_log:
            on_log()
        return {
            **state,
            "written": written,
            "done": True,
        }

    def route_after_generate(state: ShotState) -> str:
        files = state.get("files") or []
        attempt = int(state.get("attempt") or 0)
        if files:
            return "write"
        if attempt <= max_retries:
            return "generate"
        return END

    graph = StateGraph(ShotState)
    graph.add_node("generate", generate)
    graph.add_node("write", write_files)
    graph.set_entry_point("generate")
    graph.add_conditional_edges("generate", route_after_generate)
    graph.add_edge("write", END)
    app = graph.compile()

    final = app.invoke(
        {
            "system": system,
            "user": user,
            "attempt": 0,
            "files": [],
            "written": [],
            "done": False,
        },
        config={"recursion_limit": 6},
    )
    written = list((final or {}).get("written") or [])
    if not written:
        raise RuntimeError(f"langgraph single-shot {label}: no ### FILE blocks")
    listing = "\n".join(f"- `{p}`" for p in written)
    logs.append(f"[langgraph] {label} single-shot done ({len(written)} files)")
    if on_log:
        on_log()
    return f"LangGraph single-shot {label} wrote {len(written)} files:\n{listing}\n"


def run_single_shot_agent(
    *,
    workspace: Path,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    scope: str = "rde",
    label: str = "single-shot",
    legacy_fn: Callable[[], str] | None = None,
) -> str:
    """LangGraph single-shot when enabled for scope; else ``legacy_fn``."""
    if langgraph_enabled_for(scope) and langgraph_importable():
        try:
            return run_langgraph_single_shot(
                workspace=workspace,
                system=system,
                user=user,
                logs=logs,
                on_log=on_log,
                should_cancel=should_cancel,
                label=label,
            )
        except AgentCancelled:
            raise
        except Exception as exc:
            logs.append(
                f"[langgraph] single-shot FAILED ({type(exc).__name__}: {exc}) — "
                "falling back to legacy single-shot"
            )
            if on_log:
                on_log()
            if legacy_fn is not None:
                return legacy_fn()
            raise
    if legacy_fn is not None:
        return legacy_fn()
    raise RuntimeError("single-shot: LangGraph disabled and no legacy_fn provided")


def run_tool_agent(
    *,
    workspace: Path,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    max_steps: int | None = None,
    should_cancel: Callable[[], bool] | None = None,
    scope: str = "ansible",
    verify_paths: list[str] | None = None,
    repair_prompt: str = "",
    write_only: bool = False,
) -> str:
    """Prefer LangGraph+keepalive; on failure legacy RESUME (no cold rewrite)."""
    if langgraph_enabled_for(scope) and langgraph_importable():
        try:
            return run_langgraph_agent_loop(
                workspace=workspace,
                system=system,
                user=user,
                logs=logs,
                on_log=on_log,
                max_steps=max_steps,
                should_cancel=should_cancel,
                verify_paths=verify_paths,
                repair_prompt=repair_prompt,
                write_only=write_only,
            )
        except AgentCancelled:
            raise
        except Exception as exc:
            n_existing = _output_file_count(workspace)
            logs.append(
                f"[langgraph] FAILED ({type(exc).__name__}: {exc}) — "
                f"falling back to legacy RESUME (output files≈{n_existing})"
            )
            if on_log:
                on_log()
            return run_agent_loop(
                workspace=workspace,
                system=system,
                user=user + _resume_user_suffix(workspace),
                logs=logs,
                on_log=on_log,
                max_steps=max_steps,
                should_cancel=should_cancel,
                resume_existing=True,
                write_only=write_only,
            )
    elif langgraph_enabled_for(scope) and not langgraph_importable():
        logs.append(
            "[langgraph] enabled but packages missing — using legacy "
            "(pip install langgraph)"
        )
        if on_log:
            on_log()

    return run_agent_loop(
        workspace=workspace,
        system=system,
        user=user,
        logs=logs,
        on_log=on_log,
        max_steps=max_steps,
        should_cancel=should_cancel,
        write_only=write_only,
    )
