# SprintWeave — End-to-End Architecture & Operations (Presentation Deck)

**Audience:** delivery leads, platform engineers, demos  
**Scope:** Cursor-based CPAT pipeline vs OpenShift SprintWeave (RHOSO)  
**Repos:** local repo as of current SprintWeave + LangGraph + custom agents work  

> Do **not** put API keys in Git, slides, ConfigMaps, or this document.

---

## Slide 1 — One-line pitch

**SprintWeave** turns uploaded customer docs (PDF/DOCX) into RHOSO delivery artifacts (CIQ workbooks + CPAT container tree) by running the **same agent rules** that Cursor uses — either:

| Mode | Where it runs | LLM / agent engine |
|------|---------------|--------------------|
| **Cursor SprintWeave** | Developer laptop / Cursor container | Cursor SDK + Cursor models |
| **OpenShift SprintWeave** | Cluster Route (team UI) | MaaS OpenAI-compatible API + tool loop / LangGraph |

Same **agent brain** (`.cursor/rules`, templates, skills). Different **runtime**.

---

## Slide 2 — Why two runtimes?

| Need | Cursor | OpenShift |
|------|--------|-----------|
| Edit agent rules interactively | ✅ Best | Paste / PVC custom agents |
| Team self-service (no Cursor seat) | ❌ | ✅ Browser Route |
| Reproducible cluster jobs | Partial | ✅ PVC + job IDs + zip download |
| Cursor SDK / Composer models | ✅ | ❌ (use MaaS Claude / other) |
| Cost control / gates / stop | Manual | Approval gates, cancel, single-shot knobs |

**Positioning:** Cursor remains the place to **author** golden agents. OpenShift **executes** them for the team.

---

# 1. Architecture

## 1.1 Big picture (both worlds)

```text
                    Customer inputs (PDF / DOCX / TXT)
                                    |
                                    v
                         +-------------------+
                         |  Agent rules      |  .cursor/rules/*.md
                         |  Templates        |  context/templates/
                         |  Skills           |  .cursor/skills/
                         +-------------------+
                                    |
              +---------------------+---------------------+
              |                                           |
              v                                           v
   +----------------------+                 +---------------------------+
   | Cursor runtime       |                 | OpenShift SprintWeave     |
   | run_pipeline.py      |                 | Streamlit UI + FastAPI    |
   | Cursor SDK Agent     |                 | worker.py + LangGraph     |
   | CURSOR_API_KEY       |                 | LLM_API_KEY (MaaS)        |
   +----------------------+                 +---------------------------+
              |                                           |
              v                                           v
        output/ciq-*                                /data/jobs/<id>/
        output/cpat/                                output/ + zip download
```

---

## 1.2 OpenShift runtime architecture (current)

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

**One image, two Deployments:**

| Deployment | Command | Port | LLM key? | PVC? |
|------------|---------|------|----------|------|
| `sprintweave-ui` | `streamlit run ui/app.py` | 8080 | No | No |
| `sprintweave-api` | `uvicorn api.main:app --port 8000` | 8000 | Yes | Yes |

**Why split?** UI must not hold secrets; PVC is RWO → API replicas stay at **1**.

---

## 1.3 OpenShift objects

| Object | Name | Role |
|--------|------|------|
| Project / Namespace | `sprintweave` (or `sprintweave-rhoso`) | Isolation |
| Deployment | `sprintweave-ui`, `sprintweave-api` | Pods |
| Service | same names | Cluster DNS |
| Route | `sprintweave-ui` | Public HTTPS |
| PVC | `sprintweave-data` | Jobs, inputs, custom agents |
| ConfigMap | `sprintweave-config` | Non-secret knobs |
| Secret | `sprintweave-llm` | `LLM_API_KEY` only |
| (optional) Secret | `quay-pull` | Private Quay pull |

