"""Generate TEAM-GUIDE.docx from the team briefing content."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

OUT = Path(__file__).with_name("SprintWeave-OpenShift-Team-Guide.docx")
BLUE = RGBColor(0x2B, 0x57, 0x9A)


def shade_header(cell, hex_color="2B579A"):
    tc = cell._tePr if False else cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.size = Pt(10)
        shade_header(cell)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = val
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    doc.add_paragraph()


def code_block(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(8)
    p.paragraph_format.space_after = Pt(8)


def main():
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("SprintWeave on OpenShift")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = BLUE

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run("Architecture, operations, and roadmap for the team")
    r.font.size = Pt(14)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(
        "Audience: delivery and platform team  ·  App: sprintweave-web  ·  Agents (Cursor): sprintweave-agents"
    ).italic = True

    note = doc.add_paragraph()
    nr = note.add_run(
        "Do not put API keys in Git, ConfigMaps, Streamlit, or this document."
    )
    nr.bold = True

    doc.add_heading("1. What we replaced (and what we did not)", level=1)
    add_table(
        doc,
        ["Cursor today", "OpenShift app"],
        [
            ["Chat + Canvas dashboard", "Streamlit (Home / Run / Job / Outputs)"],
            ["@input/ folder", "Upload → PVC /data/jobs/<id>/input/"],
            ["Orchestrator sequencing agents", "Python worker loops stages"],
            ["Agent .md rules as system behaviour", "Not wired yet — generic prompts/system.md"],
            ["Claude inside Cursor", "LiteLLM on MaaS (OpenAI-compatible HTTP) from the API pod"],
        ],
    )
    doc.add_paragraph(
        "Cursor remains the place to edit agent prompts. The cluster runs jobs for the team via a Route. "
        "We do not run Cursor or .cursor/ as a pod."
    )

    doc.add_heading("2. Current architecture", level=1)
    code_block(
        doc,
        """Browser
   | HTTPS (OpenShift Route, TLS edge)
   v
sprintweave-ui  (Streamlit :8080)     — no LLM key
   | HTTP  SPRINTWEAVE_API_URL=http://sprintweave-api:8000
   v
