"""Cursor-like tool-calling agent loop jailed to a job workspace."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

from llm.client import complete_tools

MAX_STEPS = int(os.environ.get("SPRINTWEAVE_AGENT_MAX_STEPS", "60"))
READ_MAX = int(os.environ.get("SPRINTWEAVE_AGENT_READ_MAX", "120000"))
LIST_MAX = int(os.environ.get("SPRINTWEAVE_AGENT_LIST_MAX", "200"))
PYTHON_TIMEOUT = int(os.environ.get("SPRINTWEAVE_AGENT_PYTHON_TIMEOUT", "300"))
TOOL_RESULT_MAX = int(os.environ.get("SPRINTWEAVE_AGENT_TOOL_RESULT_MAX", "40000"))
# History compaction: keep system + first user + last N tool-turns full;
# older tool results become one-line summaries (flat tokens per step).
COMPACT_ENABLED = os.environ.get("SPRINTWEAVE_AGENT_COMPACT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
COMPACT_KEEP_TURNS = max(1, int(os.environ.get("SPRINTWEAVE_AGENT_COMPACT_KEEP_TURNS", "3")))
COMPACT_SUMMARY_MAX = max(40, int(os.environ.get("SPRINTWEAVE_AGENT_COMPACT_SUMMARY_MAX", "180")))
# Inline run_python(code=...) that reads parsed/ is the #1 token burner — refuse it.
# Default false: only script_path= (forces write generator first). Set true to allow -c.
ALLOW_PYTHON_INLINE = os.environ.get(
    "SPRINTWEAVE_AGENT_PYTHON_INLINE", "false"
).strip().lower() in {"1", "true", "yes"}
FORCE_WRITE_AFTER_STEP = max(
    0, int(os.environ.get("SPRINTWEAVE_AGENT_FORCE_WRITE_AFTER_STEP", "3"))
)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories under a path relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path (default '.').",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a text file (Cursor-like Apply for new files). "
                "Use for a SHORT skeleton only. To grow a large file, prefer "
                "append_file / str_replace — do not rewrite the whole file repeatedly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": (
                "Cursor-like search/replace in an existing file. Replaces ONE occurrence "
                "of old_text with new_text. Prefer this over rewrite write_file for edits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "replace_all": {
                        "type": "boolean",
                        "description": "If true, replace every occurrence (default false).",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": (
                "Append text to an existing file (or create it). Use to build large "
                "generators in hunks like Cursor incremental Apply — not full rewrites."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Run a workspace .py file via script_path (preferred), usually after you "
                "wrote a generator under output/. Do NOT use inline code to print/read "
                "parsed/*.md — use search_files or read_file once, then write files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "code": {"type": "string"},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional argv for script_path.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Search for a text pattern in files under a workspace path "
                "(case-insensitive substring). Returns matching file:line snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for."},
                    "path": {
                        "type": "string",
                        "description": "Relative directory or file (default '.').",
                    },
                    "glob": {
                        "type": "string",
                        "description": "Optional suffix filter, e.g. '.md' or '.py'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

SEARCH_MAX_HITS = int(os.environ.get("SPRINTWEAVE_AGENT_SEARCH_MAX", "40"))
# Stop models from rewriting the same path forever (e.g. huge generator scripts).
WRITE_SAME_PATH_MAX = int(os.environ.get("SPRINTWEAVE_WRITE_SAME_PATH_MAX", "2"))


class PathJailError(ValueError):
    pass


def _looks_like_parsed_dump(code: str) -> bool:
    """True if inline python is being used to scrape/print parsed or input docs."""
    lower = (code or "").lower()
    if not lower.strip():
        return False
    touches_docs = any(
        marker in lower
        for marker in (
            "parsed/",
            "parsed\\",
            '"parsed',
            "'parsed",
            "input/",
            "input\\",
        )
    )
    if not touches_docs:
        return False
    return any(
        marker in lower
        for marker in ("open(", "readlines", ".read(", "path(", "print(")
    )


class WorkspaceTools:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._write_counts: dict[str, int] = {}
        self.wrote_deliverable = False

    def resolve(self, rel: str) -> Path:
        raw = (rel or ".").strip() or "."
        candidate = (self.root / raw).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise PathJailError(f"path escapes workspace: {rel}") from exc
        return candidate

    def list_dir(self, path: str = ".") -> str:
        target = self.resolve(path)
        if not target.exists():
            return f"ERROR: path not found: {path}"
        if not target.is_dir():
            return f"ERROR: not a directory: {path}"
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines: list[str] = []
        for entry in entries[:LIST_MAX]:
            kind = "dir" if entry.is_dir() else "file"
            size = entry.stat().st_size if entry.is_file() else 0
            rel = entry.relative_to(self.root).as_posix()
            lines.append(f"{kind}\t{size}\t{rel}")
        if len(entries) > LIST_MAX:
            lines.append(f"... truncated ({len(entries)} total)")
        return "\n".join(lines) if lines else "(empty)"

    def read_file(self, path: str) -> str:
        target = self.resolve(path)
        if not target.is_file():
            return f"ERROR: file not found: {path}"
        data = target.read_bytes()
        if b"\x00" in data[:2048]:
            return f"ERROR: binary file ({len(data)} bytes): {path}"
        text = data.decode("utf-8", errors="replace")
        if len(text) > READ_MAX:
            return text[:READ_MAX] + f"\n\n... truncated ({len(text)} chars total)"
        return text

    def write_file(self, path: str, content: str) -> str:
        target = self.resolve(path)
        rel = target.relative_to(self.root).as_posix()
        if rel.startswith("output/"):
            self.wrote_deliverable = True
        count = self._write_counts.get(rel, 0) + 1
        self._write_counts[rel] = count
        if count > WRITE_SAME_PATH_MAX:
            return (
                f"ERROR: refused rewrite #{count} of {rel} "
                f"(limit SPRINTWEAVE_WRITE_SAME_PATH_MAX={WRITE_SAME_PATH_MAX}). "
                f"File already on disk ({target.stat().st_size if target.is_file() else 0} bytes). "
                "Do NOT write_file again. Call run_python with script_path="
                f"'{rel}' now (or stop if already done)."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        body = content if content is not None else ""
        target.write_text(body, encoding="utf-8")
        hint = ""
        if count >= WRITE_SAME_PATH_MAX:
            hint = (
                f" WARNING: this is write #{count}/{WRITE_SAME_PATH_MAX} for this path. "
                "Next rewrite will be refused. Call run_python on this script next."
            )
        return (
            f"OK wrote {rel} ({len(body)} chars) [write {count}/{WRITE_SAME_PATH_MAX}].{hint}"
        )

    def append_file(self, path: str, content: str) -> str:
        target = self.resolve(path)
        rel = target.relative_to(self.root).as_posix()
        if rel.startswith("output/"):
            self.wrote_deliverable = True
        target.parent.mkdir(parents=True, exist_ok=True)
        body = content if content is not None else ""
        with target.open("a", encoding="utf-8") as fh:
            fh.write(body)
        return (
            f"OK appended {len(body)} chars to {rel} "
            f"(file now {target.stat().st_size} bytes). "
            "Continue with append_file/str_replace, then run_python — do not rewrite via write_file."
        )

    def str_replace(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> str:
        target = self.resolve(path)
        rel = target.relative_to(self.root).as_posix()
        if not target.is_file():
            return f"ERROR: file not found: {rel}"
        text = target.read_text(encoding="utf-8")
        if old_text == "":
            return "ERROR: old_text is empty"
        count = text.count(old_text)
        if count == 0:
            return (
                f"ERROR: old_text not found in {rel}. "
                "read_file a nearby section and retry with exact text."
            )
        if not replace_all and count > 1:
            return (
                f"ERROR: old_text found {count} times in {rel}. "
                "Pass a larger unique old_text, or set replace_all=true."
            )
        if replace_all:
            updated = text.replace(old_text, new_text if new_text is not None else "")
            n = count
        else:
            updated = text.replace(old_text, new_text if new_text is not None else "", 1)
            n = 1
        target.write_text(updated, encoding="utf-8")
        return f"OK str_replace {rel}: {n} occurrence(s), file now {len(updated)} chars"

    def delete_file(self, path: str) -> str:
        target = self.resolve(path)
        if not target.exists():
            return f"ERROR: not found: {path}"
        if target.is_dir():
            return f"ERROR: refusing to delete directory: {path}"
        target.unlink()
        return f"OK deleted {path}"

    def run_python(
        self,
        script_path: str | None = None,
        code: str | None = None,
        args: list[str] | None = None,
    ) -> str:
        if script_path:
            script = self.resolve(script_path)
            if not script.is_file():
                return f"ERROR: script not found: {script_path}"
            cmd = [sys.executable, str(script), *(args or [])]
        elif code:
            if not ALLOW_PYTHON_INLINE:
                return (
                    "ERROR: inline run_python(code=...) disabled. "
                    "write_file your generator under output/, then "
                    "run_python(script_path='output/.../your_script.py')."
                )
            if _looks_like_parsed_dump(code):
                return (
                    "ERROR: forbidden — do not use run_python to read/print parsed/ or input/. "
                    "Use search_files or one read_file on parsed/*.md, then write_file/"
                    "append_file under output/. When the generator is ready, call "
                    "run_python(script_path='output/lab-requirements/generate_lab_requirements_workbook.py') "
                    "(or your CIQ generator path)."
                )
            cmd = [sys.executable, "-c", code]
        else:
            return "ERROR: provide script_path or code"
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=PYTHON_TIMEOUT,
                env={**os.environ, "PYTHONPATH": str(self.root)},
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: python timed out after {PYTHON_TIMEOUT}s"
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        status = f"exit={proc.returncode}"
        body = out.strip() or "(no output)"
        if len(body) > TOOL_RESULT_MAX:
            body = body[:TOOL_RESULT_MAX] + "\n... truncated"
        return f"{status}\n{body}"

    def search_files(
        self,
        query: str,
        path: str = ".",
        glob: str = "",
    ) -> str:
        q = (query or "").strip()
        if not q:
            return "ERROR: empty query"
        root = self.resolve(path)
        if not root.exists():
            return f"ERROR: path not found: {path}"
        suffix = (glob or "").strip().lower()
        hits: list[str] = []
        files: list[Path]
        if root.is_file():
            files = [root]
        else:
            files = [p for p in root.rglob("*") if p.is_file()]
        for file_path in files:
            if suffix and not file_path.name.lower().endswith(suffix.lstrip("*")):
                continue
            try:
                raw = file_path.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw[:2048]:
                continue
            text = raw.decode("utf-8", errors="replace")
            lower = text.lower()
            needle = q.lower()
            if needle not in lower:
                continue
            rel = file_path.relative_to(self.root).as_posix()
            for i, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                    if len(hits) >= SEARCH_MAX_HITS:
                        hits.append("... truncated")
                        return "\n".join(hits)
        return "\n".join(hits) if hits else "(no matches)"

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            if name == "list_dir":
                return self.list_dir(arguments.get("path") or ".")
            if name == "read_file":
                return self.read_file(arguments.get("path") or "")
            if name == "write_file":
                return self.write_file(
                    arguments.get("path") or "",
                    arguments.get("content") if arguments.get("content") is not None else "",
                )
            if name == "append_file":
                return self.append_file(
                    arguments.get("path") or "",
                    arguments.get("content") if arguments.get("content") is not None else "",
                )
            if name == "str_replace":
                return self.str_replace(
                    path=arguments.get("path") or "",
                    old_text=arguments.get("old_text")
                    if arguments.get("old_text") is not None
                    else "",
                    new_text=arguments.get("new_text")
                    if arguments.get("new_text") is not None
                    else "",
                    replace_all=bool(arguments.get("replace_all")),
                )
            if name == "delete_file":
                return self.delete_file(arguments.get("path") or "")
            if name == "run_python":
                return self.run_python(
                    script_path=arguments.get("script_path"),
                    code=arguments.get("code"),
                    args=arguments.get("args"),
                )
            if name == "search_files":
                return self.search_files(
                    query=arguments.get("query") or "",
                    path=arguments.get("path") or ".",
                    glob=arguments.get("glob") or "",
                )
            return f"ERROR: unknown tool {name}"
        except PathJailError as exc:
            return f"ERROR: {exc}"
        except Exception as exc:
            return f"ERROR: {exc}\n{traceback.format_exc()[-1500:]}"


class AgentCancelled(Exception):
    """Raised when the job cancel flag is set between agent steps."""


def _tool_name_for_call_id(messages: list[dict[str, Any]], call_id: str) -> str:
    if not call_id:
        return "tool"
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            tid = tc.get("id") or ""
            if tid != call_id:
                continue
            fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
            return str(fn.get("name") or tc.get("name") or "tool")
    return "tool"


def _summarize_tool_result(name: str, content: str) -> str:
    """One-line stand-in for an old tool result (keeps tool_call_id pairing intact)."""
    text = (content or "").strip()
    if not text:
        return f"[{name}] (empty, compacted)"
    if text.startswith("ERROR"):
        return text.splitlines()[0][:COMPACT_SUMMARY_MAX]
    first = text.splitlines()[0].strip()
    n_lines = text.count("\n") + 1
    if text.startswith("OK"):
        return first[:COMPACT_SUMMARY_MAX]
    if name == "search_files":
        hits = sum(1 for line in text.splitlines() if ":" in line)
        return f"[search_files] {hits} hit line(s), compacted"
    if name == "list_dir":
        return f"[list_dir] {n_lines} entr(y/ies), compacted"
    if name == "read_file":
        return f"[read_file] {len(text)} chars, compacted — use path again if needed"
    if name == "run_python":
        return f"[run_python] {n_lines} line(s) stdout, compacted"
    if n_lines > 1 or len(first) > COMPACT_SUMMARY_MAX:
        return f"[{name}] {first[:COMPACT_SUMMARY_MAX]} … ({n_lines} lines, compacted)"
    return f"[{name}] {first}"


def _assistant_tool_turn_indices(messages: list[dict[str, Any]]) -> list[int]:
    """Indices of assistant messages that open a tool-calling turn."""
    starts: list[int] = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        if msg.get("tool_calls"):
            starts.append(i)
    return starts


def compact_messages(
    messages: list[dict[str, Any]],
    *,
    keep_turns: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Keep system + original user + last ``keep_turns`` tool-turns with full tool bodies.
    Older ``role=tool`` contents become one-line summaries. Assistant tool_calls stay
    so the provider still sees valid call_id pairing.

    Returns (messages, number_of_tool_results_compacted).
    """
    if not COMPACT_ENABLED or len(messages) < 4:
        return messages, 0
    keep = COMPACT_KEEP_TURNS if keep_turns is None else max(1, keep_turns)
    turn_starts = _assistant_tool_turn_indices(messages)
    if len(turn_starts) <= keep:
        return messages, 0

    # Compact tool results belonging to turns before the last ``keep`` starts.
    compact_before_idx = turn_starts[-keep]
    compacted = 0
    out: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        if i < compact_before_idx and msg.get("role") == "tool":
            content = msg.get("content") or ""
            # Skip if already compacted
            if isinstance(content, str) and ", compacted" in content.split("\n", 1)[0]:
                out.append(msg)
                continue
            name = _tool_name_for_call_id(messages, str(msg.get("tool_call_id") or ""))
            summary = _summarize_tool_result(name, content if isinstance(content, str) else str(content))
            new_msg = dict(msg)
            new_msg["content"] = summary
            out.append(new_msg)
            compacted += 1
        else:
            out.append(msg)
    return out, compacted