Manifest: `deploy/openshift/quay-deploy-rhoso.yaml` (RHOSO) or `quay-deploy.yaml` (full).

---

## 1.4 Image architecture (Docling split)

Docling is heavy (hours, multi-GB). We split builds:

```text
┌─────────────────────────────────────┐
│ sprintweave-docling-base            │  Dockerfile.docling-base
│  • python:3.12-slim                 │  Rebuild RARELY
│  • docling + deps                   │
│  • HF/model cache paths             │
└─────────────────┬───────────────────┘
                  │ FROM
                  v
┌─────────────────────────────────────┐
│ sprintweave-rhoso  (or sprintweave) │  Dockerfile.bundle
│  • FastAPI / Streamlit / LangGraph  │  Rebuild OFTEN (minutes)
│  • COPY sprintweave-web/            │
│  • COPY agents (cpat-main or …)     │
│  • overlay .cursor/skills           │
└─────────────────────────────────────┘
```

| Quay image | Agents source | Typical pipelines |
|------------|---------------|-------------------|
| `sprintweave-docling-base` | (none) | Base only |
| `sprintweave-rhoso` | `cpat-main` | `lab-requirements,rhoso` |
| `sprintweave` | `sprintweave-agents` | `all` or filtered |

---

## 1.5 Job workspace layout (OpenShift)

```text
/data/
  jobs/<job_id>/
    workspace/
      input/      # uploaded / input-set files
      parsed/     # Docling markdown (prefer these)
      context/    # seeded templates / glossary
      .cursor/    # skills + rules for tools
      output/     # real deliverables
    output/       # mirrored for download API / zip
  inputs/<input_id>/          # reusable input sets
  custom-agents/
    catalog.json
    rules/agent-<id>.md
```

---

## 1.6 Pipeline stages (RHOSO delivery)

| Stage | Agent | Mode (typical) | Produces |
|-------|-------|----------------|----------|
| RDA | RHOSO DA | Single-shot (legacy path today) | CIQ schema, generator, `.xlsx`, reports |
| RDE-Ansible | RHOSO DE | Tool-loop + LangGraph + until-complete rounds | `output/cpat/ansible/` |
| RDE-Backend | RHOSO DE | Single-shot / LangGraph bundle | `output/cpat/backend/` |
| RDE-Frontend | RHOSO DE | Single-shot / LangGraph bundle | `output/cpat/frontend/` |
| RDE-Docker | RHOSO DE | Single-shot / LangGraph bundle | Dockerfile, bringup, USAGE |
| Gates | Human | Approve / reject / skip | Continue or stop |

**LangGraph scope (ConfigMap):** `SPRINTWEAVE_LANGGRAPH_SCOPE=ansible,custom,rde`  
RDA remains on dedicated `_run_rda_single_shot` (same streaming `complete()`; not yet wrapped in LangGraph).

---

## 1.7 Runtime components (OpenShift code map)

| Component | Path | Role |
|-----------|------|------|
| UI | `ui/app.py` | Home / Run / Job / Agents / Deploy CPAT |
| API | `api/main.py` | Jobs, agents CRUD, CPAT deploy, health |
| Orchestrator | `api/worker.py` | Docling → stages → gates → sync output |
| Tool loop (legacy) | `api/agent_runtime.py` | Cursor-like tools over workspace |
| LangGraph | `api/langgraph_runtime.py` | StateGraph + SSE keep-alive; verify+repair |
| Custom agents | `api/custom_agents.py` | PVC catalog; no image rebuild |
| LLM client | `llm/client.py` | OpenAI-compatible + `complete_tools` stream |
| CPAT deploy | `api/cpat_deploy.py` | Manifests / bringup / `oc` deploy |
| Agent rules (baked) | `/app/sprintweave-agents/.cursor/rules/` | Image copy of cpat-main |

---

# 2. Setup — from Docker images to a running Route

## 2.0 Prerequisites checklist

