# SprintWeave on OpenShift — architecture, operations, and roadmap

**Audience:** delivery and platform team  
**Scope:** Streamlit UI + worker on OpenShift, LiteLLM/MaaS (including Claude Opus via `/v1/chat/completions`), PVC storage  
**Related repo:** Cursor agents live in `sprintweave-agents/` (rules and templates). This document is for `sprintweave-web/` (cluster app).

Do not put API keys in Git, ConfigMaps, Streamlit, or this file.

---

## 1. What we replaced (and what we did not)

| Cursor today | OpenShift app |
|--------------|----------------|
| Chat + Canvas dashboard | Streamlit (Home / Run / Job / Outputs) |
| `@input/` folder | Upload → PVC `/data/jobs/<id>/input/` |
| Orchestrator rule sequencing agents | Python worker loops `stages` |
| Agent `.md` rules as system behaviour | **Not wired yet** — one generic `prompts/system.md` |
| Claude inside Cursor | LiteLLM on MaaS (OpenAI-compatible HTTP) from the **API pod** |

Cursor remains the place to **edit** agent prompts. The cluster **runs** jobs for the team via a Route. We do not run Cursor or `.cursor/` as a pod.

---

## 2. Current architecture

```text
 Browser
    |
    | HTTPS (OpenShift Route, TLS edge)
    v
 sprintweave-ui  (Streamlit :8080)
    |  no LLM key
    |  HTTP  SPRINTWEAVE_API_URL=http://sprintweave-api:8000
    v
 sprintweave-api (FastAPI + background worker :8000)
    |  Secret: LLM_API_KEY
    |  ConfigMap: LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, …
    |  PVC: /data
    |
    +--> POST LiteLLM  {LLM_BASE_URL}/chat/completions
    |
    +--> /data/jobs/<job-id>/input/     uploaded files
    +--> /data/jobs/<job-id>/output/    generated markdown
```

**One container image** (`sprintweave-ui` ImageStream) is used twice:

- UI DeploymentConfig: `streamlit run ui/app.py` on port **8080**
- API DeploymentConfig: `uvicorn api.main:app` on port **8000**

**Why two pods:** the UI must not hold the key; only the API mounts the PVC (RWO). Streamlit posts multipart files to the API.

### OpenShift objects (project `sprintweave`)

| Object | Name | Role |
|--------|------|------|
| ImageStream + BuildConfig | `sprintweave-ui` | Binary Docker build from `sprintweave-web/` |
| DeploymentConfig | `sprintweave-ui` | Streamlit |
| DeploymentConfig | `sprintweave-api` | Worker + FastAPI |
| Service | `sprintweave-ui` :8080, `sprintweave-api` :8000 | In-cluster |
| Route | `sprintweave-ui` | Public HTTPS |
| PVC | `sprintweave-data` | `/data` on API pod |
| ConfigMap | `sprintweave-config` | Non-secret LLM settings |
| Secret | `sprintweave-llm` | `LLM_API_KEY` only |

### LLM wiring (current workshop)

MaaS is **OpenAI-compatible LiteLLM**, not Anthropic’s native Messages API.

| Env | Typical value |
|-----|----------------|
| `LLM_PROVIDER` | `openai` |
| `LLM_BASE_URL` | `https://maas-rhdp.apps.maas.redhatworkshops.io/v1` |
| `LLM_MODEL` | `claude-opus-4-6` (or another MaaS model id) |
| `LLM_API_KEY` | Bearer token (`sk-…`) in Secret |

`LLM_PROVIDER=anthropic` exists in code (`llm/client.py`) for a future direct `https://api.anthropic.com/v1/messages` path. **Do not use it** for this MaaS curl (`/v1/chat/completions` + `Authorization: Bearer`).

### Request path for one Run

1. User picks a pipeline (e.g. Lab Requirements) and uploads files.  
2. Streamlit `POST /v1/jobs` (form: `pipeline_id`, `instructions`, `files`).  
3. API creates `/data/jobs/<id>/input/`, saves bytes, starts a background thread.  
4. Worker, for **each stage**: builds a user message (sources + extra instructions + previous output) and calls `complete(system, user)` with generic `prompts/system.md`.  
5. Writes `/data/jobs/<id>/output/<abbrev>.md` and `summary.md`.  
6. UI polls `GET /v1/jobs/<id>` every ~2 seconds.

**Text files** (`.md`, `.txt`) are decoded and truncated (`SPRINTWEAVE_TEXT_MAX`, default 20 000 characters). **PDF/DOCX** are stored on disk but largely treated as binary until Docling (or similar) is added.

