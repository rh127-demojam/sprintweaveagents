# SprintWeave Agents

**SprintWeave** is an OpenShift-hosted AI delivery platform that turns uploaded customer docs (PDF / DOCX / TXT) into Telco Cloud artifacts — **CIQ** (Customer Information Questionnaire) workbooks, **Ansible / AAP** (Ansible Automation Platform) content, backend/frontend/Docker trees — using multi-agent **LLM** (Large Language Model) pipelines (tool-loop / LangGraph) over **MaaS** (Model as a Service).

> **Do not** put API keys in Git, slides, ConfigMaps, or this file. Use the `sprintweave-llm` Secret only.

**Detailed docs**

| Document | Purpose |
|----------|---------|
| [`docs/PRESENTATION-E2E-ARCHITECTURE.md`](docs/PRESENTATION-E2E-ARCHITECTURE.md) | End-to-end architecture & operations deck |
| [`docs/SprintWeave_User_Guide.docx`](docs/SprintWeave_User_Guide.docx) | Step-by-step UI usage guide |
| [`docs/TEAM-GUIDE.md`](docs/TEAM-GUIDE.md) | OpenShift ops & roadmap |
| [`docs/NEW-CLUSTER-SETUP.md`](docs/NEW-CLUSTER-SETUP.md) | New cluster bring-up |

---

## Architecture

```text
 Browser (HTTPS Route, TLS edge)
    |
    v
 sprintweave-ui   Streamlit :8080
    |  env: SPRINTWEAVE_API_URL=http://sprintweave-api:8000
    |  NO LLM key
    v
 sprintweave-api  FastAPI + background worker :8000
    |  Secret: sprintweave-llm → LLM_API_KEY
    |  ConfigMap: sprintweave-config (model, Docling, LangGraph, …)
    |  PVC: sprintweave-data → /data
    |
    +--> Docling  (PDF/DOCX → parsed/*.md)
    +--> MaaS     POST {LLM_BASE_URL}/v1/chat/completions  (+ tools)
    +--> /data/jobs/<job-id>/workspace/
    |       input/   parsed/   context/   output/
    +--> /data/custom-agents/   (PVC catalog + rules — no rebuild)
```

**One image, two Deployments**

| Deployment | Command | Port | LLM key? | PVC? |
|------------|---------|------|----------|------|
| `sprintweave-ui` | `streamlit run ui/app.py` | 8080 | No | No |
| `sprintweave-api` | `uvicorn api.main:app --port 8000` | 8000 | Yes | Yes |

UI must not hold secrets. PVC is RWO → keep **API replicas = 1**.

### OpenShift objects

| Object | Name | Role |
|--------|------|------|
| Namespace | `sprintweave` (or `sprintweave-rhoso`) | Isolation |
| Deployment | `sprintweave-ui`, `sprintweave-api` | Pods |
| Service | same names | Cluster DNS |
| Route | `sprintweave-ui` | Public HTTPS |
| PVC | `sprintweave-data` | Jobs, inputs, custom agents |
| ConfigMap | `sprintweave-config` | Non-secret knobs |
| Secret | `sprintweave-llm` | `LLM_API_KEY` only |

Manifests: `deploy/openshift/quay-deploy-rhoso.yaml` (RHOSO) or `quay-deploy.yaml` (full).

### Image layout (Docling split)

```text
sprintweave-docling-base   (Dockerfile.docling-base)  — rebuild rarely
        │ FROM
        v
sprintweave-rhoso / sprintweave   (Dockerfile.bundle) — rebuild often
  • FastAPI / Streamlit / LangGraph
  • COPY sprintweave-web/ + agent rules
```

### Code map

| Component | Path | Role |
|-----------|------|------|
| UI | `ui/app.py` | Home / Run / Job / Agents / Deploy |
| API | `api/main.py` | Jobs, agents CRUD, CPAT deploy, health |
| Orchestrator | `api/worker.py` | Docling → stages → gates → sync output |
| Tool loop | `api/agent_runtime.py` | Agent tools over workspace (read/write/shell/self-review) |
| LangGraph | `api/langgraph_runtime.py` | StateGraph + verify/repair |
| Custom agents | `api/custom_agents.py` | PVC catalog; no image rebuild |
| LLM client | `llm/client.py` | OpenAI-compatible + tools; model catalog |
| CPAT deploy | `api/cpat_deploy.py` | Manifests / bringup / `oc` deploy |

### Pipeline stages (RHOSO)

**RHOSO** = Red Hat OpenStack Services on OpenShift.

