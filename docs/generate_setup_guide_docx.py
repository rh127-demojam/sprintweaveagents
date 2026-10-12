"""Generate NEW-CLUSTER-SETUP.docx from the setup guide content."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

OUT = Path(__file__).with_name("SprintWeave-New-Cluster-Setup.docx")
BLUE = RGBColor(0x2B, 0x57, 0x9A)
GREEN = RGBColor(0x22, 0x7D, 0x51)


def shade_header(cell, hex_color="2B579A"):
    tcPr = cell._tc.get_or_add_tcPr()
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
                r.font.size = Pt(9)
        shade_header(cell)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = val
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()


def code(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(8)
    p.paragraph_format.space_after = Pt(6)


def note(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)


def main():
    doc = Document()
    s = doc.sections[0]
    s.left_margin = Inches(0.9)
    s.right_margin = Inches(0.9)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("SprintWeave\nNew Cluster Setup Guide")
    r.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = BLUE

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("For platform engineers deploying SprintWeave on a fresh OpenShift cluster").italic = True

    doc.add_paragraph().add_run("Do not put API keys in Git, YAML files, ConfigMaps, or this document.").bold = True

    # Prerequisites
    doc.add_heading("Prerequisites", level=1)
    add_table(doc, ["Requirement", "Details"], [
        ["OpenShift cluster", "4.14+ (tested on 4.22)"],
        ["oc CLI", "Logged in with project-create permissions"],
        ["Quay image", "quay.io/rh_global_services_auto/sprintweave:latest (public)"],
        ["LLM endpoint", "OpenAI-compatible /v1/chat/completions with Bearer key"],
        ["LLM API key", "Bearer token for the endpoint"],
        ["Bastion or terminal", "SSH access or oc from laptop"],
    ])

    # Architecture
    doc.add_heading("Architecture", level=1)
    code(doc, """Browser
   | HTTPS (Route, TLS edge)
   v
sprintweave-ui  (Streamlit :8080)  -- no LLM key
   | HTTP
   v