### Token behaviour (today)

- Idle UI: **0** tokens.  
- One **Lab Requirements** job = **1** LLM call.  
- **Standard** = 4 calls; **RHOSO/NRHO** = 5.  
- Smoke file `samples/lab-smoke.txt` ≈ **1k–2.5k** tokens per run (input small; output capped by `LLM_MAX_TOKENS`).  
- Large PDFs and full agent rule files will increase this a lot.

---

## 3. Repository layout (`sprintweave-web/`)

```text
Dockerfile                 # UBI Python 3.12, Streamlit + FastAPI
requirements.txt
ui/app.py                  # Streamlit pages
ui/pipelines.py            # Pipeline catalog (stage names)
ui/job_client.py           # Fake jobs OR HTTP API
api/main.py                # FastAPI
api/worker.py              # Stage loop + file I/O
llm/client.py              # openai vs anthropic HTTP
prompts/system.md          # Generic system prompt (current)
samples/lab-smoke.txt      # Cheap upload for tests
deploy/openshift/
  sprintweave-ui.yaml
  sprintweave-api.yaml
```

---

## 4. How it works for a user

1. Open the Route (`oc get route sprintweave-ui`).  
2. Sidebar must show **Backend: API** and **API reachable**.  
3. Home → **Lab Requirements** (1 stage) for tests; avoid Full/RHOSO until agents and cost are agreed.  
4. Run → upload `.txt`/`.md` → **Run pipeline**.  
5. Job page shows status, logs, `On disk` path.  
6. On success, download markdown; files remain on the PVC.

Browse files from the bastion:

```bash
oc rsh dc/sprintweave-api
ls -R /data/jobs
```

---

## 5. Operations runbook (bastion)

### 5.1 Build directory

Always `cd` to the folder that contains **`Dockerfile`** (not `deploy/openshift`).

```bash
oc project sprintweave
oc start-build sprintweave-ui --from-dir=. --follow
```

`oc new-build --name=sprintweave-ui` **fails if the BuildConfig already exists** — that is expected. Reuse `start-build`.

### 5.2 Apply manifests

```bash
oc apply -f deploy/openshift/sprintweave-api.yaml
oc apply -f deploy/openshift/sprintweave-ui.yaml
```

If `oc rollout latest` says **already in progress**, wait. Do not stack rollouts.

```bash
oc get pods
oc get dc sprintweave-api
oc get pvc
oc get route sprintweave-ui
```

Healthy: `sprintweave-api-*-xxxxx` and `sprintweave-ui-*-xxxxx` **1/1 Running**, PVC **Bound**.

### 5.3 LLM Secret and ConfigMap

```bash
oc create secret generic sprintweave-llm \
  --from-literal=LLM_API_KEY='YOUR_KEY' \
  -n sprintweave
```

```bash
oc patch configmap sprintweave-config -n sprintweave --type merge -p '{
  "data": {
    "LLM_PROVIDER": "openai",
    "LLM_BASE_URL": "https://maas-rhdp.apps.maas.redhatworkshops.io/v1",
    "LLM_MODEL": "claude-opus-4-6",
    "LLM_MAX_TOKENS": "1024",
    "LLM_TIMEOUT": "180"
  }
}'
oc rollout latest dc/sprintweave-api
```

After changing the Secret or ConfigMap, wait for a **new** API pod.

### 5.4 Known platform issue (SCC)

Do **not** set `securityContext.fsGroup: 0` on the API pod. Restricted SCC rejects group `0`; the API replica stays at CURRENT 0 (`FailedCreate`). Omit pod-level `fsGroup`, or use the project’s allocated supplemental GID (`oc get project sprintweave -o yaml` → `sa.scc.supplemental-groups`).

### 5.5 Typical failures

| Symptom | Cause |
|---------|--------|
| Job **failed** `401 Unauthorized` … `maas-rhdp…` | Wrong/expired MaaS key, or Claude native key used against LiteLLM |
| Sidebar **fake jobs** | `SPRINTWEAVE_API_URL` empty; re-apply UI YAML |
| Build `Dockerfile: no such file` | `--from-dir` was `deploy/openshift` |
| API never schedules | `fsGroup: 0` (see 5.4) |
| PVC Pending | Normal until the first API pod mounts it |

---

## 6. Further enhancement — remaining agents

**Goal:** each pipeline stage uses the real Cursor agent rule as the LLM **system** prompt. No new OpenShift service.

### 6.1 Mapping

```text
ui/pipelines.py  stage.agent
        →  lookup
prompts/agents/agent-*.md     (copy from sprintweave-agents/.cursor/rules/)
        →  system
LiteLLM chat/completions
        →  /data/jobs/<id>/output/<abbrev>.md
```

