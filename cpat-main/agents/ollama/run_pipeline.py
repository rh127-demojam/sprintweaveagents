#!/usr/bin/env python3
"""
CPAT Agent Pipeline Runner — Open-Source Models (Ollama / vLLM / any OpenAI-compatible API)

Runs RHOSO DA + RDE agents using local open-source LLMs with tool-use capabilities.
Agent definitions from .cursor/rules/*.md serve as system prompts.

Prerequisites:
    1. Install Ollama: https://ollama.com/download
    2. Pull a model:   ollama pull qwen2.5-coder:14b
    3. pip install openai pyyaml

Usage:
    python run_pipeline.py                              # Full pipeline
    python run_pipeline.py --pipeline rda               # RDA only
    python run_pipeline.py --pipeline rde               # RDE only
    python run_pipeline.py --stage RDE-1                # Single stage
    python run_pipeline.py --model codellama:34b        # Different model
    python run_pipeline.py --api-base http://host:8000/v1  # Custom endpoint (vLLM, etc.)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from textwrap import dedent

from openai import OpenAI


# ── Configuration ────────────────────────────────────────────

CPAT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_MODEL = "qwen2.5-coder:14b"
DEFAULT_API_BASE = "http://localhost:11434/v1"  # Ollama default
DEFAULT_API_KEY = "ollama"  # Ollama doesn't need a real key

MAX_ITERATIONS = 40          # Max tool-call rounds per stage
MAX_FILE_READ_CHARS = 30000  # Truncate large file reads
TEMPERATURE = 0.1            # Low temp for deterministic code gen


def set_max_iterations(value: int):
    global MAX_ITERATIONS
    MAX_ITERATIONS = value


# ── Tool Definitions (OpenAI function-calling format) ────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root (e.g., '.cursor/rules/agent-rhoso-da.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path (e.g., 'output/cpat/ansible/playbooks/roles/rhoso/tasks')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the workspace directory. Use for: running Python scripts, pip install, verifying outputs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a text pattern across files in the workspace (like grep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (relative, default: '.')",
                    },
                    "glob": {
                        "type": "string",
                        "description": "File glob filter (e.g., '*.py', '*.yml')",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


# ── Tool Implementations ─────────────────────────────────────

def tool_read_file(path: str) -> str:
    full = CPAT_ROOT / path
    if not full.exists():
        return f"ERROR: File not found: {path}"
    if not full.is_file():
        return f"ERROR: Not a file: {path}"
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_FILE_READ_CHARS:
            return content[:MAX_FILE_READ_CHARS] + f"\n\n... [TRUNCATED — {len(content)} chars total]"
        return content
    except Exception as e:
        return f"ERROR: {e}"


def tool_write_file(path: str, content: str) -> str:
    full = CPAT_ROOT / path
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return f"OK: Written {lines} lines to {path}"
    except Exception as e:
        return f"ERROR: {e}"


def tool_list_directory(path: str) -> str:
    full = CPAT_ROOT / path
    if not full.exists():
        return f"ERROR: Directory not found: {path}"
    if not full.is_dir():
        return f"ERROR: Not a directory: {path}"
    entries = []
    for item in sorted(full.iterdir()):
        kind = "DIR" if item.is_dir() else f"FILE ({item.stat().st_size}B)"
        entries.append(f"  {kind}  {item.name}")
    return f"Contents of {path}/ ({len(entries)} entries):\n" + "\n".join(entries)


def tool_run_command(command: str) -> str:
    blocked = ["rm -rf /", "format ", "del /s /q c:\\"]
    if any(b in command.lower() for b in blocked):
        return "ERROR: Dangerous command blocked."
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=str(CPAT_ROOT), timeout=120,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr
        if not output.strip():
            output = "(no output)"
        if len(output) > MAX_FILE_READ_CHARS:
            output = output[:MAX_FILE_READ_CHARS] + "\n... [TRUNCATED]"
        return f"Exit code: {result.returncode}\n{output}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 120s"
    except Exception as e:
        return f"ERROR: {e}"


def tool_search_files(pattern: str, path: str = ".", glob: str = None) -> str:
    cmd = f'rg --no-heading -n "{pattern}" "{path}"'
    if glob:
        cmd += f' --glob "{glob}"'
    cmd += " --max-count 50"
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=str(CPAT_ROOT), timeout=30,
    )
    output = result.stdout.strip()
    if not output:
        return f"No matches for '{pattern}' in {path}/"
    if len(output) > MAX_FILE_READ_CHARS:
        output = output[:MAX_FILE_READ_CHARS] + "\n... [TRUNCATED]"
    return output


TOOL_DISPATCH = {
    "read_file": lambda args: tool_read_file(args["path"]),
    "write_file": lambda args: tool_write_file(args["path"], args["content"]),
    "list_directory": lambda args: tool_list_directory(args["path"]),
    "run_command": lambda args: tool_run_command(args["command"]),
    "search_files": lambda args: tool_search_files(
        args["pattern"], args.get("path", "."), args.get("glob"),
    ),
}


# ── Agent Loop ───────────────────────────────────────────────

def load_system_prompt(agent_rule_path: str, extra_context_paths: list[str] = None) -> str:
    """Load agent rule + optional context files as the system prompt."""
    parts = []

    rule = (CPAT_ROOT / agent_rule_path).read_text(encoding="utf-8", errors="replace")
    parts.append(f"# Agent Rule\n\n{rule}")

    for ctx_path in (extra_context_paths or []):
        p = CPAT_ROOT / ctx_path
        if p.exists():
            ctx = p.read_text(encoding="utf-8", errors="replace")
            if len(ctx) > 50000:
                ctx = ctx[:50000] + "\n... [TRUNCATED]"
            parts.append(f"# Context: {ctx_path}\n\n{ctx}")

    parts.append(dedent("""\
        # Tool Instructions

        You have access to tools: read_file, write_file, list_directory, run_command, search_files.
        Use them to read existing files, generate new source code files, and verify outputs.

        IMPORTANT:
        - Write COMPLETE file contents (not partial/abbreviated).
        - Use write_file for EVERY file you generate.
        - After generating files, use list_directory to verify they exist.
        - The workspace root is the CPAT project directory.
        - All paths are relative to the workspace root.
    """))

    return "\n\n---\n\n".join(parts)


TOOL_USE_REMINDER = (
    "IMPORTANT: You MUST use the provided tools (read_file, write_file, "
    "list_directory, run_command, search_files) to perform actions. "
    "Do NOT describe code in text — call write_file with the actual file "
    "content. Start by calling read_file to read the agent rule, then "
    "call write_file for each file you need to create. "
    "Make tool calls NOW."
)


def run_agent(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    stage_name: str,
) -> bool:
    """Run a single agent stage with tool-calling loop. Returns True on success."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    text_only_retries = 0

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"  [{stage_name}] Iteration {iteration}/{MAX_ITERATIONS}...", end="", flush=True)

        # Force tool use on first iteration and after text-only retries
        force_tool = iteration == 1 or text_only_retries > 0
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="required" if force_tool else "auto",
                temperature=TEMPERATURE,
                max_tokens=16384,
            )
            try:
                response = client.chat.completions.create(**kwargs)
            except Exception:
                # Some APIs don't support tool_choice="required", fall back
                if force_tool:
                    kwargs["tool_choice"] = "auto"
                    response = client.chat.completions.create(**kwargs)
                else:
                    raise
        except Exception as e:
            print(f"\n  ERROR: API call failed: {e}")
            return False

        choice = response.choices[0]
        msg = choice.message

        # Accumulate assistant message
        messages.append(msg.model_dump())

        # If no tool calls — retry up to 2 times with a stronger nudge
        if not msg.tool_calls:
            if text_only_retries < 2:
                text_only_retries += 1
                print(f" text-only response, nudging to use tools (retry {text_only_retries}/2)")
                messages.append({
                    "role": "user",
                    "content": TOOL_USE_REMINDER,
                })
                continue
            print(" done (no more tool calls)")
            if msg.content:
                summary = msg.content[:2000]
                print(f"\n  Agent summary:\n{summary}")
            return True
        text_only_retries = 0

        # Process tool calls
        print(f" {len(msg.tool_calls)} tool call(s)")
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            handler = TOOL_DISPATCH.get(fn_name)
            if handler:
                if fn_name == "write_file":
                    print(f"    📝 write_file: {fn_args.get('path', '?')}")
                elif fn_name == "read_file":
                    print(f"    📖 read_file: {fn_args.get('path', '?')}")
                elif fn_name == "run_command":
                    print(f"    ⚡ run_command: {fn_args.get('command', '?')[:80]}")
                elif fn_name == "list_directory":
                    print(f"    📁 list_directory: {fn_args.get('path', '?')}")
                elif fn_name == "search_files":
                    print(f"    🔍 search_files: {fn_args.get('pattern', '?')}")

                result = handler(fn_args)
            else:
                result = f"ERROR: Unknown tool '{fn_name}'"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    print(f"  ⚠ [{stage_name}] Reached max iterations ({MAX_ITERATIONS})")
    return True


