#!/usr/bin/env python3
"""
CPAT Agent Pipeline Runner — runs RHOSO DA + RDE agents via Cursor SDK.

Usage:
    export CURSOR_API_KEY="cursor_..."
    python run_pipeline.py                    # Full delivery pipeline
    python run_pipeline.py --pipeline rda     # RDA only
    python run_pipeline.py --pipeline rde     # RDE only
    python run_pipeline.py --stage RDE-2      # Single sub-stage
"""

import argparse
import os
import sys
import time
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, LocalAgentOptions, CursorAgentError


CPAT_ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("CPAT_AGENT_MODEL", "composer-2.5")

# ── RHOSO stages ──────────────────────────────────────────────
_RHOSO_DA_STAGES = [
    {
        "abbrev": "RDA-1",
        "prompt": (
            "You are the RHOSO DA agent. sub_stage=Schema. Generate the CIQ "
            "schema source code (18 tables, 210+ params, v1.4) at "
            "output/ciq-generators/rhoso_ciq_schema.py. Follow the agent rule "
            "at .cursor/rules/agent-rhoso-da.md exactly."
        ),
        "verify_paths": [
            "output/ciq-generators/rhoso_ciq_schema.py",
        ],
    },
    {
        "abbrev": "RDA-2",
        "prompt": (
            "You are the RHOSO DA agent. sub_stage=Generator. Read the schema "
            "from output/ciq-generators/rhoso_ciq_schema.py, then generate the "
            "CIQ workbook generator (9 sheets, 14 conditional formatting rules, "
            "20 dropdowns) at output/ciq-generators/generate_rhoso_ciq_workbooks.py "
            "and output/ciq-generators/requirements.txt. Do NOT execute the generator."
        ),
        "verify_paths": [
            "output/ciq-generators/generate_rhoso_ciq_workbooks.py",
            "output/ciq-generators/requirements.txt",
        ],
    },
    {
        "abbrev": "RDA-3",
        "prompt": (
            "You are the RHOSO DA agent. sub_stage=Workbooks. Execute: "
            "pip install openpyxl && python output/ciq-generators/generate_rhoso_ciq_workbooks.py. "
            "Verify .xlsx files exist at output/ciq-workbooks/rhoso/."
        ),
        "verify_paths": [
            "output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx",
            "output/ciq-workbooks/rhoso/rhoso-ciq-template.xlsx",
        ],
    },
]

_RHOSO_DE_STAGES = [
    {
        "abbrev": "RDE-1",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Ansible. "
            "Generate the complete Ansible layer: 25 task files in 9 subdirs, "
            "19 Jinja2 templates, ~170 defaults, library modules, module_utils "
            "(v1.4 schema). Write all files to output/cpat/ansible/. Follow the "
            "agent rule at .cursor/rules/agent-rhoso-deployment-engineer.md."
        ),
        "verify_paths": [
            "output/cpat/ansible/playbooks/roles/rhoso/tasks/main.yml",
            "output/cpat/ansible/playbooks/roles/rhoso/templates/openstack_control_plane.yaml.j2",
            "output/cpat/ansible/playbooks/roles/rhoso/defaults/main.yml",
        ],
    },
    {
        "abbrev": "RDE-2",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Backend. "
            "Generate the complete Flask backend: app.py (19 routes), "
            "ansible_runner.py (19 task tags), ciq_parser.py (cross-sheet), "
            "models.py, paths.py, input_files.py, version.py, "
            "rhoso_ciq_schema.py shim, requirements.txt. Write all files to "
            "output/cpat/backend/. Read the CIQ schema from "
            "output/cpat/ansible/module_utils/rhoso_ciq_schema.py."
        ),
        "verify_paths": [
            "output/cpat/backend/app.py",
            "output/cpat/backend/ansible_runner.py",
        ],
    },
    {
        "abbrev": "RDE-3",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Frontend. "
            "Generate the complete React frontend: 11 components, App.jsx, "
            "api.js, index.css, vite.config.js, package.json, nginx config, "
            "logos. Write all files to output/cpat/frontend/. Match API routes "
            "from output/cpat/backend/app.py."
        ),
        "verify_paths": [
            "output/cpat/frontend/src/components/RhosoInstallation.jsx",
            "output/cpat/frontend/package.json",
        ],
    },
    {
        "abbrev": "RDE-4",
        "prompt": (
            "You are the RHOSO Deployment Engineer agent. sub_stage=Docker. "
            "Generate Dockerfile (multi-stage Node+Python+Nginx), "
            "docker/entrypoint.sh, bringup.sh (Podman lifecycle), "
            ".dockerignore, and USAGE.md. Write to output/cpat/."
        ),
        "verify_paths": [
            "output/cpat/Dockerfile",
            "output/cpat/bringup.sh",
            "output/cpat/USAGE.md",
        ],
    },
]

