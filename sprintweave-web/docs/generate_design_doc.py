"""Generate SprintWeave Design Document (.docx) — comprehensive architecture,
setup, execution, agents, inputs/outputs, sample logs, and code structure.

Run:  python generate_design_doc.py
Requires: pip install python-docx
"""

from pathlib import Path
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor, Cm

OUT = Path(__file__).with_name("SprintWeave_Design_Document_v3.docx")
BLUE = RGBColor(0x2B, 0x57, 0x9A)
RED = RGBColor(0xCC, 0x00, 0x00)
GRAY = RGBColor(0x66, 0x66, 0x66)
GREEN = RGBColor(0x22, 0x7D, 0x51)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def shade_cell(cell, hex_color="2B579A"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def add_table(doc, headers, rows, header_color="2B579A"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.color.rgb = WHITE
                r.font.size = Pt(9)
        shade_cell(cell, header_color)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()
    return table


def code(doc, text, font_size=8):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(font_size)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.space_before = Pt(4)
    return p


def note(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = GRAY


def bullet(doc, text, level=0):
    p = doc.add_paragraph(text, style="List Bullet")
    p.paragraph_format.left_indent = Cm(1.27 + level * 0.63)
    for r in p.runs:
        r.font.size = Pt(10)


def numbered(doc, text):
    p = doc.add_paragraph(text, style="List Number")
    for r in p.runs:
        r.font.size = Pt(10)


def bold_para(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(10)


def main():
    doc = Document()
    s = doc.sections[0]
    s.left_margin = Inches(0.9)
    s.right_margin = Inches(0.9)
    s.top_margin = Inches(0.8)

    # ── Title Page ──────────────────────────────────────────────
    for _ in range(4):
        doc.add_paragraph()

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("SprintWeave Agent Platform\nDesign Document")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = BLUE

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("AI-Powered Delivery Automation on OpenShift")
    r2.font.size = Pt(16)
    r2.font.color.rgb = GRAY

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Version 3.0 — {datetime.now().strftime('%B %Y')}").font.size = Pt(11)

    meta2 = doc.add_paragraph()
    meta2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = meta2.add_run("RHOSO 18.0 + OCP 4.17–4.20 Delivery Pipelines")
    r3.italic = True
    r3.font.size = Pt(11)

    doc.add_page_break()

    # ── Table of Contents (manual) ─────────────────────────────
    doc.add_heading("Table of Contents", level=1)
    toc_items = [
        "1. Executive Summary",
        "2. Architecture Overview",
        "   2.1 High-Level Architecture",
        "   2.2 Two-Folder Build Model",
        "   2.3 OpenShift Runtime Architecture",
        "   2.4 Image Build Strategy (Docling Split)",
        "   2.5 OpenShift Objects",
        "3. Agent Design",
        "   3.1 How Agents Work",
        "   3.2 Agent Rules (.cursor/rules/)",
        "   3.3 Agent Skills (.cursor/skills/)",
        "   3.4 Pipeline Configuration (pipelines.yaml)",
        "   3.5 Validator Registry",
        "   3.6 Validate → Fix Loop",
        "4. Pipeline Stages",
        "   4.1 RHOSO Delivery Pipeline",
        "   4.2 OCP Delivery Pipeline",
        "   4.3 Stage Execution Modes",
        "5. Setup & Deployment",
        "   5.1 Prerequisites",
        "   5.2 Build Steps",
        "   5.3 OpenShift Deployment",
        "   5.4 Bastion Bringup Script",
        "6. Inputs & Outputs",
        "   6.1 Input Documents",
        "   6.2 Workspace Layout",
        "   6.3 Output Artifacts",
        "7. Sample Execution",
        "   7.1 RHOSO Pipeline Log (Real Run)",
        "   7.2 Stage-by-Stage Breakdown",
        "8. Code Structure",
        "   8.1 Repository Layout",
        "   8.2 Key Source Files",
        "   8.3 Configuration Reference",
        "9. Quality & Cost",
        "   9.1 Quality Improvements",
        "   9.2 Cost Estimates",
        "10. Troubleshooting",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(2)
        for r in p.runs:
            r.font.size = Pt(10)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("1. Executive Summary", level=1)

    doc.add_paragraph(
        "SprintWeave is an AI-powered delivery automation platform that turns uploaded "
        "customer documents (PDF, DOCX, Excel) into production-ready delivery artifacts — "
        "CIQ workbooks, Ansible playbooks, Python backends, React frontends, Dockerfiles, "
        "and AAP (Ansible Automation Platform) exports — by running AI agents on OpenShift."
    )
    doc.add_paragraph(
        "The platform uses agent rules (.cursor/rules/*.md) to define each AI agent's behavior — "
        "its role, capabilities, output format, and constraints. These rules drive the LLM to "
        "generate complete, validated, production-ready code on OpenShift."
    )

    bold_para(doc, "Key Capabilities:")
    bullet(doc, "Document parsing (PDF/DOCX) via Docling — extracts text, tables, structure")
    bullet(doc, "Multi-stage pipelines with human approval gates")
    bullet(doc, "Cursor-like tool loop — agents write files, run Python, iterate")
    bullet(doc, "Validate → Fix loop — generated code is validated and self-corrected by the LLM")
    bullet(doc, "Data-driven pipeline config — stages, validators, deploy specs in YAML")
    bullet(doc, "One-click CPAT deploy to OpenShift (binary build + Route)")
    bullet(doc, "Custom agents without image rebuild (PVC-based)")

    bold_para(doc, "Current Agent Scope:")
    add_table(doc, ["Agent", "Role", "Pipeline"], [
        ["RHOSO DA", "Design Authority — CIQ schema + workbook generation", "rhoso-delivery, rhoso-da"],
        ["RHOSO DE", "Deployment Engineer — Ansible, Backend, Frontend, Docker, AAP", "rhoso-delivery, rhoso-de"],
        ["OCP DA", "Design Authority — OCP CIQ schema + workbooks", "ocp-delivery, ocp-da"],
        ["OCP DE", "Deployment Engineer — OCP Ansible, Backend, Frontend, Docker, AAP", "ocp-delivery, ocp-de"],
        ["Orchestrator", "Pipeline coordination and stage routing", "All pipelines"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 2. ARCHITECTURE OVERVIEW
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("2. Architecture Overview", level=1)

    doc.add_heading("2.1 High-Level Architecture", level=2)

    code(doc, """
    Customer Inputs (PDF / DOCX / Excel / TXT)
                        |
                        v
              +-------------------+
              |  Agent Rules      |  .cursor/rules/*.md
              |  Templates        |  context/templates/
              |  Skills           |  .cursor/skills/
              |  Pipeline Config  |  context/pipelines.yaml
              +-------------------+
                        |
                        v
          +-------------------------------+
          |  OpenShift SprintWeave        |
          |  Streamlit UI + FastAPI       |
          |  worker.py + LangGraph        |
          |  LLM_API_KEY (MaaS / Azure)   |
          +-------------------------------+
                        |
                        v
              /data/jobs/<id>/output/
              (PVC + zip download)
""")

    doc.add_paragraph(
        "Agent rules define each agent's behavior. The engine loads these rules and "
        "orchestrates a tool-calling loop on OpenShift where the LLM generates production-ready code."
    )

    doc.add_heading("2.2 Two-Folder Build Model", level=2)
    doc.add_paragraph(
        "The platform builds from exactly two source folders. No dependency on "
        "sprintweave-agents — cpat-main is fully self-contained."
    )

    add_table(doc, ["Folder", "Contents", "Maps To (Container)"], [
        ["sprintweave-web/", "Runtime engine: API, UI, LLM client, prompts, deploy scripts", "/app/sprintweave-web/"],
        ["cpat-main/", "Agent rules, skills, pipeline config, context, templates, golden output", "/app/sprintweave-agents/"],
    ])

    doc.add_heading("2.3 OpenShift Runtime Architecture", level=2)

    code(doc, """
 Browser (HTTPS Route, TLS edge termination)
    |
    v
 sprintweave-ui   (Streamlit :8080)  — NO LLM key, NO PVC
    |  env: SPRINTWEAVE_API_URL=http://sprintweave-api:8000
    v
 sprintweave-api  (FastAPI + background worker :8000)
    |  Secret: sprintweave-llm → LLM_API_KEY
    |  ConfigMap: sprintweave-config (model, Docling, LangGraph, etc.)
    |  PVC: sprintweave-data → /data (jobs, inputs, custom agents)
    |
    +--→ Docling      (PDF/DOCX → parsed/*.md)
    +--→ MaaS/LLM     POST /v1/chat/completions (with tool calling)
    +--→ Workspace     /data/jobs/<id>/workspace/ (input → parsed → output)
    +--→ Custom Agents /data/custom-agents/ (PVC catalog, no rebuild)
""")

    bold_para(doc, "Why two Deployments?")
    bullet(doc, "UI never holds the LLM API key (security boundary)")
    bullet(doc, "PVC is RWO — API replicas must stay at 1")
    bullet(doc, "UI can scale independently for concurrent users")

    doc.add_heading("2.4 Image Build Strategy (Docling Split)", level=2)

    code(doc, """
┌──────────────────────────────────────┐
│ sprintweave-docling-base             │  Dockerfile.docling-base
│  • python:3.12-slim                  │  Rebuild: RARELY (hours, multi-GB)
│  • docling + OCR libs + HF models    │
└──────────────────┬───────────────────┘
                   │ FROM
                   v
┌──────────────────────────────────────┐
│ sprintweave-rhoso                    │  Dockerfile (root)
│  • FastAPI / Streamlit / LangGraph   │  Rebuild: OFTEN (3–5 minutes)
│  • COPY sprintweave-web/ → engine    │
│  • COPY cpat-main/ → agents          │
│  • oc CLI for CPAT deploy            │
└──────────────────────────────────────┘
""")

    doc.add_heading("2.5 OpenShift Objects", level=2)

    add_table(doc, ["Object", "Name", "Purpose"], [
        ["Namespace", "sprintweave", "Project isolation"],
        ["Deployment", "sprintweave-api", "FastAPI + worker + Docling"],
        ["Deployment", "sprintweave-ui", "Streamlit web UI"],
        ["Service", "sprintweave-api :8000", "Internal API"],
        ["Service", "sprintweave-ui :8080", "Internal UI"],
        ["Route", "sprintweave-ui", "Public HTTPS (TLS edge)"],
        ["PVC", "sprintweave-data (10Gi)", "Jobs, uploads, custom agents"],
        ["ConfigMap", "sprintweave-config", "LLM settings, pipeline flags"],
        ["Secret", "sprintweave-llm", "LLM_API_KEY only"],
        ["ServiceAccount", "sprintweave-api", "RBAC for CPAT deploy"],
        ["Role + RoleBinding", "sprintweave-cpat-deploy", "BuildConfig, ImageStream, Deployment, Route"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 3. AGENT DESIGN
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("3. Agent Design", level=1)

    doc.add_heading("3.1 How Agents Work", level=2)

    doc.add_paragraph(
        "Each agent is defined by a rule file (.cursor/rules/agent-*.md) that contains "
        "the agent's system prompt — its role, capabilities, output format, and constraints. "
        "The engine (worker.py) loads this rule as the LLM system message and orchestrates "
        "a tool-calling loop where the LLM can read files, write code, and run Python scripts "
        "in a sandboxed workspace."
    )

    bold_para(doc, "Agent Execution Flow:")
    code(doc, """
1. Worker loads agent rule markdown from .cursor/rules/
2. Worker loads pipeline stage config from pipelines.yaml
3. Worker seeds workspace with context/ (templates, glossaries, pipelines.yaml)
4. Worker sends system prompt (rule + tool instructions) to LLM
5. LLM calls tools: write_file, read_file, list_dir, run_python, etc.
6. Worker executes tool calls in the workspace
7. After sub-stage completes → run validators
8. If validators find errors → feed errors back to LLM → fix round
9. Repeat validation up to 3 rounds
10. Move to next sub-stage or pipeline gate
""")

    bold_para(doc, "Available Tools:")
    add_table(doc, ["Tool", "Description"], [
        ["list_dir(path)", "List directory contents"],
        ["read_file(path)", "Read file contents"],
        ["write_file(path, content)", "Write complete file"],
        ["append_file(path, content)", "Append to existing file"],
        ["str_replace(path, old, new)", "Replace text in file (hunk edit)"],
        ["delete_file(path)", "Delete a file"],
        ["run_python(script_path)", "Execute a Python script in the workspace"],
        ["search_files(pattern)", "Search for files matching a pattern"],
    ])

    doc.add_heading("3.2 Agent Rules (.cursor/rules/)", level=2)

    doc.add_paragraph(
        "Agent rules are Markdown files that define each agent's behavior. "
        "The same rules work in both Cursor IDE and OpenShift SprintWeave."
    )

    add_table(doc, ["Rule File", "Agent", "Scope"], [
        ["agent-orchestrator.md", "Orchestrator", "Pipeline coordination, stage routing"],
        ["agent-rhoso-da.md", "RHOSO DA", "CIQ schema extraction, workbook generation"],
        ["agent-rhoso-deployment-engineer.md", "RHOSO DE", "Ansible, Backend, Frontend, Docker, AAP"],
        ["agent-ocp-da.md", "OCP DA", "OCP CIQ schema extraction, workbook generation"],
        ["agent-ocp-deployment-engineer.md", "OCP DE", "OCP Ansible, Backend, Frontend, Docker, AAP"],
        ["00-sprintweave-*.md (×8)", "Platform", "Security, grounding, gates, canvas, etc."],
    ])

    bold_para(doc, "Example: Agent Rule Structure (RHOSO DE)")
    code(doc, """# RHOSO Deployment Engineer — Agent Rule (v1.4)

## Role
You are the RHOSO Deployment Engineer. You generate production-ready
CPAT code from CIQ parameters parsed by the RHOSO DA.

## Sub-stages
- RDE-1: Ansible (playbooks, roles, Jinja2 templates, module_utils)
- RDE-2: Backend (Flask API, models, parsers, CIQ schema)
- RDE-3: Frontend (React JSX, components, API client)
- RDE-4: Docker (Dockerfile, entrypoint.sh, nginx, bringup.sh)
- RDE-5: AAP (EE definition, credential types, job templates)

## RDE-4 Docker Reference — OpenShift-Safe Patterns
[Contains reference Dockerfile and entrypoint.sh patterns
 that the LLM reads as context and generates from scratch]

## Validators
python_syntax, python_imports, frontend_jsx, dockerfile,
entrypoint_sh, nginx_conf
""", font_size=7)

    doc.add_heading("3.3 Agent Skills (.cursor/skills/)", level=2)

    add_table(doc, ["Skill", "Purpose"], [
        ["sprintweave-setup/SKILL.md", "First-time workspace setup instructions"],
        ["sprintweave-pipelines/SKILL.md", "Pipeline stage definitions and routing"],
        ["sprintweave-gates/SKILL.md", "Approval gate logic and human review"],
        ["sprintweave-custom-agent/SKILL.md", "Custom agent creation (PVC-based)"],
    ])

    doc.add_heading("3.4 Pipeline Configuration (pipelines.yaml)", level=2)

    doc.add_paragraph(
        "All pipeline knowledge lives in pipelines.yaml — worker.py reads it generically. "
        "No agent-specific hardcoded logic in the engine."
    )

    bold_para(doc, "Example Stage Definition:")
    code(doc, """custom:
  - id: rhoso-delivery
    name: "RHOSO Delivery"
    stages:
      - abbrev: RDE-2
        agent: "RHOSO Deployment Engineer"
        sub_stage: "Backend"
        generates: ["output/cpat/backend/"]
        validators: [python_syntax, python_imports]
        layer: backend
      - abbrev: RDE-4
        agent: "RHOSO Deployment Engineer"
        sub_stage: "Docker"
        generates: ["output/cpat/Dockerfile"]
        validators: [dockerfile, entrypoint_sh, nginx_conf]
        layer: docker
    deploy_spec:
      type: container
      context_dir: output/cpat
      dockerfile: Dockerfile
      port: 8080
      readiness_path: /api/health
""", font_size=7)

    bold_para(doc, "Seven Pipelines Defined:")
    add_table(doc, ["Pipeline ID", "Name", "Stages"], [
        ["rhoso-delivery", "RHOSO Delivery", "RDA-1→3, RDE-1→5 (full)"],
        ["rhoso-da", "RHOSO DA Only", "RDA-1→3"],
        ["rhoso-de", "RHOSO DE Only", "RDE-1→5"],
        ["ocp-delivery", "OCP Delivery", "ODA-1→3, ODE-1→5 (full)"],
        ["ocp-da", "OCP DA Only", "ODA-1→3"],
        ["ocp-de", "OCP DE Only", "ODE-1→5"],
        ["full-delivery", "Full Delivery", "RHOSO + OCP combined"],
    ])

    doc.add_heading("3.5 Validator Registry", level=2)

    add_table(doc, ["Validator", "What It Checks", "Used By Stages"], [
        ["python_syntax", "ast.parse every .py file — catches truncated functions, bad indentation", "RDE-2 (Backend)"],
        ["python_imports", "Resolves from X import Y across modules — catches missing symbols", "RDE-2 (Backend)"],
        ["frontend_jsx", "Brace/paren balance on JSX/JS files — catches truncated components", "RDE-3 (Frontend)"],
        ["dockerfile", "ENTRYPOINT/CMD present, no bad COPY, EXPOSE correct", "RDE-4 (Docker)"],
        ["entrypoint_sh", "set -e present, no fatal chmod on mount root", "RDE-4 (Docker)"],
        ["nginx_conf", "Config exists, listen 8080 (not 80), temp dirs under /tmp", "RDE-4 (Docker)"],
        ["yaml_lint", "YAML syntax check on all .yaml files", "RDE-1 (Ansible)"],
    ])

    doc.add_heading("3.6 Validate → Fix Loop", level=2)

    code(doc, """
┌─────────────────┐
│ LLM generates    │
│ code for stage   │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌──────────────────┐
│ Run validators   │────→│ All pass?        │──→ Next stage ✓
│ (from pipeline   │     │                  │
│  config)         │     └──────────────────┘
└────────┬────────┘              │
         │ Errors found          │ No
         v                       v
┌─────────────────┐     ┌──────────────────┐
│ Feed errors back │────→│ Round < 3?       │──→ Best effort, continue
│ to LLM           │     │                  │
│ "Fix these:"     │     └──────────────────┘
└─────────────────┘
""")

    doc.add_paragraph(
        "This is the biggest quality improvement. Previously, generated code shipped without "
        "validation. Now every sub-stage runs validators and the LLM self-corrects up to 3 times."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 4. PIPELINE STAGES
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("4. Pipeline Stages", level=1)

    doc.add_heading("4.1 RHOSO Delivery Pipeline", level=2)

    add_table(doc, ["Stage", "Agent", "Mode", "Produces", "Validators"], [
        ["RDA-1", "RHOSO DA", "Single-shot", "CIQ schema (rhoso_ciq_schema.py)", "—"],
        ["RDA-2", "RHOSO DA", "Single-shot", "Workbook generator + requirements.txt", "—"],
        ["RDA-3", "RHOSO DA", "Run Python", "Excel workbooks (.xlsx)", "—"],
        ["⏸ Gate", "Human", "Approve/Reject", "Review RDA artifacts", "—"],
        ["RDE-1", "RHOSO DE", "LangGraph tool-loop", "Ansible roles, templates, module_utils", "yaml_lint"],
        ["RDE-2", "RHOSO DE", "Single-shot + validate", "Backend (app.py, models, parsers)", "python_syntax, python_imports"],
        ["RDE-3", "RHOSO DE", "Single-shot + validate", "Frontend (React JSX components)", "frontend_jsx"],
        ["RDE-4", "RHOSO DE", "Single-shot + validate", "Dockerfile, entrypoint.sh, nginx, bringup.sh", "dockerfile, entrypoint_sh, nginx_conf"],
        ["RDE-5", "RHOSO DE", "Single-shot", "AAP export (EE, cred types, job templates)", "—"],
        ["⏸ Gate", "Human", "Approve/Reject", "Review all artifacts", "—"],
        ["Deploy", "cpat_deploy.py", "Automatic", "Binary build → OpenShift Route", "Pre-build validation"],
    ])

    doc.add_heading("4.2 OCP Delivery Pipeline", level=2)
    doc.add_paragraph(
        "Mirrors the RHOSO pipeline with OCP-specific agents and templates. "
        "ODE-5 generates shared EE definition + credential types + OCP-specific job templates."
    )

    doc.add_heading("4.3 Stage Execution Modes", level=2)

    add_table(doc, ["Mode", "When Used", "How It Works"], [
        ["Single-shot", "RDA, RDE Backend/Frontend/Docker", "One LLM call → parse ### FILE: blocks → write files"],
        ["Tool-loop (LangGraph)", "RDE Ansible, custom agents", "Multi-step: LLM calls tools iteratively (write, read, run_python)"],
        ["Until-complete rounds", "Ansible sub-stage", "Multiple rounds until all required files exist (up to 15 rounds)"],
        ["Validate → Fix", "All RDE stages", "Post-generation validators + LLM self-correction (up to 3 rounds)"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 5. SETUP & DEPLOYMENT
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("5. Setup & Deployment", level=1)

    doc.add_heading("5.1 Prerequisites", level=2)

    add_table(doc, ["Requirement", "Details"], [
        ["OpenShift cluster", "4.14+ (tested on 4.22), ≥12Gi memory available"],
        ["oc CLI", "Logged in with project-create permissions"],
        ["Podman or Docker", "On bastion node for image builds"],
        ["Quay registry", "quay.io org with push access"],
        ["LLM API key", "OpenAI-compatible endpoint (MaaS-RHDP, Azure, Anthropic)"],
        ["Source tree", "CFP_NEW/ with sprintweave-web/ + cpat-main/"],
    ])

    doc.add_heading("5.2 Build Steps", level=2)

    bold_para(doc, "Step 1 — Transfer to bastion:")
    code(doc, """# From WSL/laptop (inside CFP_NEW/):
bash sprintweave-web/scripts/pack-to-bastion.sh
# Packs sprintweave-web + cpat-main + Dockerfile + bringup.sh → SCP to bastion""")

    bold_para(doc, "Step 2 — Build Docling base (one-time, ~20 min):")
    code(doc, """./bringup.sh build-base""")

    bold_para(doc, "Step 3 — Build app image (every code change, ~3 min):")
    code(doc, """./bringup.sh build""")

    bold_para(doc, "Step 4 — Push to Quay:")
    code(doc, """export REGISTRY=quay.io/rh_global_services_auto
./bringup.sh push""")

    doc.add_heading("5.3 OpenShift Deployment", level=2)

    bold_para(doc, "Step 5 — Create namespace + secrets:")
    code(doc, """export LLM_API_KEY=sk-your-key-here
./bringup.sh setup""")

    bold_para(doc, "Step 6 — Deploy:")
    code(doc, """./bringup.sh apply""")

    bold_para(doc, "All-in-one:")
    code(doc, """export REGISTRY=quay.io/rh_global_services_auto
export LLM_API_KEY=sk-your-key-here
./bringup.sh deploy""")

    doc.add_heading("5.4 Bastion Bringup Script Commands", level=2)

    add_table(doc, ["Command", "Description"], [
        ["./bringup.sh build-base", "Build Docling base image (slow, one-time)"],
        ["./bringup.sh build", "Build thin app image (fast, every code change)"],
        ["./bringup.sh push", "Push images to Quay registry"],
        ["./bringup.sh setup", "Create OCP namespace + LLM secret"],
        ["./bringup.sh apply", "Apply manifests + rollout deployments"],
        ["./bringup.sh deploy", "Full pipeline: build → push → setup → apply"],
        ["./bringup.sh status", "Show pods, routes, PVCs"],
        ["./bringup.sh logs", "Tail API pod logs"],
        ["./bringup.sh export", "Save image as .tar for air-gapped transfer"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 6. INPUTS & OUTPUTS
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("6. Inputs & Outputs", level=1)

    doc.add_heading("6.1 Input Documents", level=2)

    add_table(doc, ["Input Type", "Format", "Example"], [
        ["RHOSO Deployment Guide", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Deploying_*.pdf"],
        ["RHOSO Planning Guide", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Planning_*.pdf"],
        ["Storage Configuration", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Configuring_persistent_storage_*.pdf"],
        ["Disconnected Deployment", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Deploying_*_disconnected_*.pdf"],
        ["Multi-env Deployment", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Deploying_multiple_*.pdf"],
        ["Customization Guide", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Customizing_*.pdf"],
        ["Validation Guide", "PDF", "Red_Hat_OpenStack_Services_on_OpenShift-18.0-Validating_*.pdf"],
        ["Customer CIQ", "Excel/TXT", "Customer-specific configuration parameters"],
    ])

    doc.add_heading("6.2 Workspace Layout", level=2)

    code(doc, """/data/jobs/<job_id>/
  workspace/
    input/           ← uploaded customer files
    parsed/          ← Docling markdown (PDF → .md)
    context/         ← seeded from cpat-main/context/
      templates/     ← agent templates
      glossary*.yaml ← domain glossaries
      pipelines.yaml ← pipeline definitions
    .cursor/
      skills/        ← pipeline/gate skills
    output/          ← generated deliverables
      cpat/
        ansible/     ← playbooks, roles, templates, module_utils
        backend/     ← Python API (app.py, models, parsers)
        frontend/    ← React UI (JSX components)
        docker/      ← entrypoint.sh
        aap/         ← AAP export files
        Dockerfile
        bringup.sh
      ciq-generators/ ← CIQ schema + workbook generator
      ciq-workbooks/  ← Generated Excel workbooks
      pipeline-reports/ ← Stage reports (rda/, rde/)
  output/            ← mirrored for download API + zip""")

    doc.add_heading("6.3 Output Artifacts", level=2)

    add_table(doc, ["Stage", "Output Path", "Description"], [
        ["RDA", "output/ciq-generators/rhoso_ciq_schema.py", "CIQ parameter schema (207+ params)"],
        ["RDA", "output/ciq-generators/generate_rhoso_ciq_workbooks.py", "Workbook generator script"],
        ["RDA", "output/ciq-workbooks/rhoso/*.xlsx", "Excel CIQ workbooks"],
        ["RDE-1", "output/cpat/ansible/", "Playbooks, 19+ Jinja2 templates, roles, module_utils"],
        ["RDE-2", "output/cpat/backend/", "app.py, models.py, ciq_parser.py, paths.py, etc."],
        ["RDE-3", "output/cpat/frontend/", "React components, API client, CSS, vite config"],
        ["RDE-4", "output/cpat/Dockerfile", "OpenShift-safe multi-stage Dockerfile"],
        ["RDE-4", "output/cpat/docker/entrypoint.sh", "Gunicorn + nginx entrypoint"],
        ["RDE-4", "output/cpat/bringup.sh", "Container lifecycle script"],
        ["RDE-5", "output/cpat/aap/", "EE definition, credential types, job/workflow templates"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 7. SAMPLE EXECUTION
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("7. Sample Execution", level=1)

    doc.add_heading("7.1 RHOSO Pipeline Log (Real Run — October 2026)", level=2)

    code(doc, """[11:01:52] [workspace] linked inputs from /data/inputs/test245
[11:01:52] [workspace] seeded context/ from sprintweave-agents
[11:01:52] [workspace] seeded .cursor/skills/ (4 skills)

── Docling: Parse 8 RHOSO PDFs ──────────────────────────────
[11:02:24] [docling] parsing 8 file(s) — loading converter once
[11:02:24] [docling] converter ready in 0.4s
[11:04:59] [parsed] Configuring_persistent_storage.pdf → .md (155s)
[11:06:16] [parsed] Customizing_deployment.pdf → .md (77s)
[11:08:00] [parsed] Deploying_RHOSO.pdf → .md (104s)
[11:08:11] [parsed] Disconnected_environment.pdf → .md (11s)
[11:08:46] [parsed] Multiple_environments.pdf → .md (35s)
[11:09:44] [parsed] Planning_deployment.pdf → .md (58s)
[11:10:11] [parsed] Validating_troubleshooting.pdf → .md (27s)
[11:11:03] [parsed] rhoso-plan-18-0.pdf → .md (52s)
[11:11:03] [docling] done in 519.6s (ok=8, cache_hits=0)

── RDA: RHOSO Design Authority ──────────────────────────────
[11:11:04] [rda-single-shot] generating CIQ schema
[11:13:37] [rda-single-shot] wrote CIQ schema
[11:13:37] [rda-single-shot] generating workbook generator
[11:17:03] [rda-single-shot] wrote generator + requirements.txt
[11:17:04] [gate] RDA — review required before continuing

── RDE-1: Ansible (LangGraph tool-loop) ─────────────────────
[11:21:12] [lg-tool] list_dir("context/templates")
[11:21:15] [lg-tool] read_file("context/templates/rhoso-deployment-engineer.md")
[11:21:24] [lg-tool] write_file("output/cpat/ansible.cfg")
[11:21:24] [lg-tool] write_file("output/cpat/ansible/playbooks/main.yml")
  ... (steps 5-23: writing roles, tasks, 19 Jinja2 templates) ...
[11:30:19] [lg-tool] write_file("output/cpat/ansible/module_utils/rhoso_ciq_schema.py")
[11:33:18] [langgraph] hit max_steps=30
[11:33:18] [ansible-gate] COMPLETE after round 1/15
[11:33:18] [ansible-validate] PASS — all 8 checks passed
[11:33:18] [ansible-validate] PASS Schema parameter count ≥ 200 (found 207)
[11:33:18] [ansible-validate] PASS Jinja braces balanced (20 templates)
[11:33:18] [verify_paths] RDE-1 OK — 3 verified, 0 missing

── RDE-2: Backend (single-shot + validate) ──────────────────
[11:33:18] [rde-single-shot] Backend — one-shot generation
[11:36:37] [rde-single-shot] Backend wrote 10 file(s)
[11:36:37] [rde-single-shot] Backend self-check 1
  (validators: python_syntax ✓, python_imports ✓)

── RDE-3: Frontend ──────────────────────────────────────────
  (validators: frontend_jsx — brace balance)

── RDE-4: Docker ────────────────────────────────────────────
  (validators: dockerfile, entrypoint_sh, nginx_conf)

── RDE-5: AAP Export ────────────────────────────────────────
  (EE definition, credential types, job templates)
""", font_size=7)

    doc.add_heading("7.2 Stage-by-Stage Breakdown", level=2)

    add_table(doc, ["Stage", "Duration", "LLM Calls", "Files Written", "Validations"], [
        ["Docling (8 PDFs)", "~9 min", "0", "8 .md files", "—"],
        ["RDA (schema + generator)", "~6 min", "2-3", "4 files", "run_python exit check"],
        ["RDE-1 Ansible", "~12 min", "30 steps", "25+ files", "8 validators, all PASS"],
        ["RDE-2 Backend", "~3 min", "1-2", "10 files", "python_syntax + python_imports"],
        ["RDE-3 Frontend", "~3 min", "1-2", "12+ files", "frontend_jsx brace balance"],
        ["RDE-4 Docker", "~2 min", "1-2", "4 files", "dockerfile + entrypoint + nginx"],
        ["RDE-5 AAP", "~2 min", "1", "5+ files", "—"],
        ["Total", "~37 min", "~40", "~70 files", "All stages validated"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 8. CODE STRUCTURE
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("8. Code Structure", level=1)

    doc.add_heading("8.1 Repository Layout", level=2)

    code(doc, """CFP_NEW/
├── Dockerfile              ← Simplified root build file
├── bringup.sh              ← Bastion build + OCP deploy script
├── REVIEW.md               ← Review guide for colleagues
│
├── sprintweave-web/        ← RUNTIME ENGINE (57 files)
│   ├── api/
│   │   ├── main.py         ← FastAPI app + routes
│   │   ├── worker.py       ← Pipeline engine (4035 lines)
│   │   ├── cpat_deploy.py  ← OpenShift deploy logic
│   │   ├── custom_agents.py← PVC-based agent CRUD
│   │   ├── agent_runtime.py← Cursor-like tool execution
│   │   ├── langgraph_runtime.py ← LangGraph state graph
│   │   └── job_store.py    ← Job persistence
│   ├── ui/
│   │   └── app.py          ← Streamlit UI (Home, Run, Job, Agents, Deploy)
│   ├── llm/
│   │   └── client.py       ← OpenAI-compatible LLM client
│   ├── prompts/            ← System prompts
│   ├── deploy/openshift/   ← Kubernetes manifests
│   ├── scripts/            ← Build helpers, pack-to-bastion
│   ├── Dockerfile.bundle   ← Legacy build (AGENTS_SRC arg)
│   ├── Dockerfile.docling-base ← Heavy base image
│   └── requirements.txt
│
└── cpat-main/              ← AGENT CONFIG (220 files, self-contained)
    ├── .cursor/
    │   ├── rules/          ← 13 agent + platform rules
    │   └── skills/         ← 4 pipeline/gate/setup skills
    ├── context/
    │   ├── pipelines.yaml  ← All 7 pipeline definitions (v3)
    │   ├── team-config.yaml
    │   ├── glossary*.yaml  ← 4 glossary files
    │   ├── nrho-contract.yaml
    │   └── templates/      ← Agent templates + reference patterns
    ├── agents/             ← Standalone runners (cursor, ollama, rhoai)
    ├── output/cpat/        ← Golden baseline output (167 files)
    └── tools/              ← Dashboard, pipeline defaults
""", font_size=7)

    doc.add_heading("8.2 Key Source Files", level=2)

    add_table(doc, ["File", "Lines", "Purpose"], [
        ["sprintweave-web/api/worker.py", "4,035", "Core pipeline engine — all stage execution, validators, tool loop"],
        ["sprintweave-web/api/cpat_deploy.py", "972", "OpenShift deploy — binary build, manifests, sanitizers"],
        ["sprintweave-web/api/custom_agents.py", "437", "Custom agent CRUD + pipeline generation"],
        ["sprintweave-web/llm/client.py", "~300", "OpenAI-compatible LLM client with streaming"],
        ["sprintweave-web/ui/app.py", "~500", "Streamlit UI — Home, Run, Job, Agents pages"],
        ["cpat-main/context/pipelines.yaml", "311", "All pipeline stage definitions (data-driven)"],
        ["cpat-main/.cursor/rules/agent-rhoso-de.md", "441", "RHOSO DE agent rule with reference patterns"],
        ["cpat-main/.cursor/rules/agent-rhoso-da.md", "~350", "RHOSO DA agent rule"],
    ])

    doc.add_heading("8.3 Configuration Reference (ConfigMap)", level=2)

    add_table(doc, ["Setting", "Default", "Purpose"], [
        ["LLM_MODEL", "claude-opus-4-6", "LLM model for code generation"],
        ["LLM_MAX_TOKENS", "32768", "Max output tokens per LLM call"],
        ["LLM_TIMEOUT", "600", "LLM call timeout (seconds)"],
        ["SPRINTWEAVE_AGENT_MAX_STEPS", "80", "Max tool-loop steps per sub-stage"],
        ["SPRINTWEAVE_ANSIBLE_ROUND_STEPS", "30", "Steps per Ansible round"],
        ["SPRINTWEAVE_ANSIBLE_MAX_ROUNDS", "15", "Max Ansible until-complete rounds"],
        ["SPRINTWEAVE_VALIDATE_FIX_ROUNDS", "3", "Max validate→fix iterations"],
        ["SPRINTWEAVE_AGENT_PROMPT_MAX", "16000", "Max agent rule size in prompt"],
        ["SPRINTWEAVE_TEXT_MAX", "80000", "Max input document text"],
        ["SPRINTWEAVE_TOOL_RESULT_MAX", "60000", "Max tool result context"],
        ["SPRINTWEAVE_USE_LANGGRAPH", "true", "Enable LangGraph runtime"],
        ["SPRINTWEAVE_LANGGRAPH_SCOPE", "ansible,custom,rde", "Which stages use LangGraph"],
        ["SPRINTWEAVE_CPAT_DEPLOY_MODE", "openshift", "Deploy mode: openshift/bringup/manifests"],
        ["SPRINTWEAVE_PIPELINES", "rhoso,ocp", "Visible pipelines in UI"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 9. QUALITY & COST
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("9. Quality & Cost", level=1)

    doc.add_heading("9.1 Quality Improvements (v3 vs Previous)", level=2)

    add_table(doc, ["Improvement", "Before", "Now", "Impact"], [
        ["Validate→Fix loop", "No validation", "3 self-correction rounds", "Catches broken imports, truncated files, bad Dockerfiles"],
        ["Reference patterns", "LLM guessed patterns", "Patterns in agent rules", "OpenShift-safe code from first generation"],
        ["Token limits", "2K output", "32K output", "No truncated functions or missing code"],
        ["Agent steps", "60 max", "80 max", "Complex Ansible stages complete fully"],
        ["Data-driven validators", "Generic checks", "Per-stage validators from YAML", "Right checks for each stage type"],
        ["Context window", "40K tool results", "60K tool results", "LLM sees more file context for cross-module consistency"],
    ])

    doc.add_heading("9.2 Cost Estimates", level=2)

    add_table(doc, ["Scenario", "Estimated Cost", "Notes"], [
        ["Previous pipeline (no validation)", "~$11", "Broken code, needs manual fixing"],
        ["New pipeline — best case (clean generation)", "$14–16", "Few fix rounds needed"],
        ["New pipeline — typical", "$17–20", "Some stages need 1–2 fix rounds"],
        ["New pipeline — worst case", "$22–25", "All stages need all 3 fix rounds"],
    ])

    doc.add_paragraph(
        "ROI: $6–9 more per run saves hours of manual debugging. "
        "The generated code builds on OpenShift on the first try."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 10. TROUBLESHOOTING
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("10. Troubleshooting", level=1)

    add_table(doc, ["Problem", "Cause", "Fix"], [
        ["API pod OOMKilled", "Docling model load exceeds memory", "Increase limit to ≥12Gi"],
        ["API pod CrashLoopBackOff", "Missing LLM_API_KEY secret", "oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY=..."],
        ["Route shows 503", "API readiness probe takes ~30s on boot", "Wait and refresh. Check oc logs."],
        ["Image pull fails", "Private Quay without pull secret", "oc secrets link default quay-pull --for=pull"],
        ["RDA generator exit=1", "LLM wrote list/dict as Excel cell value", "Approve gate — doesn't affect RDE stages"],
        ["Ansible hits max_steps", "Complex template set needs more steps", "Increase SPRINTWEAVE_AGENT_MAX_STEPS"],
        ["Backend import errors", "Cross-module symbol mismatch", "Validate→fix loop handles this automatically"],
        ["Dockerfile EXPOSE 80", "LLM defaulted to nginx port 80", "Validator catches this; reference patterns prevent it"],
        ["Entrypoint chmod crash", "Fatal chmod on emptyDir mount under set -e", "entrypoint_sh validator catches this"],
        ["MaaS key expired", "7-day rotation on RHDP keys", "Rotate secret + restart API"],
    ])

    # ── Footer ─────────────────────────────────────────────────
    doc.add_paragraph()
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("— End of Document —")
    r.italic = True
    r.font.color.rgb = GRAY

    # ── Save ───────────────────────────────────────────────────
    doc.save(OUT)
    print(f"Generated: {OUT}")
    print(f"Size: {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