| Stage | Full name | Agent | Typical mode | Produces |
|-------|-----------|-------|--------------|----------|
| **RDA** | RHOSO Design Authority | RHOSO DA | Single-shot | CIQ schema, workbook generator, Excel workbooks, reports |
| **RDA-1** | RDA — Schema | RHOSO DA | Single-shot | CIQ parameter schema (Python) |
| **RDA-2** | RDA — Generator | RHOSO DA | Single-shot | Workbook generator scripts |
| **RDA-3** | RDA — Workbooks | RHOSO DA | Single-shot | CIQ Excel (`.xlsx`) workbooks |
| **RDE** | RHOSO Deployment Engineer | RHOSO DE | Multi sub-stage | Full CPAT delivery tree |
| **RDE-1** | RDE — Ansible | RHOSO DE | Tool-loop / LangGraph | `output/cpat/ansible/` (roles, templates, playbooks) |
| **RDE-2** | RDE — Backend | RHOSO DE | Single-shot / LangGraph | `output/cpat/backend/` (Flask API) |
| **RDE-3** | RDE — Frontend | RHOSO DE | Single-shot / LangGraph | `output/cpat/frontend/` (React UI) |
| **RDE-4** | RDE — Docker | RHOSO DE | Single-shot / LangGraph | Dockerfile, bringup, USAGE |
| **RDE-5** | RDE — AAP | RHOSO DE | Single-shot | AAP exports (EE, credentials, job templates) |
| Gates | Human approval | — | Approve / reject / skip | Continue or stop |

**OCP** (OpenShift Container Platform) pipelines use the same pattern with **ODA** (OCP Design Authority) and **ODE** (OCP Deployment Engineer).

---

## Glossary

| Abbreviation | Full form | Meaning in SprintWeave |
|--------------|-----------|------------------------|
| **RHOSO** | Red Hat OpenStack Services on OpenShift | OpenStack control plane / services running on OpenShift |
| **OCP** | OpenShift Container Platform | Red Hat’s Kubernetes platform |
| **OCP-V** | OpenShift Virtualization | VMs on OpenShift (related training context) |
| **DA** | Design Authority | Agent that reads docs and designs CIQ schema / workbooks |
| **DE** | Deployment Engineer | Agent that generates deployable code (Ansible, app, Docker, AAP) |
| **RDA** | RHOSO Design Authority | DA stage(s) for RHOSO delivery |
| **RDE** | RHOSO Deployment Engineer | DE stage(s) for RHOSO delivery |
| **ODA** | OCP Design Authority | DA stage(s) for OCP delivery |
| **ODE** | OCP Deployment Engineer | DE stage(s) for OCP delivery |
| **CIQ** | Customer Information Questionnaire | Parameter workbook / schema customers fill for deployment |
| **MoP / MOP** | Method of Procedure | Step-by-step operational / upgrade procedure document |
| **CPAT** | CPAT delivery container tree | Generated install/delivery project (`output/cpat/…`) |
| **AAP** | Ansible Automation Platform | Red Hat automation controller / EE / job templates |
| **EE** | Execution Environment | Container image that runs Ansible jobs in AAP |
| **JT** | Job Template | AAP job definition that runs a playbook |
| **LLM** | Large Language Model | Model used for generation (via MaaS) |
| **MaaS** | Model as a Service | Enterprise OpenAI-compatible LLM endpoint |
| **Docling** | Docling (IBM/open-source) | Parses PDF/DOCX into markdown for agents |
| **LangGraph** | LangGraph | Graph-based agent workflow runtime (staged tool loops) |
| **PVC** | Persistent Volume Claim | OpenShift storage for jobs / inputs / custom agents |
| **RWO** | ReadWriteOnce | PVC access mode — why API stays at 1 replica |
| **SCC** | Security Context Constraints | OpenShift pod security policy |
| **Quay** | Quay.io | Container image registry |
| **UI** | User Interface | Streamlit SprintWeave front end |
| **API** | Application Programming Interface | FastAPI + worker backend |

---

## Quick start (users)

1. Open the UI Route:

   ```bash
   oc get route sprintweave-ui -n sprintweave -o jsonpath='https://{.spec.host}{"\n"}'
   ```

2. Confirm sidebar shows **API connected** (not demo mode).
3. **Inputs** — create an input set (PDF / DOCX / TXT / MD / XLSX).
4. **Run** — start with **Lab Requirements** (cheap smoke), then RHOSO / OCP with gates on.
5. **Job** — watch logs, approve gates, download ZIP.
6. Optional — **Deploy CPAT** from the Job page after a successful RDE run.

### Supported inputs

| Format | Processing |
|--------|------------|
| PDF / DOCX | Docling → markdown (cached by content hash) |
| Excel (`.xlsx`) | Read by agents (CIQ sheets) |
| TXT / MD | Passed through to agents |