| Item | Notes |
|------|-------|
| OpenShift 4.14+ | `oc` logged in with project-create rights |
| Podman or Docker | Bastion / WSL preferred if corp proxy breaks pulls |
| Quay org + repos | `sprintweave-docling-base`, `sprintweave-rhoso` (and/or `sprintweave`) |
| LLM endpoint | OpenAI-compatible `/v1` (e.g. MaaS LiteLLM) |
| LLM API key | Bearer token — **Secret only** |
| Source tree | `CFP_NEW/` containing `sprintweave-web/` + `cpat-main/` (and optionally `sprintweave-agents/`) |

---

## 2.1 Build Docling base (once)

```bash
cd /path/to/CFP_NEW
ORG=rh_global_services_auto   # or YOUR_ORG

podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/${ORG}/sprintweave-docling-base:latest .

podman login quay.io
podman push quay.io/${ORG}/sprintweave-docling-base:latest
```

**Expect:** long build, multi-GB image. Rebuild only when Docling / OCR deps change.

---

## 2.2 Build thin app image (every code/agents change)

### RHOSO / CPAT (recommended for RHOSO demos)

```bash
cd /path/to/CFP_NEW
ORG=rh_global_services_auto

podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=cpat-main \
  --build-arg PIPELINES=lab-requirements,rhoso \
  -t quay.io/${ORG}/sprintweave-rhoso:latest .

podman push quay.io/${ORG}/sprintweave-rhoso:latest
```

### Full agents workspace

```bash
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=sprintweave-agents \
  --build-arg PIPELINES=all \
  -t quay.io/${ORG}/sprintweave:latest .

podman push quay.io/${ORG}/sprintweave:latest
```

### Bastion helper (optional)

```bash
# From laptop: pack tree → bastion
# On bastion:
bash ~/sprintweave-build/sprintweave-web/scripts/bastion-build-rollout.sh
# Env: IMAGE, BASE_IMAGE, NAMESPACE, PIPELINES, SKIP_PUSH, SKIP_ROLLOUT
```

---

## 2.3 Cursor CPAT image (separate — Cursor SDK path)

Built from **cpat-main** root (not SprintWeave bundle):

```bash
cd /path/to/CFP_NEW/cpat-main

docker build -f agents/cursor/Dockerfile -t cpat-agents-cursor .

docker run --rm \
  -e CURSOR_API_KEY="cursor_..." \
  -v "$(pwd)/output:/workspace/output" \
  cpat-agents-cursor --pipeline rhoso-delivery
```

This image carries rules/templates + `run_pipeline.py`. It does **not** use MaaS or OpenShift PVC.

---

# 3. Project, secrets, deploy — end to end

## 3.1 Login and project

```bash
oc login https://api.<cluster>:6443
oc new-project sprintweave          # or sprintweave-rhoso
oc project sprintweave
```

---

## 3.2 Network check to LLM (no key)

```bash
oc run curl-test --image=registry.access.redhat.com/ubi9/ubi-minimal \
  --rm -it --restart=Never -- \
  curl -sS -o /dev/null -w "%{http_code}\n" \
  https://maas-rhdp.apps.maas.redhatworkshops.io/v1/models
```

`200` or `401` = reachability OK. Timeouts = fix egress first.

---

## 3.3 Create LLM Secret

```bash
oc create secret generic sprintweave-llm \
  --from-literal=LLM_API_KEY='<your-key>' \
  -n sprintweave
```

Never put the key in the ConfigMap or YAML committed to Git.

---

## 3.4 (Private Quay) Pull secret

```bash
oc create secret docker-registry quay-pull \
  --docker-server=quay.io \
  --docker-username='<quay-user>' \
  --docker-password='<quay-token>' \
  --docker-email='unused@example.com' \
  -n sprintweave

oc secrets link default quay-pull --for=pull -n sprintweave
```

Skip if Quay repo is public.

---

