"""Chat client with prompt caching for Cursor-like token usage.

Supports:
  LLM_PROVIDER=openai     → OpenAI-compatible /chat/completions (MaaS/LiteLLM)
  LLM_PROVIDER=anthropic  → Anthropic Messages API with prompt caching + tool use

Prompt caching (Anthropic):
  System prompt + first user message are marked with cache_control.
  After the first call in a session, Anthropic caches that prefix.
  Subsequent calls pay ~10% for cached tokens → like Cursor.

Prompt caching (OpenAI/MaaS):
  If the endpoint supports it (e.g. OpenAI with structured prefix),
  we set extra headers. Otherwise retry logic helps with stability.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-scout-17b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", "3"))

# Per-stage model override — set by worker.py before each stage
_model_override: str | None = None


def set_model_override(model: str | None) -> None:
    """Temporarily override the LLM model (e.g. use Sonnet for simple stages)."""
    global _model_override
    _model_override = model.strip() if model else None


def get_active_model() -> str:
    """Return the currently active model (override or default)."""
    return _model_override or LLM_MODEL

log = logging.getLogger("llm.client")


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any],
    timeout: int | None = None,
) -> requests.Response:
    """POST/GET with retry on connection errors."""
    t = timeout or LLM_TIMEOUT
    last_exc: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json_body, timeout=t,
            )
            resp.raise_for_status()
            return resp
        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_exc = exc
            if attempt < LLM_RETRIES:
                time.sleep(5 * attempt)
                continue
            raise
    raise last_exc  # unreachable, but makes type checker happy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete(system: str, user: str) -> str:
    """Single-turn completion (no tools)."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set")
    if LLM_PROVIDER in {"anthropic", "claude"}:
        return _anthropic_complete(system, user)
    return _openai_complete(system, user)


def complete_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    tool_choice: str | dict[str, Any] = "auto",
) -> dict[str, Any]:
    """
    One tool-enabled chat turn.

    Returns:
      {
        "content": str | None,
        "tool_calls": [{"id", "name", "arguments": dict}, ...],
        "raw_message": dict,
      }
    """
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set")
    if LLM_PROVIDER in {"anthropic", "claude"}:
        return _anthropic_complete_tools(messages, tools, tool_choice=tool_choice)
    return _openai_complete_tools(messages, tools, tool_choice=tool_choice)


# ---------------------------------------------------------------------------
# OpenAI-compatible (MaaS / LiteLLM) — with cache hints
# ---------------------------------------------------------------------------