sprintweave-api (FastAPI :8000)    -- Secret + PVC
   |
   +--> LLM endpoint (/v1/chat/completions)
   +--> /data/jobs/<id>/input/   (uploads)
   +--> /data/jobs/<id>/output/  (artifacts)""")

    doc.add_paragraph("One image, two Deployments. UI never holds the key. Only API mounts the PVC.")

    add_table(doc, ["Object", "Name", "Role"], [
        ["Deployment", "sprintweave-ui", "Streamlit UI"],
        ["Deployment", "sprintweave-api", "FastAPI + worker"],
        ["Service", "sprintweave-ui :8080, sprintweave-api :8000", "In-cluster"],
        ["Route", "sprintweave-ui", "Public HTTPS"],
        ["PVC", "sprintweave-data (2Gi)", "Uploads + outputs"],
        ["ConfigMap", "sprintweave-config", "LLM settings (non-secret)"],
        ["Secret", "sprintweave-llm", "LLM_API_KEY only"],
    ])

    # Steps
    doc.add_heading("Setup Steps", level=1)

    doc.add_heading("Step 1 — Login and create project", level=2)
    code(doc, "oc login https://api.<cluster>:6443\noc new-project sprintweave\noc project sprintweave")

    doc.add_heading("Step 2 — Test LLM egress", level=2)
    code(doc, 'oc run curl-test --image=registry.access.redhat.com/ubi9/ubi-minimal \\\n  --rm -it --restart=Never -- \\\n  curl -sS -o /dev/null -w "%{http_code}\\n" <LLM_BASE_URL>/models')
    doc.add_paragraph("200 or 401 = network works. Timeout = fix egress first. Do not pass the key.")

    doc.add_heading("Step 3 — Create LLM Secret", level=2)
    code(doc, "oc create secret generic sprintweave-llm \\\n  --from-literal=LLM_API_KEY='<your-key>' \\\n  -n sprintweave")
    code(doc, "oc get secret sprintweave-llm\noc describe secret sprintweave-llm")

    doc.add_heading("Step 4 — (Private Quay only) Pull secret", level=2)
    doc.add_paragraph("Skip if the Quay repo is public.")
    code(doc, "oc create secret docker-registry quay-pull \\\n  --docker-server=quay.io \\\n  --docker-username='<user>' --docker-password='<token>' \\\n  --docker-email='unused@example.com' -n sprintweave\n\noc secrets link default quay-pull --for=pull -n sprintweave")

    doc.add_heading("Step 5 — Edit quay-deploy.yaml", level=2)
    doc.add_paragraph("Replace YOUR_ORG in both API and UI image lines:")
    code(doc, "image: quay.io/rh_global_services_auto/sprintweave:latest")
    doc.add_paragraph("Review the ConfigMap section and set LLM values:")
    add_table(doc, ["Provider", "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL"], [
        ["MaaS/LiteLLM", "openai", "https://maas-rhdp.apps.…/v1", "claude-opus-4-6"],
        ["Azure OpenAI", "openai", "https://<resource>.openai.azure.com/…", "gpt-4"],
        ["Anthropic direct", "anthropic", "https://api.anthropic.com", "claude-opus-4-6"],
        ["Ollama (in-cluster)", "openai", "http://ollama:11434/v1", "llama3"],
    ])

    doc.add_heading("Step 6 — Apply", level=2)
    code(doc, "oc apply -f quay-deploy.yaml")

    doc.add_heading("Step 7 — Wait for pods", level=2)
    code(doc, "oc get pods -w")
    doc.add_paragraph("Wait for both sprintweave-api and sprintweave-ui to show 1/1 Running.")
    add_table(doc, ["Pod status", "Check", "Common cause"], [
        ["ImagePullBackOff", "oc describe pod -l app=sprintweave-api", "Wrong image name or private Quay without pull secret"],
        ["CrashLoopBackOff", "oc logs deploy/sprintweave-api --tail=30", "Missing Secret or Python error"],
        ["Pending", "oc describe pod", "PVC cannot bind or insufficient resources"],
    ])

    doc.add_heading("Step 8 — Get the URL", level=2)
    code(doc, "oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{\"\\n\"}'")

    doc.add_heading("Step 9 — Verify in the browser", level=2)
    for item in [
        "Sidebar shows 'API connected' (not 'Demo mode').",
        "Home > Lab Requirements (1 stage, cheapest test).",
        "Upload lab-smoke.txt (small text file).",
        "Click 'Run pipeline'.",
        "Job page: stage goes from clock to checkmark.",
        "Download the markdown artifact on success.",
    ]:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("Step 10 — Verify files on disk", level=2)
    code(doc, "oc rsh deploy/sprintweave-api\nls -R /data/jobs\nexit")

    doc.add_heading("Step 11 — Verify agents are bundled", level=2)
    code(doc, "oc rsh deploy/sprintweave-api\nls /app/sprintweave-agents/.cursor/rules/ | head\nls /app/sprintweave-agents/context/templates/ | head\nexit")

    # Operations
    doc.add_heading("Post-Setup Operations", level=1)

    doc.add_heading("Update LLM model or endpoint", level=2)
    code(doc, "oc patch configmap sprintweave-config --type merge -p '{\n  \"data\": { \"LLM_MODEL\": \"new-model\" }\n}'\noc rollout restart deployment/sprintweave-api")

    doc.add_heading("Rotate LLM key", level=2)
    code(doc, "oc delete secret sprintweave-llm\noc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='<new>'\noc rollout restart deployment/sprintweave-api")

    doc.add_heading("Update image (after new build + push)", level=2)
    code(doc, "oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui")

    doc.add_heading("View logs", level=2)
    code(doc, "oc logs -f deploy/sprintweave-api\noc logs -f deploy/sprintweave-ui")

    # Known issues
    doc.add_heading("Known Issues", level=1)
    add_table(doc, ["Issue", "Workaround"], [
        ["fsGroup: 0 rejected by SCC", "Do not set pod-level fsGroup: 0. Omit it."],
        ["PVC is RWO", "Keep API replicas at 1."],
        ["MaaS keys expire (7 days)", "Rotate Secret and restart API."],
        ["PDF/DOCX seen as binary", "Docling not installed. Use .txt/.md for now."],
        ["Large agent rules increase tokens", "SPRINTWEAVE_AGENT_PROMPT_MAX truncates (default 24000)."],
    ])

    # Quick ref
    doc.add_heading("Quick Reference Card", level=1)
    code(doc, """# Login
oc login https://api.<cluster>:6443

# Create project
oc new-project sprintweave

# Create secret
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='...'

# Deploy
oc apply -f quay-deploy.yaml

# Check
oc get pods
oc get route sprintweave-ui

# Logs
oc logs -f deploy/sprintweave-api

# Files
oc rsh deploy/sprintweave-api -- ls -R /data/jobs

# Rotate key
oc delete secret sprintweave-llm
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='...'
oc rollout restart deployment/sprintweave-api

# Update image
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui""")

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