## 3.5 Edit and apply manifests

1. Copy `deploy/openshift/quay-deploy-rhoso.yaml` (or `quay-deploy.yaml`).
2. Replace `quay.io/YOUR_ORG/sprintweave-rhoso:latest` with your image.
3. Confirm ConfigMap values (model, LangGraph, Docling, pipelines).

```bash
oc apply -f sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml
```

Creates: PVC, ConfigMap, API+UI Deployments, Services, Route.

---

## 3.6 Wait and open UI

```bash
oc get pods -w
# Both should be 1/1 Running

oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{"\n"}'
```

Sidebar should show **API connected** (not demo mode).

---

## 3.7 Smoke test

1. **Inputs** — small PDF or `samples/lab-smoke.txt`.
2. **Run** — Lab Requirements (cheap) first.
3. Job page: Docling (if PDF) → stage → artifacts.
4. Then full **RHOSO** pipeline with gates on.

```bash
oc logs -f deploy/sprintweave-api
oc rsh deploy/sprintweave-api -- ls -R /data/jobs
```

---

## 3.8 Day-2 operations

| Action | Command |
|--------|---------|
| New image | `oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui` |
| Rotate key | delete/recreate `sprintweave-llm` + restart API |
| Change model | `oc patch configmap sprintweave-config …` + restart API |
| Logs | `oc logs -f deploy/sprintweave-api` |
| Scale UI | OK to scale UI; **keep API = 1** (RWO PVC) |

---

## 3.9 Key ConfigMap knobs (presentation table)

| Knob | Purpose |
|------|---------|
| `LLM_BASE_URL` / `LLM_MODEL` | MaaS endpoint + model id |
| `SPRINTWEAVE_USE_DOCLING` | PDF → markdown |
| `SPRINTWEAVE_RDA_SINGLE_SHOT` / `RDE_SINGLE_SHOT` | Cheap one-shot bundles |
| `SPRINTWEAVE_ANSIBLE_ROUND_STEPS` / `MAX_ROUNDS` | Ansible until-complete |
| `SPRINTWEAVE_USE_LANGGRAPH` | Enable LangGraph runtime |
| `SPRINTWEAVE_LANGGRAPH_SCOPE` | `ansible,custom,rde` (comma list or `all`) |
| `SPRINTWEAVE_LANGGRAPH_KEEPALIVE` | SSE stream via `complete_tools` |
| `SPRINTWEAVE_CPAT_DEPLOY_MODE` | `openshift` / `bringup` / `manifests` |
| `SPRINTWEAVE_PIPELINES` | Which pipelines UI shows |

---

# 4. Detailed working — Cursor vs OpenShift

## 4.1 Cursor-based SprintWeave (golden path)

### Flow

```text
1. Developer has cpat-main checkout (rules, context, optional golden output/)
2. docker build agents/cursor/Dockerfile  OR  run locally with CURSOR_API_KEY
3. run_pipeline.py loads PIPELINE_STAGES (RDA-1..3, RDE-1..4, …)
4. For each stage:
      Agent.create(model, local cwd=CPAT_ROOT)
      agent.send(stage["prompt"])   # prompt points at .cursor/rules/...
      stream messages → wait
      verify_paths (files exist + non-empty)
      if RDE and validator fails → repair prompt on SAME agent session
5. Artifacts land under output/
```

### What Cursor does well

- Reads `.cursor/rules` automatically in the project workspace  
- Rich multi-turn tool use (Composer / Cursor Agent)  
- Stage prompts are **specific** (file counts, paths, CRITICAL notes)  
- **verify_paths** + **repair loop** after validation  

### Entry points

| Piece | Location |
|-------|----------|
| Pipeline runner | `cpat-main/agents/cursor/run_pipeline.py` |
| Dockerfile | `cpat-main/agents/cursor/Dockerfile` |
| Rules | `cpat-main/.cursor/rules/` |
| Validator | `cpat-main/agents/validate_rhoso_output.py` |