def _inject_cache_hints(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add cache_control to system + first user message for LiteLLM→Anthropic."""
    out: list[dict[str, Any]] = []
    first_user_done = False
    for msg in messages:
        m = dict(msg)  # shallow copy
        role = m.get("role", "")
        if role == "system" and "cache_control" not in m:
            m["cache_control"] = {"type": "ephemeral"}
        elif role == "user" and not first_user_done and "cache_control" not in m:
            m["cache_control"] = {"type": "ephemeral"}
            first_user_done = True
        out.append(m)
    return out


def _log_openai_usage(usage: dict[str, Any] | None) -> None:
    """Log token counts from OpenAI-compatible responses."""
    if not usage:
        return
    prompt = usage.get("prompt_tokens", 0)
    comp = usage.get("completion_tokens", 0)
    cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    if cached > 0:
        pct = round(cached / max(prompt, 1) * 100)
        log.info(
            f"[cache HIT] {cached:,} cached ({pct}%) + "
            f"{prompt - cached:,} fresh + {comp:,} output"
        )
    else:
        log.info(f"[tokens] {prompt:,} input + {comp:,} output")

def _openai_complete(system: str, user: str) -> str:
    if not LLM_BASE_URL:
        raise RuntimeError("LLM_BASE_URL is not set")
    # LiteLLM passes cache_control through to Anthropic backends
    messages = [
        {
            "role": "system",
            "content": system,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "role": "user",
            "content": user,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    # Use streaming to keep MaaS connection alive during long generations
    last_exc: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            resp = requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": get_active_model(),
                    "messages": messages,
                    "max_tokens": LLM_MAX_TOKENS,
                    "temperature": 0.2,
                    "stream": True,
                },
                timeout=LLM_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()
            # Collect streamed chunks
            content_parts: list[str] = []
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                except json.JSONDecodeError:
                    continue
            text = "".join(content_parts)
            if not text:
                raise RuntimeError("Streaming returned empty response")
            log.info(f"[tokens] streamed ~{len(text)} chars output")
            return text
        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_exc = exc
            log.warning(f"[stream] attempt {attempt}/{LLM_RETRIES} failed: {exc}")
            if attempt < LLM_RETRIES:
                time.sleep(5 * attempt)
                continue
            raise
    raise last_exc  # unreachable


def _openai_complete_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    tool_choice: str | dict[str, Any] = "auto",
) -> dict[str, Any]:
    """Tool-calling via streaming — keeps MaaS connection alive on long writes.

    Non-streaming tool calls often die with RemoteDisconnected after ~2–3 min
    when the model emits multiple write_file payloads.
    """
    if not LLM_BASE_URL:
        raise RuntimeError("LLM_BASE_URL is not set")
    cached_messages = _inject_cache_hints(messages)
    last_exc: Exception | None = None

    for attempt in range(1, LLM_RETRIES + 1):
        try:
            resp = requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": get_active_model(),
                    "messages": cached_messages,
                    "tools": tools,
                    "tool_choice": tool_choice,
                    "max_tokens": LLM_MAX_TOKENS,
                    "temperature": 0.2,
                    "stream": True,
                },
                timeout=LLM_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()

            content_parts: list[str] = []
            # index -> {id, name, arguments}
            tool_acc: dict[int, dict[str, str]] = {}

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choice0 = (chunk.get("choices") or [{}])[0]
                delta = choice0.get("delta") or {}
                if delta.get("content"):
                    content_parts.append(delta["content"])
                for tc in delta.get("tool_calls") or []:
                    idx = int(tc.get("index") or 0)
                    slot = tool_acc.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = fn["name"]
                    if fn.get("arguments"):
                        slot["arguments"] += fn["arguments"]

            message: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(content_parts) or None,
            }
            if tool_acc:
                message["tool_calls"] = [
                    {
                        "id": tool_acc[i]["id"] or f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": tool_acc[i]["name"],
                            "arguments": tool_acc[i]["arguments"] or "{}",
                        },
                    }
                    for i in sorted(tool_acc)
                ]
            log.info(
                f"[tokens] streamed tools: "
                f"~{len(message.get('content') or '')} chars content, "
                f"{len(tool_acc)} tool_call(s)"
            )
            return _parse_openai_tool_message(message)
        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError,
            requests.exceptions.StreamConsumedError,
        ) as exc:
            last_exc = exc
            log.warning(
                f"[stream-tools] attempt {attempt}/{LLM_RETRIES} failed: {exc}"
            )
            if attempt < LLM_RETRIES:
                time.sleep(5 * attempt)
                continue
            raise
    raise last_exc  # unreachable


def _parse_openai_tool_message(message: dict[str, Any]) -> dict[str, Any]:
    tool_calls_out: list[dict[str, Any]] = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            args = {"_raw": raw_args}
        tool_calls_out.append({
            "id": call.get("id") or "",
            "name": fn.get("name") or "",
            "arguments": args,
            "raw": call,
        })
    return {
        "content": message.get("content"),
        "tool_calls": tool_calls_out,
        "raw_message": message,
    }


# ---------------------------------------------------------------------------
# Anthropic Messages API — with PROMPT CACHING
# ---------------------------------------------------------------------------
# Caching: mark system + first user with cache_control.
# After the first request, Anthropic caches the prefix (~90% cheaper on
# subsequent calls). This is how Cursor keeps costs low.

def _anthropic_headers() -> dict[str, str]:
    return {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "prompt-caching-2024-07-31",
        "Content-Type": "application/json",
    }


def _anthropic_base() -> str:
    return LLM_BASE_URL or "https://api.anthropic.com"


def _log_anthropic_usage(usage: dict[str, Any] | None) -> None:
    """Log cache hit/miss/output tokens for cost visibility."""
    if not usage:
        return
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)
    fresh = inp - cache_read - cache_create
    if cache_read > 0:
        pct = round(cache_read / max(inp, 1) * 100)
        log.info(
            f"[cache HIT] {cache_read:,} cached ({pct}%) + "
            f"{fresh:,} fresh + {out:,} output"
        )
    elif cache_create > 0:
        log.info(
            f"[cache WRITE] {cache_create:,} tokens cached + "
            f"{fresh:,} fresh + {out:,} output"
        )
    else:
        log.info(f"[no cache] {inp:,} input + {out:,} output")


def _anthropic_complete(system: str, user: str) -> str:
    """Single-turn with prompt caching on system + user."""
    resp = _request_with_retry(
        "POST",
        f"{_anthropic_base()}/v1/messages",
        headers=_anthropic_headers(),
        json_body={
            "model": get_active_model(),
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0.2,
            "system": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
            ],
        },
    )
    data = resp.json()
    parts = data.get("content") or []
    texts = [p.get("text", "") for p in parts if p.get("type") == "text"]
    if not texts:
        raise RuntimeError(f"Anthropic returned no text: {data}")
    _log_anthropic_usage(data.get("usage"))
    return "\n".join(texts)


def _convert_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI tool schemas to Anthropic format."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        fn = tool.get("function") or {}
        out.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


def _convert_messages_to_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Split OpenAI messages into (system_blocks, anthropic_messages).
    First system message → system with cache_control.
    First user message → user with cache_control (cacheable prefix).
    Tool results and assistant messages converted to Anthropic format.
    """
    system_blocks: list[dict[str, Any]] = []
    anth_messages: list[dict[str, Any]] = []
    first_user_done = False

    for msg in messages:
        role = msg.get("role", "")

        if role == "system":
            system_blocks.append({
                "type": "text",
                "text": msg.get("content") or "",
                "cache_control": {"type": "ephemeral"},
            })

        elif role == "user":
            content = msg.get("content") or ""
            if not first_user_done:
                anth_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                })
                first_user_done = True
            else:
                anth_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            blocks: list[dict[str, Any]] = []
            if msg.get("content"):
                blocks.append({"type": "text", "text": msg["content"]})
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                raw_args = fn.get("arguments") or tc.get("arguments") or "{}"
                if isinstance(raw_args, str):
                    try:
                        parsed = json.loads(raw_args)
                    except json.JSONDecodeError:
                        parsed = {"_raw": raw_args}
                else:
                    parsed = raw_args
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or "",
                    "name": fn.get("name") or tc.get("name") or "",
                    "input": parsed,
                })
            if blocks:
                anth_messages.append({"role": "assistant", "content": blocks})

        elif role == "tool":
            anth_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id") or "",
                        "content": msg.get("content") or "",
                    }
                ],
            })

    return system_blocks, anth_messages