sprintweave-api (FastAPI + worker :8000)
   | Secret LLM_API_KEY  ·  ConfigMap LLM_*  ·  PVC /data
   +--> POST LiteLLM  {LLM_BASE_URL}/chat/completions
   +--> /data/jobs/<job-id>/input/     uploaded files
   +--> /data/jobs/<job-id>/output/    generated markdown""",
    )
    doc.add_paragraph(
        "One container image (ImageStream sprintweave-ui) is used twice: Streamlit on 8080 and uvicorn api.main:app on 8000. "
        "Two pods so the UI never holds the key and only the API mounts the RWO PVC. Streamlit posts multipart files to the API."
    )

    doc.add_heading("OpenShift objects (project sprintweave)", level=2)
    add_table(
        doc,
        ["Object", "Name", "Role"],
        [
            ["ImageStream + BuildConfig", "sprintweave-ui", "Binary Docker build from sprintweave-web/"],
            ["DeploymentConfig", "sprintweave-ui", "Streamlit"],
            ["DeploymentConfig", "sprintweave-api", "Worker + FastAPI"],
            ["Service", "ui :8080, api :8000", "In-cluster"],
            ["Route", "sprintweave-ui", "Public HTTPS"],
            ["PVC", "sprintweave-data", "/data on API pod"],
            ["ConfigMap", "sprintweave-config", "Non-secret LLM settings"],
            ["Secret", "sprintweave-llm", "LLM_API_KEY only"],
        ],
    )

    doc.add_heading("LLM wiring (current workshop)", level=2)
    doc.add_paragraph(
        "MaaS is OpenAI-compatible LiteLLM, not Anthropic’s native Messages API. "
        "Keep LLM_PROVIDER=openai even when the model is claude-opus-4-6."
    )
    add_table(
        doc,
        ["Env", "Typical value"],
        [
            ["LLM_PROVIDER", "openai"],
            ["LLM_BASE_URL", "https://maas-rhdp.apps.maas.redhatworkshops.io/v1"],
            ["LLM_MODEL", "claude-opus-4-6 (or another MaaS model id)"],
            ["LLM_API_KEY", "Bearer token (sk-…) in Secret"],
        ],
    )
    doc.add_paragraph(
        "LLM_PROVIDER=anthropic exists in llm/client.py for a future direct api.anthropic.com path. "
        "Do not use it for MaaS /v1/chat/completions with Authorization: Bearer."
    )

    doc.add_heading("Request path for one Run", level=2)
    for item in [
        "User picks a pipeline (e.g. Lab Requirements) and uploads files.",
        "Streamlit POST /v1/jobs (pipeline_id, instructions, files).",
        "API creates /data/jobs/<id>/input/, saves bytes, starts a background thread.",
        "Worker, for each stage: user message (sources + instructions + previous output) and complete() with prompts/system.md.",
        "Writes /data/jobs/<id>/output/<abbrev>.md and summary.md.",
        "UI polls GET /v1/jobs/<id> every ~2 seconds.",
    ]:
        doc.add_paragraph(item, style="List Number")
    doc.add_paragraph(
        "Text files (.md, .txt) are decoded and truncated (SPRINTWEAVE_TEXT_MAX, default 20,000 characters). "
        "PDF/DOCX are stored on disk but largely treated as binary until Docling is added."
    )

    doc.add_heading("Token behaviour (today)", level=2)
    for item in [
        "Idle UI: 0 tokens.",
        "One Lab Requirements job = 1 LLM call.",
        "Standard = 4 calls; RHOSO/NRHO = 5.",
        "Smoke file samples/lab-smoke.txt ≈ 1k–2.5k tokens per run.",
        "Large PDFs and full agent rule files increase this a lot.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("3. Repository layout (sprintweave-web/)", level=1)
    code_block(
        doc,
        """Dockerfile                 UBI Python 3.12, Streamlit + FastAPI