### Typical outputs (`output/`)

- `cpat/ansible/` — playbooks, roles, Jinja2 templates, module_utils  
- `cpat/backend/` — Flask API  
- `cpat/frontend/` — React UI  
- `cpat/aap/` — AAP EE / credentials / job templates  
- `cpat/Dockerfile`, `bringup.sh`  
- `ciq-generators/`, `ciq-workbooks/`, `pipeline-reports/`  

---

## Deploy on OpenShift (platform)

### Prerequisites

- OpenShift 4.14+, `oc` logged in  
- Podman or Docker  
- Quay org (or public images)  
- MaaS / OpenAI-compatible LLM endpoint + API key  

### 1. Build images

```bash
cd /path/to/CFP_NEW
ORG=YOUR_ORG

# Docling base (once)
podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/${ORG}/sprintweave-docling-base:latest .
podman push quay.io/${ORG}/sprintweave-docling-base:latest

# App image (every code/agents change) — RHOSO example
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=cpat-main \
  --build-arg PIPELINES=lab-requirements,rhoso \
  -t quay.io/${ORG}/sprintweave-rhoso:latest .
podman push quay.io/${ORG}/sprintweave-rhoso:latest
```

### 2. Project + Secret

```bash
oc new-project sprintweave   # or: oc project sprintweave
oc create secret generic sprintweave-llm \
  --from-literal=LLM_API_KEY='YOUR_KEY' \
  -n sprintweave
```

### 3. Apply manifests

Edit `deploy/openshift/quay-deploy-rhoso.yaml` (image + ConfigMap), then:

```bash
oc apply -f sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml
oc get pods -w
oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{"\n"}'
```

### Key ConfigMap knobs

| Knob | Purpose |
|------|---------|
| `LLM_BASE_URL` / `LLM_MODEL` | MaaS endpoint + model id |
| `SPRINTWEAVE_USE_DOCLING` | PDF/DOCX → markdown |
| `SPRINTWEAVE_USE_LANGGRAPH` | Enable LangGraph runtime |
| `SPRINTWEAVE_LANGGRAPH_SCOPE` | e.g. `ansible,custom,rde` |
| `SPRINTWEAVE_PIPELINES` | Which pipelines the UI shows |
| `SPRINTWEAVE_CPAT_DEPLOY_MODE` | `openshift` / `bringup` / `manifests` |

### Day-2

```bash
# New image
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui

# Logs / workspace
oc logs -f deploy/sprintweave-api
oc rsh deploy/sprintweave-api -- ls -R /data/jobs
```

Keep **API = 1** replica (RWO PVC). UI can scale.

---

## Repository layout

```text
sprintweave-web/
  api/                 # FastAPI, worker, agent runtime, LangGraph, custom agents
  ui/                  # Streamlit app + pipeline catalog
  llm/                 # OpenAI-compatible client + model helpers
  deploy/openshift/    # Deployments, Routes, ConfigMap, PVC
  docs/                # Architecture, user guide, team/setup guides
  samples/             # Smoke inputs (e.g. lab-smoke.txt)
  scripts/             # Build / rollout helpers
  Dockerfile.bundle
  Dockerfile.docling-base
  requirements.txt
```

Agent rules are **baked from** `cpat-main` (or `sprintweave-agents`) at image build time. Custom agents live on the PVC and do not require a rebuild.

---

## Custom agents

Create agents from the **Agents** page (or `POST /v1/agents`). Rules and stages are stored under `/data/custom-agents/` on the PVC — no image rebuild. Stages can use tool-loop or single-shot mode, optional gates, and per-stage model selection when configured.

---

## Troubleshooting (quick)

| Symptom | Check |
|---------|--------|
| UI “demo mode” / API unreachable | `SPRINTWEAVE_API_URL`, API pod Running, Service DNS |
| LLM timeouts | Egress to `LLM_BASE_URL`; Secret key; ConfigMap model id |
| PVC / API won’t schedule | Do **not** set `fsGroup: 0` (restricted SCC) |
| Docling slow | First parse is heavy; repeats use content-hash cache |
| Gate stuck | Approve / Reject / Skip on the Job page |

Full tables: architecture deck § ops and User Guide § Troubleshooting.

---

## Security notes

- LLM key → **Secret** only (`sprintweave-llm`)  
- UI pod has **no** LLM credentials  
- Prefer approval **gates** before continuing expensive or deploy stages  
- Agent shell tools are constrained; treat generated playbooks as **draft** until lint/review  

---

## License / distribution

Internal Red Hat delivery tooling. Follow your team’s confidentiality and NDA rules for customer content and demos.