# ── Pipeline Stages ──────────────────────────────────────────

PIPELINE_STAGES = {
    "rhoso-delivery": [
        {
            "abbrev": "RDA",
            "agent_rule": ".cursor/rules/agent-rhoso-da.md",
            "extra_context": [],
            "prompt": dedent("""\
                You are the RHOSO DA agent. Your task:

                1. First, read your agent rule to understand the full specification:
                   read_file('.cursor/rules/agent-rhoso-da.md')

                2. Generate the CIQ schema code:
                   write_file('output/ciq-generators/rhoso_ciq_schema.py', ...)
                   - 15 tables, 175+ parameters, 38 CIQ_TYPES
                   - SCHEMA_VERSION = "1.3"

                3. Generate the CIQ workbook generator:
                   write_file('output/ciq-generators/generate_rhoso_ciq_workbooks.py', ...)
                   - 8-sheet workbook (Versioning, Environment, Storage, Control Plane, Networks, Data Plane, values, Guidelines)
                   - 14 conditional formatting rules
                   - SHEET_GROUPS structure

                4. Generate requirements.txt:
                   write_file('output/ciq-generators/requirements.txt', ...)

                5. Run the generator to produce workbooks:
                   run_command('pip install openpyxl')
                   run_command('python output/ciq-generators/generate_rhoso_ciq_workbooks.py')

                6. Verify outputs exist:
                   list_directory('output/ciq-generators')
                   list_directory('output/ciq-workbooks/rhoso')

                Write COMPLETE source code for each file. Do not abbreviate or skip sections.
            """),
            "verify_paths": [
                "output/ciq-generators/rhoso_ciq_schema.py",
                "output/ciq-generators/generate_rhoso_ciq_workbooks.py",
            ],
        },
        {
            "abbrev": "RDE-1",
            "agent_rule": ".cursor/rules/agent-rhoso-deployment-engineer.md",
            "extra_context": ["context/templates/rhoso-deployment-engineer.md"],
            "prompt": dedent("""\
                You are the RHOSO Deployment Engineer agent. sub_stage=Ansible.

                1. Read your agent rule and context template for the complete specification.
                2. Read the CIQ schema generated by RDA.
                3. Generate ALL 22 Ansible task files, 15 Jinja2 templates, defaults, library modules.
                4. Write all files to output/cpat/ansible/.
                5. Verify with list_directory.

                Write COMPLETE source code. Do NOT abbreviate with "..." or comments like "rest of code here".
            """),
            "verify_paths": [
                "output/cpat/ansible/playbooks/roles/rhoso/tasks/main.yml",
                "output/cpat/ansible/playbooks/roles/rhoso/templates/openstack_control_plane.yaml.j2",
                "output/cpat/ansible/playbooks/roles/rhoso/defaults/main.yml",
            ],
        },
        {
            "abbrev": "RDE-2",
            "agent_rule": ".cursor/rules/agent-rhoso-deployment-engineer.md",
            "extra_context": ["context/templates/rhoso-deployment-engineer.md"],
            "prompt": dedent("""\
                You are the RHOSO Deployment Engineer agent. sub_stage=Backend.

                1. Read your agent rule and context template.
                2. Read the CIQ schema from output/cpat/ansible/module_utils/.
                3. Generate ALL 10 backend files (app.py, ansible_runner.py with 16 task tags, etc.).
                4. Write all files to output/cpat/backend/.
                5. Verify with list_directory.

                Write COMPLETE source code for each file.
            """),
            "verify_paths": [
                "output/cpat/backend/app.py",
                "output/cpat/backend/ansible_runner.py",
            ],
        },
        {
            "abbrev": "RDE-3",
            "agent_rule": ".cursor/rules/agent-rhoso-deployment-engineer.md",
            "extra_context": ["context/templates/rhoso-deployment-engineer.md"],
            "prompt": dedent("""\
                You are the RHOSO Deployment Engineer agent. sub_stage=Frontend.

                1. Read your agent rule.
                2. Read backend app.py to match API routes.
                3. Generate ALL 23 frontend files (11 components incl. RhosoInstallation with 16 deploy tasks).
                4. Write all files to output/cpat/frontend/.
                5. Verify with list_directory.

                Write COMPLETE source code for each file.
            """),
            "verify_paths": [
                "output/cpat/frontend/src/components/RhosoInstallation.jsx",
                "output/cpat/frontend/package.json",
            ],
        },
        {
            "abbrev": "RDE-4",
            "agent_rule": ".cursor/rules/agent-rhoso-deployment-engineer.md",
            "extra_context": ["context/templates/rhoso-deployment-engineer.md"],
            "prompt": dedent("""\
                You are the RHOSO Deployment Engineer agent. sub_stage=Docker.

                1. Read your agent rule.
                2. Generate Dockerfile, docker/entrypoint.sh, bringup.sh, .dockerignore, USAGE.md, README.md.
                3. Write all files to output/cpat/.
                4. Verify with list_directory.

                Write COMPLETE source code for each file.
            """),
            "verify_paths": [
                "output/cpat/Dockerfile",
                "output/cpat/bringup.sh",
                "output/cpat/USAGE.md",
            ],
        },
    ],
}