requirements.txt
ui/app.py                  Streamlit pages
ui/pipelines.py            Pipeline catalog (stage names)
ui/job_client.py           Fake jobs OR HTTP API
api/main.py                FastAPI
api/worker.py              Stage loop + file I/O
llm/client.py              openai vs anthropic HTTP
prompts/system.md          Generic system prompt (current)
samples/lab-smoke.txt      Cheap upload for tests
deploy/openshift/          sprintweave-ui.yaml, sprintweave-api.yaml
docs/                      This guide (Markdown + Word)""",
    )

    doc.add_heading("4. How it works for a user", level=1)
    for item in [
        "Open the Route (oc get route sprintweave-ui).",
        "Sidebar must show Backend: API and API reachable.",
        "Home → Lab Requirements (1 stage) for tests; avoid Full/RHOSO until agents and cost are agreed.",
        "Run → upload .txt/.md → Run pipeline.",
        "Job page shows status, logs, On disk path.",
        "On success, download markdown; files remain on the PVC.",
    ]:
        doc.add_paragraph(item, style="List Number")
    doc.add_paragraph("Browse files from the bastion:")
    code_block(doc, "oc rsh dc/sprintweave-api\nls -R /data/jobs")

    doc.add_heading("5. Operations runbook (bastion)", level=1)
    doc.add_heading("5.1 Build directory", level=2)
    doc.add_paragraph(
        "Always cd to the folder that contains Dockerfile (not deploy/openshift)."
    )
    code_block(
        doc,
        "oc project sprintweave\noc start-build sprintweave-ui --from-dir=. --follow",
    )
    doc.add_paragraph(
        "oc new-build --name=sprintweave-ui fails if the BuildConfig already exists — that is expected. Reuse start-build."
    )

    doc.add_heading("5.2 Apply manifests", level=2)
    code_block(
        doc,
        "oc apply -f deploy/openshift/sprintweave-api.yaml\n"
        "oc apply -f deploy/openshift/sprintweave-ui.yaml",
    )
    doc.add_paragraph(
        "If oc rollout latest says already in progress, wait. Do not stack rollouts."
    )
    code_block(
        doc,
        "oc get pods\noc get dc sprintweave-api\noc get pvc\noc get route sprintweave-ui",
    )
    doc.add_paragraph(
        "Healthy: sprintweave-api-*-xxxxx and sprintweave-ui-*-xxxxx 1/1 Running, PVC Bound."
    )

    doc.add_heading("5.3 LLM Secret and ConfigMap", level=2)
    code_block(
        doc,
        "oc create secret generic sprintweave-llm \\\n"
        "  --from-literal=LLM_API_KEY='YOUR_KEY' \\\n"
        "  -n sprintweave",
    )
    code_block(
        doc,
        "oc patch configmap sprintweave-config -n sprintweave --type merge -p '{\n"
        '  "data": {\n'
        '    "LLM_PROVIDER": "openai",\n'
        '    "LLM_BASE_URL": "https://maas-rhdp.apps.maas.redhatworkshops.io/v1",\n'
        '    "LLM_MODEL": "claude-opus-4-6",\n'
        '    "LLM_MAX_TOKENS": "1024",\n'
        '    "LLM_TIMEOUT": "180"\n'
        "  }\n"
        "}'\n"
        "oc rollout latest dc/sprintweave-api",
    )
    doc.add_paragraph(
        "After changing the Secret or ConfigMap, wait for a new API pod."
    )

    doc.add_heading("5.4 Known platform issue (SCC)", level=2)
    doc.add_paragraph(
        "Do not set securityContext.fsGroup: 0 on the API pod. Restricted SCC rejects group 0; "
        "the API replica stays at CURRENT 0 (FailedCreate). Omit pod-level fsGroup, or use the "
        "project’s allocated supplemental GID (oc get project sprintweave -o yaml → sa.scc.supplemental-groups)."
    )

    doc.add_heading("5.5 Typical failures", level=2)
    add_table(
        doc,
        ["Symptom", "Cause"],
        [
            ["Job failed 401 Unauthorized … maas-rhdp…", "Wrong/expired MaaS key, or native Anthropic key used against LiteLLM"],
            ["Sidebar fake jobs", "SPRINTWEAVE_API_URL empty; re-apply UI YAML"],
            ["Build Dockerfile: no such file", "--from-dir was deploy/openshift"],
            ["API never schedules", "fsGroup: 0 (see 5.4)"],
            ["PVC Pending", "Normal until the first API pod mounts it"],
        ],
    )

    doc.add_heading("6. Further enhancement — remaining agents", level=1)
    doc.add_paragraph(
        "Goal: each pipeline stage uses the real Cursor agent rule as the LLM system prompt. No new OpenShift service."
    )
    doc.add_heading("6.1 Mapping", level=2)
    code_block(
        doc,
        "ui/pipelines.py  stage.agent\n"
        "        →  lookup\n"
        "prompts/agents/agent-*.md     (copy from sprintweave-agents/.cursor/rules/)\n"
        "        →  system\n"
        "LiteLLM chat/completions\n"
        "        →  /data/jobs/<id>/output/<abbrev>.md",
    )
    add_table(
        doc,
        ["stage.agent", "Suggested file"],
        [
            ["Requirements Analyst", "agent-requirements-analyst.md"],
            ["Solution Architect", "agent-solution-architect.md"],
            ["Technical Lead", "agent-technical-lead.md"],
            ["QA Architect", "agent-qa-architect.md"],
            ["DevOps Engineer", "agent-devops-engineer.md"],
            ["Cloud Deployment Engineer", "agent-cloud-deployment-engineer.md"],
            ["Automation Engineer", "agent-automation-engineer.md"],
            ["SRE Engineer", "agent-sre-engineer.md"],
            ["Technical Writer", "agent-technical-writer.md"],
            ["Governance Specialist", "agent-governance-specialist.md"],
            ["Project Manager", "agent-project-manager.md"],
            ["Sprint Coach", "agent-sprint-coach.md"],
            ["Proposal Writer", "agent-proposal-writer.md"],
            ["RHOSO DA", "agent-rhoso-da.md"],
            ["RHOSO Deployment Engineer", "agent-rhoso-deployment-engineer.md"],
            ["NRHO DA", "agent-nrho-da.md"],
            ["NRHO Deployment Engineer", "agent-nrho-deployment-engineer.md"],
        ],
    )
    doc.add_paragraph(
        "Missing mapping → fall back to prompts/system.md or fail the stage (team choice). "
        "One stage = one file = one LLM call. Do not concatenate all agents into one prompt. "
        "agent-orchestrator.md is not an LLM agent; Python already sequences stages."
    )

    doc.add_heading("6.2 Implementation outline (when you build it)", level=2)
    for item in [
        "Copy selected agent-*.md into sprintweave-web/prompts/agents/.",
        "In api/worker.py, resolve stage[\"agent\"] → file; use as system. Optionally append context/templates.",
        "Rebuild (oc start-build), roll API.",
        "Prove Lab Requirements first (RHOSO DA only), then Standard, then RHOSO/NRHO.",
        "Later: load sprintweave-agents/context/pipelines.yaml instead of duplicating pipelines.py.",
        "Later: Excel via sprintweave-agents/tools/excel-generator.py after markdown exists.",
    ]:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("6.3 Token warning", level=2)
    doc.add_paragraph(
        "Full agent markdown files are large system prompts. Add them only after a cheap smoke test works. "
        "Keep LLM_MAX_TOKENS and SPRINTWEAVE_TEXT_MAX as guards."
    )

    doc.add_heading("7. Further enhancement — Docling", level=1)
    doc.add_paragraph(
        "Goal: turn PDF/DOCX/PPTX into Markdown before the LLM so agents see real content."
    )
    code_block(
        doc,
        "/data/jobs/<id>/input/file.pdf\n"
        "        →  Docling on the API/worker\n"
        "        →  /data/jobs/<id>/parsed/file.md\n"
        "        →  existing stage loop (read parsed/ first)",
    )
    for item in [
        "Run Docling only on the API pod (or a future parse Deployment), never in Streamlit.",
        "Skip Docling for .txt/.md.",
        "Dependencies are heavy (often torch); image size, RAM, and job time go up. Single-node workshops may OOM — raise API memory or use pypdf first.",
        "Parsed Markdown can increase tokens; keep truncation.",
        "Alternative: separate sprintweave-parse Deployment sharing the PVC if the UI/API image must stay small.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("8. Suggested delivery sequence", level=1)
    add_table(
        doc,
        ["Phase", "Outcome"],
        [
            ["Now (done)", "Route + API + PVC; Lab Requirements; LiteLLM; generic prompt"],
            ["Next", "Map RHOSO DA → agent-rhoso-da.md; rebuild; smoke job"],
            ["Then", "Remaining agents used by Standard / RHOSO / NRHO"],
            ["Then", "Docling for PDF/DOCX"],
            ["Then", "YAML pipelines + Excel tools + optional OAuth on the Route"],
        ],
    )

    doc.add_heading("9. Security and hygiene", level=1)
    for item in [
        "Keys only in Secret sprintweave-llm. Rotate if a key was pasted in chat, tickets, or screenshots.",
        "MaaS keys may expire (workshop often 7 days).",
        "Do not log full document text or the Bearer token.",
        "UI replica: 1 until job state is only in the API (not Streamlit session).",
        "DeploymentConfig is deprecated in OCP 4.14+; a later enhancement can move to Deployment.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("10. Quick reference", level=1)
    code_block(
        doc,
        "# URL\n"
        "oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{\"\\n\"}'\n\n"
        "# Logs\n"
        "oc logs -f dc/sprintweave-api\n"
        "oc logs -f dc/sprintweave-ui\n\n"
        "# Rebuild after code/prompt changes\n"
        "cd /path/to/sprintweave-web\n"
        "oc start-build sprintweave-ui --from-dir=. --follow",
    )
    doc.add_paragraph("Smoke upload: sprintweave-web/samples/lab-smoke.txt")

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