---

## 4.2 OpenShift-based SprintWeave (team path)

### End-to-end request path

```text
User opens Route → Streamlit
  → Create / reuse Input set (PVC /data/inputs/<id>/)
  → Select pipeline (baked + custom from /data/custom-agents/)
  → POST /v1/jobs  (files or input_id)
       |
       v
worker start_job_thread
  1) Seed workspace (context, skills, rules)
  2) Docling each PDF/DOCX → parsed/*.md  (cache by hash)
  3) For each stage in pipeline:
       - Resolve agent rule (PVC custom OR baked image)
       - Mode: tool_loop  OR  single_shot (### FILE bundle)
       - Runtime:
           * Ansible / custom tool-loop → LangGraph (if enabled) else legacy
           * RDE Backend/Frontend/Docker → LangGraph bundle or legacy
           * RDA → _run_rda_single_shot (legacy single-shot today)
       - Soft gates / ansible missing-file gate / until-complete rounds
       - Optional approval gate → pause for human
  4) Sync workspace/output → job output + zip
  5) Optional: Deploy CPAT from UI (manifests / bringup / oc)
```

### How agent rules are used

1. `_system_for_agent()` loads rule markdown (PVC first, then image).  
2. Injects OpenShift tool runtime instructions (paths, anti-explore, edit style).  
3. User message includes stage goal, `@` prompt chips, document excerpt, previous stage summary.  
4. Tools write under `output/` only (workspace jail).  

### Modes compared

| Mode | When | Mechanism |
|------|------|-----------|
| **Single-shot** | Lab, RDA, RDE BE/FE/Docker | One `complete()` → parse `### FILE:` → write |
| **Tool-loop** | Ansible, rich custom agents | Many steps: `write_file` / `append_file` / `run_python` |
| **LangGraph** | Flag + scope | Same LLM client (SSE keep-alive); graph routing; verify+repair for custom |
| **Legacy fallback** | LangGraph error | Resume mode — do not rewrite existing files |

### Custom agents (no rebuild)

UI **Agents** page → `POST /v1/agents` → PVC:

- Rule markdown (paste Cursor rule as-is)  
- `mode`: tool_loop / single_shot  
- Optional multi-stage `stages_json`  
- Optional `verify_paths` + `repair_prompt` (Cursor parity)  
- Auto-extract `output/...` paths from rule if verify list empty  

Pipeline appears on Home with ✨ — same worker path as baked agents.

### Verify + repair (Cursor parity on OpenShift)

After tool-loop (LangGraph):

1. Check `verify_paths` exist and are non-empty (**local FS — $0**).  
2. If missing → inject repair user message → short extra tool loop.  
3. Logs: `[verify]`, `[repair]`, `[verify-post-repair]`.  

---

## 4.3 Side-by-side comparison (use in slides)

| Topic | Cursor | OpenShift SprintWeave |
|-------|--------|------------------------|
| Orchestrator | `run_pipeline.py` | `api/worker.py` |
| Agent engine | Cursor SDK `Agent.create` | Tool loop / LangGraph + MaaS |
| Auth | `CURSOR_API_KEY` | `LLM_API_KEY` Secret |
| Rules | Project `.cursor/rules` | Image + PVC custom |
| Inputs | Files in repo / cwd | Upload → PVC input sets |
| PDF parse | Cursor / local tools | Docling in API pod |
| UI | Cursor IDE | Streamlit Route |
| Gates | Manual / script verify | UI approve / reject / skip |
| Repair | Validator + same session | LangGraph verify+repair (+ ansible rounds) |
| Deploy CPAT | Manual | UI “Deploy & run CPAT” |
| Cost knobs | Model choice | Single-shot flags, max steps, compact history |

---

## 4.4 RHOSO happy-path timeline (OpenShift)

Typical log sequence for a presentation:

