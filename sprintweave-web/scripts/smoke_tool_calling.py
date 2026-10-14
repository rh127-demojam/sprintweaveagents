#!/usr/bin/env python3
"""Smoke-test OpenAI-compatible tool calling (MaaS / LiteLLM).

Usage (from sprintweave-web, with env set like the API pod):

  export LLM_PROVIDER=openai
  export LLM_BASE_URL=https://maas-.../v1
  export LLM_API_KEY=...
  export LLM_MODEL=claude-opus-4-6
  export LLM_MAX_TOKENS=512
  export LLM_TIMEOUT=120

  python scripts/smoke_tool_calling.py

Exit 0 = model returned a tool call and local tools executed.
Exit 1 = tool calling failed or model ignored tools.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Allow running from repo without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.agent_runtime import TOOL_SCHEMAS, WorkspaceTools  # noqa: E402
from llm.client import complete_tools  # noqa: E402


def main() -> int:
    missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"FAIL: set env vars: {', '.join(missing)}", file=sys.stderr)
        return 1

    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider in {"anthropic", "claude"}:
        print("FAIL: use LLM_PROVIDER=openai for tool calling", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="sw-smoke-") as tmp:
        workspace = Path(tmp)
        tools = WorkspaceTools(workspace)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a tool-using agent. You MUST call the write_file tool "
                    "to create smoke.txt with content exactly: ok\n"
                    "Do not only reply with text."
                ),
            },
            {
                "role": "user",
                "content": "Create smoke.txt with the text ok using write_file.",
            },
        ]
        print("Calling complete_tools…")
        try:
            result = complete_tools(messages, TOOL_SCHEMAS, tool_choice="auto")
        except Exception as exc:
            print(f"FAIL: LLM request error: {exc}", file=sys.stderr)
            return 1

        calls = result.get("tool_calls") or []
        print("content:", (result.get("content") or "")[:200])
        print("tool_calls:", json.dumps(calls, indent=2)[:2000])

        if not calls:
            print(
                "FAIL: model returned no tool_calls. "
                "MaaS/LiteLLM may not support tools for this model.",
                file=sys.stderr,
            )
            return 1

        wrote = False
        for call in calls:
            name = call.get("name") or ""
            args = call.get("arguments") or {}
            out = tools.dispatch(name, args)
            print(f"dispatch {name} -> {out}")
            if name == "write_file":
                wrote = True

        path = workspace / "smoke.txt"
        if path.is_file() and "ok" in path.read_text(encoding="utf-8"):
            print("PASS: tool calling + write_file works")
            return 0
        if wrote:
            print("FAIL: write_file called but smoke.txt missing/wrong", file=sys.stderr)
        else:
            print("FAIL: no write_file tool call", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
