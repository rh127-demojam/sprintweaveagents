#!/usr/bin/env python3
"""Offline check for agent history compaction (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.agent_runtime import compact_messages  # noqa: E402


def _assistant(call_id: str, name: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": "{}"},
            }
        ],
    }


def main() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user task"},
        _assistant("c1", "read_file"),
        {"role": "tool", "tool_call_id": "c1", "content": "A" * 5000},
        _assistant("c2", "search_files"),
        {
            "role": "tool",
            "tool_call_id": "c2",
            "content": "parsed/x.md:1: hit one\nparsed/x.md:2: hit two\n",
        },
        _assistant("c3", "write_file"),
        {"role": "tool", "tool_call_id": "c3", "content": "OK wrote output/a.py (10 chars)"},
        _assistant("c4", "append_file"),
        {"role": "tool", "tool_call_id": "c4", "content": "OK appended 20 chars to output/a.py"},
        _assistant("c5", "run_python"),
        {"role": "tool", "tool_call_id": "c5", "content": "exit 0\ndid work\n"},
    ]
    # keep last 3 turns full → first 2 tool results compact
    out, n = compact_messages(messages, keep_turns=3)
    assert n == 2, n
    assert "compacted" in out[3]["content"], out[3]
    assert "compacted" in out[5]["content"], out[5]
    assert out[7]["content"].startswith("OK wrote"), out[7]
    assert out[9]["content"].startswith("OK appended"), out[9]
    assert "did work" in out[11]["content"], out[11]
    # idempotent
    out2, n2 = compact_messages(out, keep_turns=3)
    assert n2 == 0, n2
    print("PASS compact_messages keep_turns=3")


if __name__ == "__main__":
    main()