```text
[docling] 1/N … → [parsed] *.md
[docling] done (ok=N)
[running] RDA RHOSO DA
[rda-single-shot] schema → generator → xlsx
[gate] wait for approval (if enabled)
[running] RDE …
[rde-pass] Ansible — Cursor-like tool loop / [langgraph] steps
[ansible-gate] rounds until required files exist
[rde-pass] Backend / Frontend / Docker  (single-shot / langgraph)
[done] artifacts ready → download zip → optional Deploy CPAT
```

---

## 4.5 What “closer to Cursor” means on OpenShift today

| Cursor behavior | OpenShift equivalent |
|-----------------|----------------------|
| Agent rules drive output | Same rule markdown in system prompt |
| File tools + edits | `WorkspaceTools` (write / append / str_replace / run_python) |
| @ references | `@input` `@cpat` `@context` chips on Run |
| Sub-stages | RDE Ansible → Backend → Frontend → Docker |
| Verify outputs | `verify_paths` + ansible missing gate |
| Repair | LangGraph repair pass; ansible until-complete rounds |
| Skills | `.cursor/skills` seeded + prompt injection |
| Keep-alive long runs | SSE streaming `complete_tools` (not bare ChatOpenAI) |

**Still different:** no Cursor Composer model; no full IDE; RDA not on LangGraph yet; quality depends on MaaS + rule richness.

---

# 5. Presentation storyboard (suggested order)

| # | Title | Speak to |
|---|-------|----------|
| 1 | Problem | Manual RHOSO packaging from PDFs is slow / inconsistent |
| 2 | Solution | Same agent rules, two runtimes |
| 3 | Architecture | UI → API → Docling → LLM → PVC |
| 4 | Images | Docling base (rare) + thin app (often) |
| 5 | Cluster setup | Project → Secret → ConfigMap → apply → Route |
| 6 | Cursor flow | `run_pipeline.py` + verify + repair |
| 7 | OpenShift flow | Job worker stages + gates + zip |
| 8 | LangGraph / custom agents | Flagged runtime + PVC agents without rebuild |
| 9 | Demo | Lab smoke → RHOSO job logs → download → Deploy CPAT |
| 10 | Ops | Rollout, key rotate, cost knobs, known limits |

---

# 6. Quick reference cards

## Build + push (RHOSO)

```bash
cd /path/to/CFP_NEW
ORG=YOUR_ORG
podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/${ORG}/sprintweave-docling-base:latest .
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=cpat-main \
  --build-arg PIPELINES=lab-requirements,rhoso \
  -t quay.io/${ORG}/sprintweave-rhoso:latest .
podman push quay.io/${ORG}/sprintweave-docling-base:latest
podman push quay.io/${ORG}/sprintweave-rhoso:latest
```

## Cluster bootstrap

```bash
oc new-project sprintweave
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='…'
# edit YOUR_ORG in YAML, then:
oc apply -f sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml
oc get route sprintweave-ui
```

## After code change

```bash
# rebuild thin image + push, then:
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui -n sprintweave
```

---

# 7. Related docs in repo

| Doc | Use |
|-----|-----|
| `docs/NEW-CLUSTER-SETUP.md` | First-time cluster checklist |
| `docs/QUAY.md` | Image naming + build args |
| `docs/CURSOR-LIKE-RHOSO.md` | Tool loop / single-shot / smoke |
| `docs/TEAM-GUIDE.md` | Older team overview (partially superseded by this deck) |
| `deploy/openshift/quay-deploy-rhoso.yaml` | Live ConfigMap + Deployments |
| `scripts/bastion-build-rollout.sh` | Bastion build → push → rollout |

---

## Closing line for slides

> **Cursor authors the agents. OpenShift runs them for the team — with Docling, durable jobs, approval gates, LangGraph tool loops, and optional one-click CPAT deploy — without rebuilding the image for every new custom agent.**