PIPELINE_STAGES["rda"] = PIPELINE_STAGES["rhoso-delivery"][:1]
PIPELINE_STAGES["rde"] = PIPELINE_STAGES["rhoso-delivery"][1:]


# ── Pipeline Runner ──────────────────────────────────────────

def verify_outputs(stage: dict) -> tuple[int, int]:
    found = missing = 0
    for rel in stage["verify_paths"]:
        p = CPAT_ROOT / rel
        if p.exists() and p.stat().st_size > 0:
            found += 1
        else:
            missing += 1
            print(f"  ⚠ MISSING: {rel}", file=sys.stderr)
    return found, missing


def run_pipeline(args):
    client = OpenAI(
        base_url=args.api_base,
        api_key=args.api_key,
    )

    try:
        models = client.models.list()
        available = [m.id for m in models.data]
        if args.model not in available:
            print(f"WARNING: Model '{args.model}' not in available models: {available[:10]}")
            print("Proceeding anyway (some APIs don't list all models)...")
    except Exception:
        print(f"Note: Could not list models from {args.api_base} (proceeding anyway)")

    stages = PIPELINE_STAGES.get(args.pipeline)
    if not stages:
        print(f"ERROR: Unknown pipeline '{args.pipeline}'", file=sys.stderr)
        sys.exit(1)

    if args.stage:
        stages = [s for s in stages if s["abbrev"] == args.stage]
        if not stages:
            print(f"ERROR: Stage '{args.stage}' not found", file=sys.stderr)
            sys.exit(1)

    total = len(stages)
    print(f"\n{'='*60}")
    print(f"CPAT Pipeline (Open-Source): {args.pipeline} — {total} stage(s)")
    print(f"Model:    {args.model}")
    print(f"API Base: {args.api_base}")
    print(f"CWD:      {CPAT_ROOT}")
    print(f"{'='*60}\n")

    for i, stage in enumerate(stages, 1):
        abbrev = stage["abbrev"]
        print(f"\n{'─'*50}")
        print(f"[{i}/{total}] Stage: {abbrev}")
        print(f"{'─'*50}")

        t0 = time.time()

        system_prompt = load_system_prompt(
            stage["agent_rule"],
            stage.get("extra_context"),
        )

        success = run_agent(
            client=client,
            model=args.model,
            system_prompt=system_prompt,
            user_prompt=stage["prompt"],
            stage_name=abbrev,
        )

        elapsed = time.time() - t0
        found, missing = verify_outputs(stage)
        status = "✅" if missing == 0 else "⚠️"
        print(f"\n{status} [{abbrev}] {'Done' if success else 'Stopped'} in {elapsed:.0f}s — "
              f"{found} verified, {missing} missing")

    print(f"\n{'='*60}")
    print(f"Pipeline '{args.pipeline}' complete.")
    print(f"{'='*60}\n")


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CPAT Agent Pipeline — Open-Source Models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Recommended Models (by VRAM):
              8GB  VRAM: qwen2.5-coder:7b, deepseek-coder-v2:16b-lite-instruct-q4_0
              16GB VRAM: qwen2.5-coder:14b (recommended), codellama:13b
              24GB VRAM: qwen2.5-coder:32b (best quality), deepseek-coder-v2:16b
              48GB VRAM: qwen2.5-coder:32b-instruct-fp16, llama3.1:70b-instruct-q4_0

            Compatible APIs:
              Ollama:     http://localhost:11434/v1   (default)
              vLLM:       http://localhost:8000/v1
              LM Studio:  http://localhost:1234/v1
              text-gen-webui: http://localhost:5000/v1
              OpenRouter: https://openrouter.ai/api/v1  (set --api-key)
        """),
    )
    parser.add_argument("--pipeline", "-p", default="rhoso-delivery",
                        choices=list(PIPELINE_STAGES.keys()),
                        help="Pipeline to execute (default: rhoso-delivery)")
    parser.add_argument("--stage", "-s", help="Single stage abbreviation (RDA, RDE-1, etc.)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help=f"OpenAI-compatible API URL (default: {DEFAULT_API_BASE})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key (default: 'ollama' for local)")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS, help=f"Max tool-call rounds per stage (default: {MAX_ITERATIONS})")

    args = parser.parse_args()

    set_max_iterations(args.max_iterations)

    run_pipeline(args)


if __name__ == "__main__":
    main()