# ── OCP stages ────────────────────────────────────────────────
_OCP_DA_STAGES = [
    {
        "abbrev": "ODA-1",
        "prompt": (
            "You are the OCP DA agent. sub_stage=Schema. Generate the OCP CIQ "
            "schema source code (~18 tables, ~180 params, v1.0) at "
            "output/ciq-generators/ocp_ciq_schema.py. Follow the agent rule "
            "at .cursor/rules/agent-ocp-da.md exactly."
        ),
        "verify_paths": [
            "output/ciq-generators/ocp_ciq_schema.py",
        ],
    },
    {
        "abbrev": "ODA-2",
        "prompt": (
            "You are the OCP DA agent. sub_stage=Generator. Read the schema "
            "from output/ciq-generators/ocp_ciq_schema.py, then generate the "
            "OCP workbook generator (8 sheets) at "
            "output/ciq-generators/generate_ocp_ciq_workbooks.py and "
            "output/ciq-generators/requirements.txt. Do NOT execute the generator."
        ),
        "verify_paths": [
            "output/ciq-generators/generate_ocp_ciq_workbooks.py",
            "output/ciq-generators/requirements.txt",
        ],
    },
    {
        "abbrev": "ODA-3",
        "prompt": (
            "You are the OCP DA agent. sub_stage=Workbooks. Execute: "
            "pip install openpyxl && python output/ciq-generators/generate_ocp_ciq_workbooks.py. "
            "Verify .xlsx files exist at output/ciq-workbooks/ocp/."
        ),
        "verify_paths": [
            "output/ciq-workbooks/ocp/sample-ocp.ciq.xlsx",
            "output/ciq-workbooks/ocp/ocp-ciq-template.xlsx",
        ],
    },
]

_OCP_DE_STAGES = [
    {
        "abbrev": "ODE-1",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Ansible. "
            "Generate the complete OCP Ansible role: ~20 task files in 9 subdirs, "
            "12 Jinja2 templates, ~120 defaults. Write all files to "
            "output/cpat/ansible/playbooks/roles/ocp/. Follow the agent rule "
            "at .cursor/rules/agent-ocp-deployment-engineer.md."
        ),
        "verify_paths": [
            "output/cpat/ansible/playbooks/roles/ocp/tasks/main.yml",
            "output/cpat/ansible/playbooks/roles/ocp/defaults/main.yml",
            "output/cpat/ansible/playbooks/ocp_install.yml",
        ],
    },
    {
        "abbrev": "ODE-2",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Backend. "
            "Generate ciq_parser.py (unified RHOSO+OCP), update ansible_runner.py with OCP task "
            "tags, update app.py with OCP routes. Write to output/cpat/backend/."
        ),
        "verify_paths": [
            "output/cpat/backend/ciq_parser.py",
        ],
    },
    {
        "abbrev": "ODE-3",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Frontend. "
            "Generate OcpInstallation.jsx and ocpInputFiles.js. Write to "
            "output/cpat/frontend/src/. Match API routes from backend."
        ),
        "verify_paths": [
            "output/cpat/frontend/src/components/OcpInstallation.jsx",
        ],
    },
    {
        "abbrev": "ODE-4",
        "prompt": (
            "You are the OCP Deployment Engineer agent. sub_stage=Docker. "
            "Update Dockerfile, bringup.sh, and USAGE.md with OCP support. "
            "Write to output/cpat/."
        ),
        "verify_paths": [
            "output/cpat/Dockerfile",
            "output/cpat/bringup.sh",
            "output/cpat/USAGE.md",
        ],
    },
]