| `stage.agent` | Suggested file |
|---------------|----------------|
| Requirements Analyst | `agent-requirements-analyst.md` |
| Solution Architect | `agent-solution-architect.md` |
| Technical Lead | `agent-technical-lead.md` |
| QA Architect | `agent-qa-architect.md` |
| DevOps Engineer | `agent-devops-engineer.md` |
| Cloud Deployment Engineer | `agent-cloud-deployment-engineer.md` |
| Automation Engineer | `agent-automation-engineer.md` |
| SRE Engineer | `agent-sre-engineer.md` |
| Technical Writer | `agent-technical-writer.md` |
| Governance Specialist | `agent-governance-specialist.md` |
| Project Manager | `agent-project-manager.md` |
| Sprint Coach | `agent-sprint-coach.md` |
| Proposal Writer | `agent-proposal-writer.md` |
| RHOSO DA | `agent-rhoso-da.md` |
| RHOSO Deployment Engineer | `agent-rhoso-deployment-engineer.md` |
| NRHO DA | `agent-nrho-da.md` |
| NRHO Deployment Engineer | `agent-nrho-deployment-engineer.md` |

Missing mapping → fall back to `prompts/system.md` or fail the stage (team choice).

**One stage = one file = one LLM call.** Do not concatenate all agents into one prompt.

`agent-orchestrator.md` is **not** an LLM agent; Python already sequences stages.

### 6.2 Implementation outline (when you build it)

1. Copy selected `agent-*.md` into `sprintweave-web/prompts/agents/`.  
2. In `api/worker.py`, resolve `stage["agent"]` → file; use as `system`. Optionally append `context/templates/<agent>.md`.  
3. Rebuild (`oc start-build`), roll API.  
4. Prove **Lab Requirements** first (`RHOSO DA` only), then Standard, then RHOSO/NRHO.  
5. Later: load `sprintweave-agents/context/pipelines.yaml` instead of duplicating `pipelines.py`. Honour YAML `conditional` stages.  
6. Later: Excel via existing `sprintweave-agents/tools/excel-generator.py` after markdown exists.

### 6.3 Token warning

Full agent markdown files are large system prompts. Add them only after a cheap smoke test works. Keep `LLM_MAX_TOKENS` and `SPRINTWEAVE_TEXT_MAX` as guards.

---

## 7. Further enhancement — Docling

**Goal:** turn PDF/DOCX/PPTX into Markdown **before** the LLM so agents see real content.

```text
/data/jobs/<id>/input/file.pdf
        →  Docling on the API/worker
        →  /data/jobs/<id>/parsed/file.md
        →  existing stage loop (read parsed/ first)
```

- Run Docling **only on the API pod** (or a future parse Deployment), never in Streamlit.  
- Skip Docling for `.txt`/`.md`.  
- Dependencies are heavy (often torch); image size, RAM, and job time go up. Workshop **single-node** clusters may OOM — raise API memory or use a lighter extractor (`pypdf`) first.  
- Parsed Markdown can **increase tokens**; keep truncation.  
- Alternative: separate `sprintweave-parse` Deployment sharing the PVC if the UI/API image must stay small.

---

## 8. Suggested delivery sequence

| Phase | Outcome |
|-------|---------|
| **Now (done)** | Route + API + PVC; Lab Requirements; LiteLLM; generic prompt |
| **Next** | Map `RHOSO DA` → `agent-rhoso-da.md`; rebuild; smoke job |
| **Then** | Remaining agents used by Standard / RHOSO / NRHO |
| **Then** | Docling for PDF/DOCX |
| **Then** | YAML pipelines + Excel tools + optional OAuth on the Route |

---

## 9. Security and hygiene

- Keys only in Secret `sprintweave-llm`. Rotate if a key was pasted in chat, tickets, or screenshots.  
- MaaS keys may expire (workshop often 7 days).  
- Do not log full document text or the Bearer token.  
- UI replica: **1** until job state is only in the API (not Streamlit session).  
- DeploymentConfig is deprecated in OCP 4.14+; a later enhancement can move to `Deployment`.

---

## 10. Quick reference

```bash
# URL
oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{"\n"}'

# Logs
oc logs -f dc/sprintweave-api
oc logs -f dc/sprintweave-ui

# Rebuild after code/prompt changes
cd /path/to/sprintweave-web
oc start-build sprintweave-ui --from-dir=. --follow
```

Smoke upload: `sprintweave-web/samples/lab-smoke.txt`.