def _anthropic_complete_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    tool_choice: str | dict[str, Any] = "auto",
) -> dict[str, Any]:
    """Tool-calling via Anthropic Messages API with prompt caching."""
    system_blocks, anth_messages = _convert_messages_to_anthropic(messages)
    anth_tools = _convert_tools_to_anthropic(tools)

    # Map tool_choice
    if isinstance(tool_choice, str):
        tc = {"type": tool_choice} if tool_choice in {"auto", "any"} else {"type": "auto"}
    else:
        tc = tool_choice

    body: dict[str, Any] = {
        "model": get_active_model(),
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": 0.2,
        "system": system_blocks,
        "messages": anth_messages,
        "tools": anth_tools,
        "tool_choice": tc,
    }

    resp = _request_with_retry(
        "POST",
        f"{_anthropic_base()}/v1/messages",
        headers=_anthropic_headers(),
        json_body=body,
    )
    data = resp.json()

    _log_anthropic_usage(data.get("usage"))

    # Parse response into OpenAI-like format for agent_runtime compatibility
    content_text = ""
    tool_calls_out: list[dict[str, Any]] = []
    raw_blocks: list[dict[str, Any]] = []

    for block in data.get("content") or []:
        btype = block.get("type", "")
        if btype == "text":
            content_text += block.get("text", "")
        elif btype == "tool_use":
            tool_calls_out.append({
                "id": block.get("id") or "",
                "name": block.get("name") or "",
                "arguments": block.get("input") or {},
            })
        raw_blocks.append(block)

    # Build a raw_message that agent_runtime can append to messages[]
    raw_message: dict[str, Any] = {
        "role": "assistant",
        "content": content_text or None,
    }
    if tool_calls_out:
        raw_message["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"]),
                },
            }
            for tc in tool_calls_out
        ]

    return {
        "content": content_text or None,
        "tool_calls": tool_calls_out,
        "raw_message": raw_message,
        "_anthropic_usage": data.get("usage"),
    }