# ── Pipeline registry ─────────────────────────────────────────
PIPELINE_STAGES = {
    "rhoso-delivery": _RHOSO_DA_STAGES + _RHOSO_DE_STAGES,
    "rda":            _RHOSO_DA_STAGES,
    "rde":            _RHOSO_DE_STAGES,
    "ocp-delivery":   _OCP_DA_STAGES + _OCP_DE_STAGES,
    "oda":            _OCP_DA_STAGES,
    "ode":            _OCP_DE_STAGES,
    "full-delivery":  _RHOSO_DA_STAGES + _RHOSO_DE_STAGES + _OCP_DA_STAGES + _OCP_DE_STAGES,
}


def verify_outputs(stage: dict) -> tuple[int, int]:
    """Check that expected output files exist and are non-empty."""
    found = missing = 0
    for rel in stage["verify_paths"]:
        p = CPAT_ROOT / rel
        if p.exists() and p.stat().st_size > 0:
            found += 1
        else:
            missing += 1
            print(f"  ⚠ MISSING: {rel}", file=sys.stderr)
    return found, missing


def run_pipeline(pipeline_id: str, single_stage: str | None = None):
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        print("ERROR: Set CURSOR_API_KEY environment variable.", file=sys.stderr)
        print("  Get your key at: https://cursor.com/dashboard/integrations", file=sys.stderr)
        sys.exit(1)

    stages = PIPELINE_STAGES.get(pipeline_id)
    if not stages:
        print(f"ERROR: Unknown pipeline '{pipeline_id}'. "
              f"Available: {', '.join(PIPELINE_STAGES.keys())}", file=sys.stderr)
        sys.exit(1)

    if single_stage:
        stages = [s for s in stages if s["abbrev"] == single_stage]
        if not stages:
            print(f"ERROR: Stage '{single_stage}' not found in pipeline '{pipeline_id}'.",
                  file=sys.stderr)
            sys.exit(1)

    total = len(stages)
    print(f"\n{'='*60}")
    print(f"CPAT Pipeline: {pipeline_id} — {total} stage(s)")
    print(f"Model: {MODEL}")
    print(f"Working directory: {CPAT_ROOT}")
    print(f"{'='*60}\n")

    for i, stage in enumerate(stages, 1):
        abbrev = stage["abbrev"]
        print(f"[{i}/{total}] {abbrev} — Starting...")
        t0 = time.time()

        try:
            with Agent.create(
                model=MODEL,
                api_key=api_key,
                local=LocalAgentOptions(cwd=str(CPAT_ROOT)),
            ) as agent:
                run = agent.send(stage["prompt"])

                for message in run.messages():
                    if message.type == "assistant":
                        for block in message.message.content:
                            if block.type == "text":
                                print(block.text, end="")

                result = run.wait()
                elapsed = time.time() - t0

                if result.status == "error":
                    print(f"\n❌ [{abbrev}] Run failed after {elapsed:.0f}s", file=sys.stderr)
                    print(f"   Run ID: {run.id}", file=sys.stderr)
                    sys.exit(2)

                found, missing = verify_outputs(stage)
                status = "✅" if missing == 0 else "⚠️"
                print(f"\n{status} [{abbrev}] Complete in {elapsed:.0f}s — "
                      f"{found} verified, {missing} missing\n")

                if missing > 0:
                    print(f"  WARNING: {missing} expected file(s) not found. "
                          "Stage may have partially completed.", file=sys.stderr)

        except CursorAgentError as err:
            print(f"\n❌ [{abbrev}] Agent startup failed: {err.message}", file=sys.stderr)
            if err.is_retryable:
                print("  (retryable — check API key and network)", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Pipeline '{pipeline_id}' complete — {total} stage(s) finished.")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="CPAT Agent Pipeline Runner (Cursor SDK)")
    parser.add_argument(
        "--pipeline", "-p",
        default="rhoso-delivery",
        choices=list(PIPELINE_STAGES.keys()),
        help="Pipeline to execute (default: rhoso-delivery)",
    )
    parser.add_argument(
        "--stage", "-s",
        default=None,
        help="Run a single stage by abbreviation (e.g., RDA, RDE-1, RDE-2)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help=f"Override model (default: {MODEL})",
    )
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    run_pipeline(args.pipeline, args.stage)


if __name__ == "__main__":
    main()