def run_agent_loop(
    *,
    workspace: Path,
    system: str,
    user: str,
    logs: list[str],
    on_log: Callable[[], None] | None = None,
    max_steps: int | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> str:
    """
    Run a multi-step tool loop. Returns the final assistant text (or a status summary).

    ``should_cancel`` is checked before each LLM round (cannot abort an in-flight
    HTTP call to the model — same practical boundary as Cursor Stop between tools).

    Before each LLM call, older tool results are compacted (see
    ``SPRINTWEAVE_AGENT_COMPACT``) so token use stays roughly flat across steps.
    """
    tools = WorkspaceTools(workspace)
    steps = max_steps if max_steps is not None else MAX_STEPS
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    final_text = ""
    step = 0
    force_write_nudged = False

    for step in range(1, steps + 1):
        if should_cancel and should_cancel():
            logs.append(f"[agent] cancelled at step {step}/{steps}")
            if on_log:
                on_log()
            raise AgentCancelled(f"cancelled at agent step {step}")

        messages, n_compact = compact_messages(messages)
        if n_compact:
            logs.append(
                f"[agent] compacted {n_compact} older tool result(s) "
                f"(keep last {COMPACT_KEEP_TURNS} turns)"
            )

        logs.append(f"[agent] step {step}/{steps}")
        if on_log:
            on_log()
        result = complete_tools(messages, TOOL_SCHEMAS, tool_choice="auto")
        content = result.get("content") or ""
        tool_calls = result.get("tool_calls") or []
        raw_message = result.get("raw_message") or {
            "role": "assistant",
            "content": content,
        }
        messages.append(raw_message)

        if content:
            final_text = content

        if not tool_calls:
            logs.append(f"[agent] finished at step {step} (no more tools)")
            if on_log:
                on_log()
            break

        for call in tool_calls:
            if should_cancel and should_cancel():
                logs.append(f"[agent] cancelled during tools at step {step}")
                if on_log:
                    on_log()
                raise AgentCancelled(f"cancelled during tools at step {step}")
            name = call.get("name") or ""
            args = call.get("arguments") or {}
            call_id = call.get("id") or f"call_{step}"
            arg_preview = json.dumps(args)[:200]
            logs.append(f"[tool] {name}({arg_preview})")
            if on_log:
                on_log()
            tool_result = tools.dispatch(name, args)
            if len(tool_result) > TOOL_RESULT_MAX:
                tool_result = tool_result[:TOOL_RESULT_MAX] + "\n... truncated"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_result,
                }
            )

        # One-time nudge: stop explore thrash — must write under output/
        if (
            FORCE_WRITE_AFTER_STEP
            and step >= FORCE_WRITE_AFTER_STEP
            and not tools.wrote_deliverable
            and not force_write_nudged
        ):
            force_write_nudged = True
            logs.append(
                f"[agent] force-write nudge after step {step} "
                "(no output/ files yet)"
            )
            if on_log:
                on_log()
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "STOP exploring. You have not written any file under output/. "
                        "Do NOT call run_python to print parsed/. "
                        "Next actions MUST be: write_file skeleton under "
                        "output/lab-requirements/ or output/ciq-generators/, "
                        "then append_file/str_replace hunks, then "
                        "run_python(script_path=...) once."
                    ),
                }
            )
    else:
        logs.append(f"[agent] stopped: max steps ({steps})")
        if on_log:
            on_log()

    if not final_text.strip():
        final_text = (
            f"Agent completed {min(step, steps)} step(s). "
            "See workspace/output for generated files."
        )
    return final_text
