"""Generate SprintWeave User Guide (.docx) — step-by-step usage guide for
end users: how to access, upload inputs, run pipelines, review outputs,
approve gates, deploy CPAT, and manage custom agents.

Run:  py -3 generate_user_guide.py
Requires: pip install python-docx
"""

from pathlib import Path
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor, Cm

OUT = Path(__file__).with_name("SprintWeave_User_Guide.docx")
BLUE = RGBColor(0x2B, 0x57, 0x9A)
GRAY = RGBColor(0x66, 0x66, 0x66)
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
    r = t.add_run("SprintWeave\nUser Guide")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = BLUE

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("Running RHOSO & OCP Delivery Pipelines on OpenShift")
    r2.font.size = Pt(16)
    r2.font.color.rgb = GRAY

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Version 3.0 — {datetime.now().strftime('%B %Y')}").font.size = Pt(11)

    meta2 = doc.add_paragraph()
    meta2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = meta2.add_run("For delivery engineers, architects, and team leads")
    r3.italic = True
    r3.font.size = Pt(11)

    doc.add_page_break()

    # ── Table of Contents ──────────────────────────────────────
    doc.add_heading("Table of Contents", level=1)
    toc = [
        "1. Getting Started",
        "   1.1 Accessing SprintWeave",
        "   1.2 Home Page Overview",
        "   1.3 Navigation",
        "2. Managing Inputs",
        "   2.1 Creating an Input Set",
        "   2.2 Supported File Formats",
        "   2.3 Reusing Input Sets",
        "3. Running a Pipeline",
        "   3.1 Selecting a Pipeline",
        "   3.2 Configuring the Run",
        "   3.3 Monitoring Progress",
        "   3.4 Understanding the Logs",
        "4. Pipeline Stages — What Happens",
        "   4.1 Docling (Document Parsing)",
        "   4.2 RDA — Design Authority",
        "   4.3 RDE — Deployment Engineer",
        "   4.4 Stage Validation",
        "5. Approval Gates",
        "   5.1 What Gates Are",
        "   5.2 Reviewing Artifacts at a Gate",
        "   5.3 Approving, Rejecting, or Skipping",
        "6. Downloading Outputs",
        "   6.1 Output Artifacts Overview",
        "   6.2 Downloading as ZIP",
        "   6.3 Browsing Individual Files",
        "7. Deploying CPAT to OpenShift",
        "   7.1 One-Click Deploy",
        "   7.2 Deploy Modes",
        "   7.3 Checking Deploy Status",
        "8. Custom Agents",
        "   8.1 Creating a Custom Agent",
        "   8.2 Editing Agent Rules",
        "   8.3 Running Custom Pipelines",
        "9. Available Pipelines Reference",
        "10. Troubleshooting",
    ]
    for item in toc:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(2)
        for r in p.runs:
            r.font.size = Pt(10)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 1. GETTING STARTED
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("1. Getting Started", level=1)

    doc.add_heading("1.1 Accessing SprintWeave", level=2)
    doc.add_paragraph(
        "SprintWeave runs on OpenShift and is accessed through a web browser. "
        "Your platform team will provide the URL (OpenShift Route)."
    )
    bold_para(doc, "Get the URL:")
    code(doc, "oc get route sprintweave-ui -n sprintweave -o jsonpath='https://{.spec.host}'")
    doc.add_paragraph(
        "Open the URL in Chrome, Firefox, or Edge. No login is required for the "
        "SprintWeave UI itself — authentication is handled at the OpenShift Route level."
    )

    doc.add_heading("1.2 Home Page Overview", level=2)
    doc.add_paragraph("The home page shows:")
    bullet(doc, "Available pipelines (RHOSO Delivery, OCP Delivery, etc.)")
    bullet(doc, "Recent jobs with status (running, completed, failed)")
    bullet(doc, "Quick actions: Run Pipeline, Manage Inputs, Agents")
    bullet(doc, "API connection status (should show 'Connected')")

    doc.add_heading("1.3 Navigation", level=2)
    add_table(doc, ["Page", "What It Does"], [
        ["Home", "Pipeline list + recent jobs"],
        ["Run", "Start a new pipeline run"],
        ["Jobs", "View all jobs with status, logs, outputs"],
        ["Inputs", "Manage reusable input sets (upload/delete documents)"],
        ["Agents", "View and create custom agents (no image rebuild)"],
        ["Deploy", "CPAT deploy status and controls"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 2. MANAGING INPUTS
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("2. Managing Inputs", level=1)

    doc.add_heading("2.1 Creating an Input Set", level=2)
    doc.add_paragraph(
        "An input set is a named collection of documents that a pipeline processes. "
        "You can reuse the same input set across multiple runs."
    )
    numbered(doc, "Go to Inputs page")
    numbered(doc, "Click 'New Input Set'")
    numbered(doc, "Enter a name (e.g., 'rhoso-customer-acme')")
    numbered(doc, "Upload files — drag and drop or click 'Choose Files'")
    numbered(doc, "Click 'Create'")

    doc.add_heading("2.2 Supported File Formats", level=2)
    add_table(doc, ["Format", "Processing", "Notes"], [
        ["PDF", "Docling extracts text + tables → .md", "Best for Red Hat documentation PDFs"],
        ["DOCX", "Docling extracts text + tables → .md", "Customer architecture documents"],
        ["Excel (.xlsx)", "Read directly by agents", "CIQ workbooks, parameter sheets"],
        ["Text (.txt)", "Passed directly to agents", "Notes, requirements"],
        ["Markdown (.md)", "Passed directly to agents", "Pre-parsed content"],
    ])

    doc.add_heading("2.3 Reusing Input Sets", level=2)
    doc.add_paragraph(
        "Input sets persist on the PVC. When starting a new run, select an existing "
        "input set instead of uploading files again. Docling caches parsed results — "
        "re-running the same PDFs is instant."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 3. RUNNING A PIPELINE
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("3. Running a Pipeline", level=1)

    doc.add_heading("3.1 Selecting a Pipeline", level=2)
    add_table(doc, ["Pipeline", "When to Use", "Input Documents"], [
        ["RHOSO Delivery", "Full RHOSO delivery (DA + DE)", "RHOSO 18.0 PDFs (7-8 docs)"],
        ["RHOSO DA Only", "Generate CIQ schema + workbooks only", "RHOSO PDFs"],
        ["RHOSO DE Only", "Generate code only (if CIQ already exists)", "Previous RDA output"],
        ["OCP Delivery", "Full OCP delivery (DA + DE)", "OCP documentation"],
        ["OCP DA Only", "Generate OCP CIQ schema + workbooks", "OCP docs"],
        ["OCP DE Only", "Generate OCP code only", "Previous ODA output"],
        ["Full Delivery", "RHOSO + OCP combined", "All documentation"],
    ])

    doc.add_heading("3.2 Configuring the Run", level=2)
    numbered(doc, "Click 'Run Pipeline' from the Home page")
    numbered(doc, "Select the pipeline from the dropdown")
    numbered(doc, "Select an existing input set OR upload new files")
    numbered(doc, "Optionally add a command (e.g., 'Run RHOSO delivery pipeline on @cpat')")
    numbered(doc, "Toggle 'Enable Gates' (recommended — lets you review before each major stage)")
    numbered(doc, "Click 'Start'")

    doc.add_heading("3.3 Monitoring Progress", level=2)
    doc.add_paragraph("After starting, you'll see the Job page with:")
    bullet(doc, "Stage progress — each stage shows a clock icon (running), checkmark (done), or X (failed)")
    bullet(doc, "Live log stream — real-time output from the worker")
    bullet(doc, "Elapsed time per stage")
    bullet(doc, "Stop button — cancels the job between stages (cannot cancel mid-LLM-call)")

    doc.add_heading("3.4 Understanding the Logs", level=2)
    add_table(doc, ["Log Prefix", "Meaning"], [
        ["[workspace]", "Workspace setup — seeding context, skills, linking inputs"],
        ["[docling]", "PDF/DOCX parsing progress"],
        ["[parsed]", "Individual file parsed successfully + time"],
        ["[rda-single-shot]", "RDA stage — CIQ schema and workbook generation"],
        ["[langgraph] step N/M", "LangGraph tool-loop — agent writing files iteratively"],
        ["[lg-tool] write_file(...)", "Agent wrote a file in the workspace"],
        ["[ansible-validate]", "Ansible validation results (PASS/FAIL per check)"],
        ["[rde-single-shot]", "RDE Backend/Frontend/Docker — single-shot generation"],
        ["[rde-pass]", "RDE sub-stage starting or completing"],
        ["[gate]", "Approval gate — waiting for human review"],
        ["[verify_paths]", "Output file verification (files exist + non-empty)"],
        ["[cpat-deploy]", "CPAT deploy to OpenShift progress"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 4. PIPELINE STAGES
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("4. Pipeline Stages — What Happens", level=1)

    doc.add_heading("4.1 Docling (Document Parsing)", level=2)
    doc.add_paragraph(
        "First, all uploaded PDF and DOCX files are parsed by Docling into Markdown. "
        "This extracts text, tables, and structure. Typical timing: 10–150 seconds per file "
        "depending on size. Results are cached by content hash — re-running the same files is instant."
    )

    doc.add_heading("4.2 RDA — Design Authority", level=2)
    doc.add_paragraph("The Design Authority agent reads parsed documents and generates:")
    bullet(doc, "CIQ Parameter Schema — Python data structure with all deployment parameters (200+ for RHOSO)")
    bullet(doc, "Workbook Generator — Python script that creates Excel CIQ workbooks")
    bullet(doc, "Excel Workbooks — Ready-to-fill .xlsx files for customer data collection")
    bullet(doc, "Pipeline Reports — Documentation of what was extracted")

    bold_para(doc, "Common RDA issues:")
    add_table(doc, ["Issue", "What It Means", "Action"], [
        ["generator exit=1", "Excel generator script had a runtime error", "Non-blocking. Approve gate and continue. CIQ schema is still valid."],
        ["Schema parameter count < 200", "Some parameters not extracted", "Check input PDFs — may be missing pages or wrong version"],
    ])

    doc.add_heading("4.3 RDE — Deployment Engineer", level=2)
    doc.add_paragraph("The Deployment Engineer runs 5 sub-stages:")

    add_table(doc, ["Sub-stage", "What It Generates", "Duration"], [
        ["RDE-1 Ansible", "Playbooks, roles, 19+ Jinja2 templates, module_utils, CIQ schema", "~12 min"],
        ["RDE-2 Backend", "Flask API (app.py, models, parsers, routes, schema shim)", "~3 min"],
        ["RDE-3 Frontend", "React UI (13 components, API client, styles, routing)", "~3 min"],
        ["RDE-4 Docker", "Dockerfile, entrypoint.sh, nginx config, bringup.sh", "~2 min"],
        ["RDE-5 AAP", "Ansible Automation Platform exports (EE, credentials, job templates)", "~2 min"],
    ])

    doc.add_heading("4.4 Stage Validation", level=2)
    doc.add_paragraph(
        "After each RDE sub-stage, validators automatically check the generated code. "
        "If errors are found, the LLM gets the error messages and self-corrects (up to 3 rounds). "
        "You'll see this in the logs as:"
    )
    code(doc, """[rde-single-shot] Backend wrote 10 file(s)
[rde-single-shot] Backend self-check 1
  python_syntax: PASS (10 files)
  python_imports: PASS (all symbols resolve)
[verify_paths] RDE-2 OK — 10 verified, 0 missing""")

    doc.add_paragraph(
        "If validation fails and self-correction can't fix it, the pipeline continues "
        "with best-effort output. You can review and manually fix in the downloaded artifacts."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 5. APPROVAL GATES
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("5. Approval Gates", level=1)

    doc.add_heading("5.1 What Gates Are", level=2)
    doc.add_paragraph(
        "Gates are pause points where the pipeline stops and waits for human review. "
        "They appear after major stages (RDA, full RDE) to let you inspect artifacts "
        "before the pipeline continues or deploys."
    )

    doc.add_heading("5.2 Reviewing Artifacts at a Gate", level=2)
    doc.add_paragraph("When a gate is active, the Job page shows:")
    bullet(doc, "List of generated files with sizes")
    bullet(doc, "Download link for individual files or full ZIP")
    bullet(doc, "Stage report with summary of what was generated")
    bullet(doc, "Approve / Reject / Skip buttons")

    bold_para(doc, "What to check at the RDA gate:")
    bullet(doc, "CIQ schema has correct parameter count (≥200 for RHOSO)")
    bullet(doc, "Workbook generator ran (exit=0 ideal, exit=1 is non-blocking)")
    bullet(doc, "Pipeline report lists all expected files")

    bold_para(doc, "What to check at the RDE gate:")
    bullet(doc, "Ansible: templates balanced, schema parses, task files present")
    bullet(doc, "Backend: all .py files parse, imports resolve")
    bullet(doc, "Frontend: all 13 components present, JSX balanced")
    bullet(doc, "Docker: Dockerfile has ENTRYPOINT/CMD, port 8080, OpenShift-safe")

    doc.add_heading("5.3 Approving, Rejecting, or Skipping", level=2)
    add_table(doc, ["Action", "What Happens"], [
        ["Approve", "Pipeline continues to the next stage"],
        ["Reject", "Pipeline stops. You can download what was generated."],
        ["Skip", "Pipeline continues but marks stage as skipped in the report"],
    ])

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 6. DOWNLOADING OUTPUTS
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("6. Downloading Outputs", level=1)

    doc.add_heading("6.1 Output Artifacts Overview", level=2)
    add_table(doc, ["Folder", "Contents"], [
        ["output/cpat/ansible/", "Ansible playbooks, roles, 19+ Jinja2 templates, module_utils"],
        ["output/cpat/backend/", "Flask API — app.py, models, parsers, CIQ schema, requirements.txt"],
        ["output/cpat/frontend/", "React UI — 13 components, API client, styles, nginx config"],
        ["output/cpat/docker/", "entrypoint.sh"],
        ["output/cpat/aap/", "AAP exports — EE definition, credential types, job templates"],
        ["output/cpat/Dockerfile", "OpenShift-safe multi-stage Dockerfile"],
        ["output/cpat/bringup.sh", "Container build & run lifecycle script"],
        ["output/ciq-generators/", "CIQ schema + workbook generator Python scripts"],
        ["output/ciq-workbooks/", "Generated Excel CIQ workbooks"],
        ["output/pipeline-reports/", "Stage reports (rda-report.md, rde-report.md)"],
    ])

    doc.add_heading("6.2 Downloading as ZIP", level=2)
    numbered(doc, "Go to the Job page for the completed run")
    numbered(doc, "Click 'Download ZIP' — downloads all output artifacts")
    numbered(doc, "Extract the ZIP — you'll have the complete CPAT project tree")

    doc.add_heading("6.3 Browsing Individual Files", level=2)
    doc.add_paragraph(
        "On the Job page, expand the output tree to browse individual files. "
        "Click any file to view its contents in the browser. "
        "You can also access files directly from the bastion:"
    )
    code(doc, """oc rsh deploy/sprintweave-api -- ls -R /data/jobs/<job-id>/output/cpat/
oc cp sprintweave-api-<pod>:/data/jobs/<job-id>/output/ ./local-output/""")

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 7. DEPLOYING CPAT
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("7. Deploying CPAT to OpenShift", level=1)

    doc.add_heading("7.1 One-Click Deploy", level=2)
    doc.add_paragraph(
        "After a successful RDE run, the 'Deploy CPAT' button appears on the Job page. "
        "This builds the generated code into a container and deploys it on the same "
        "OpenShift cluster with a Route."
    )
    numbered(doc, "Complete an RDE pipeline run (or approve the final gate)")
    numbered(doc, "Click 'Deploy CPAT' on the Job page")
    numbered(doc, "Select deploy mode (see below)")
    numbered(doc, "Wait for the binary build + rollout (3–5 minutes)")
    numbered(doc, "Click the Route URL to open the CPAT app")

    doc.add_heading("7.2 Deploy Modes", level=2)
    add_table(doc, ["Mode", "How It Works", "When to Use"], [
        ["OpenShift", "Binary BuildConfig → ImageStream → Deployment → Route", "On the cluster (recommended)"],
        ["Bringup", "Runs bringup.sh with podman/docker locally", "On bastion node with container runtime"],
        ["Manifests", "Writes YAML + deploy script only (no build)", "When you want to review manifests first"],
    ])

    doc.add_heading("7.3 Checking Deploy Status", level=2)
    doc.add_paragraph("The Deploy page shows:")
    bullet(doc, "Build status — building / pushing / deploying / running / failed")
    bullet(doc, "Route URL — click to open the deployed CPAT app")
    bullet(doc, "Build logs — real-time output from the OpenShift binary build")
    bullet(doc, "Manifest directory — where YAML files were written")

    bold_para(doc, "The deployed CPAT app (example URL):")
    code(doc, "https://cpat-<job-id>-sprintweave.apps.<cluster>.redhatworkshops.io")

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 8. CUSTOM AGENTS
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("8. Custom Agents", level=1)

    doc.add_heading("8.1 Creating a Custom Agent", level=2)
    doc.add_paragraph(
        "Custom agents let you create new pipelines without rebuilding the image. "
        "They're stored on the PVC and appear in the pipeline dropdown with a ✨ icon."
    )
    numbered(doc, "Go to the Agents page")
    numbered(doc, "Click 'New Agent'")
    numbered(doc, "Enter agent name and description")
    numbered(doc, "Paste the agent rule markdown (same format as .cursor/rules/*.md)")
    numbered(doc, "Select mode: tool_loop (iterative) or single_shot (one call)")
    numbered(doc, "Optionally add verify_paths (files the agent must produce)")
    numbered(doc, "Click 'Create'")

    doc.add_heading("8.2 Editing Agent Rules", level=2)
    doc.add_paragraph(
        "Click any custom agent on the Agents page to edit its rule markdown. "
        "Changes take effect immediately — no image rebuild needed."
    )

    doc.add_heading("8.3 Running Custom Pipelines", level=2)
    doc.add_paragraph(
        "Custom agents appear on the Home page as pipelines. Run them the same way: "
        "select inputs, click Start, monitor progress, approve gates."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 9. AVAILABLE PIPELINES REFERENCE
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("9. Available Pipelines Reference", level=1)

    add_table(doc, ["Pipeline", "Stages", "Input Docs", "Est. Time", "Est. Cost"], [
        ["RHOSO Delivery", "Docling → RDA (3) → Gate → RDE (5) → Gate → Deploy", "7-8 RHOSO PDFs", "~37 min", "$17-20"],
        ["RHOSO DA Only", "Docling → RDA (3) → Gate", "RHOSO PDFs", "~15 min", "$5-7"],
        ["RHOSO DE Only", "RDE (5) → Gate → Deploy", "Previous RDA output", "~22 min", "$12-15"],
        ["OCP Delivery", "Docling → ODA (3) → Gate → ODE (5) → Gate → Deploy", "OCP docs", "~35 min", "$17-20"],
        ["OCP DA Only", "Docling → ODA (3) → Gate", "OCP docs", "~15 min", "$5-7"],
        ["OCP DE Only", "ODE (5) → Gate → Deploy", "Previous ODA output", "~22 min", "$12-15"],
        ["Full Delivery", "RHOSO + OCP combined", "All docs", "~60 min", "$30-40"],
    ])

    doc.add_paragraph(
        "Cost estimates are based on Claude Opus via MaaS-RHDP. Actual cost depends on "
        "input document size, number of fix rounds, and LLM pricing."
    )

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════
    # 10. TROUBLESHOOTING
    # ══════════════════════════════════════════════════════════════
    doc.add_heading("10. Troubleshooting", level=1)

    add_table(doc, ["Problem", "What to Check", "Fix"], [
        ["UI shows 'Demo mode'", "API not connected", "Check API pod: oc logs deploy/sprintweave-api"],
        ["Docling fails on all files", "PDF/DOCX parsing error", "Check file format. Try .txt/.md instead."],
        ["RDA generator exit=1", "Excel generation error (list/dict as cell value)", "Non-blocking — approve gate, CIQ schema is valid"],
        ["Ansible hits max_steps=30", "Complex template set needs more steps", "Job still succeeds. Increase AGENT_MAX_STEPS for future runs."],
        ["Backend import errors", "Cross-module symbol mismatch", "Validate→fix loop handles automatically. Check self-check logs."],
        ["Frontend incomplete", "Missing React components", "Check agent rule has explicit component list. Rebuild + re-run."],
        ["CPAT deploy fails", "Binary build error", "Check RBAC: oc apply -f deploy/openshift/cpat-deploy-rbac.yaml"],
        ["CPAT UI shows EXPOSE 80", "LLM generated wrong port", "Validator catches this. If deployed, check nginx config."],
        ["Job stuck at gate", "Waiting for approval", "Click Approve on the Job page to continue"],
        ["MaaS key expired", "LLM calls fail with 401", "Rotate secret: oc delete/create secret sprintweave-llm"],
        ["API pod OOMKilled", "Not enough memory", "Increase limits to ≥12Gi in manifest"],
        ["Slow Docling", "First-run model download", "Subsequent runs use cache. Or pre-warm with a test job."],
    ])

    bold_para(doc, "Getting Help:")
    bullet(doc, "API logs: oc logs -f deploy/sprintweave-api -n sprintweave")
    bullet(doc, "UI logs: oc logs -f deploy/sprintweave-ui -n sprintweave")
    bullet(doc, "Pod status: oc get pods -n sprintweave")
    bullet(doc, "Job files: oc rsh deploy/sprintweave-api -- ls /data/jobs/")

    # ── Footer ─────────────────────────────────────────────────
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("— End of User Guide —")
    r.italic = True
    r.font.color.rgb = GRAY

    doc.save(OUT)
    print(f"Generated: {OUT}")
    print(f"Size: {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
