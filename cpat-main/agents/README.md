# SprintWeave Agent Pipeline — Runners

Run the RHOSO Design Architect (RDA) and RHOSO Deployment Engineer (RDE)
SprintWeave agents outside the Cursor IDE using one of three execution
backends.

## Directory Layout

```
agents/
  rhoai/               ← Enterprise: Red Hat OpenShift AI (vLLM on OCP)
    run-agents.ps1        PowerShell helper (auto-discovers RHOAI endpoint)
    run-agents.sh         Bash helper
    requirements.txt      openai, pyyaml

  ollama/              ← Local GPU: Ollama (self-contained, no API key)
    run_pipeline.py       Shared pipeline runner (OpenAI-compatible API)
    Dockerfile            Self-contained container (Ollama + model)
    run-agents.ps1        PowerShell helper
    run-agents.sh         Bash helper
    requirements.txt      openai, pyyaml

  cursor/              ← Cloud: Cursor SDK (requires API key)
    run_pipeline.py       Pipeline runner (Cursor SDK)
    Dockerfile            Container image
    run-agents.ps1        PowerShell helper
    run-agents.sh         Bash helper
    requirements.txt      cursor-sdk
```

## Quick Comparison

| | RHOAI (Enterprise) | Ollama (Local GPU) | Cursor SDK (Cloud) |
|--|-------------------|-------------------|-------------------|
| **API Key** | None (uses `oc` token) | Not needed | Required (`CURSOR_API_KEY`) |
| **Model** | IBM Granite, Llama, any vLLM model | qwen2.5-coder, Llama, etc. | Claude, GPT, etc. |
| **GPU** | OCP GPU nodes (L4/A100/H100) | Your local GPU (8–48 GB) | Not needed locally |
| **Quality** | Good–Excellent (model-dependent) | Good–Excellent (model-dependent) | Excellent |
| **Privacy** | In-cluster (air-gapped possible) | 100% local | Cloud inference |
| **Cost** | RHDP demo / existing OCP cluster | Free (your hardware) | Cursor subscription |
| **Best For** | Team demos, enterprise deployment | Development, offline use | Highest quality output |

## Architecture

All three runners execute the SprintWeave pipelines:

**RHOSO Pipeline (7 stages):**
```
RDA-1 (Schema) → RDA-2 (Generator) → RDA-3 (Workbooks) → RDE-1 (Ansible) → RDE-2 (Backend) → RDE-3 (Frontend) → RDE-4 (Docker)
```

**OCP Pipeline (7 stages):**
```
ODA-1 (Schema) → ODA-2 (Generator) → ODA-3 (Workbooks) → ODE-1 (Ansible) → ODE-2 (Backend) → ODE-3 (Frontend) → ODE-4 (Docker)
```

**Full Delivery Pipeline (14 stages):**
```
RHOSO (RDA-1..3 → RDE-1..4) → OCP (ODA-1..3 → ODE-1..4)
```

RDA-3 / ODA-3 are pure shell execution steps (no LLM) — they run generator scripts to produce Excel workbooks.

The `rhoai/` and `ollama/` paths share the same OpenAI-compatible pipeline
runner (`ollama/run_pipeline.py`). RHOAI helpers add endpoint auto-discovery
and OCP token resolution on top.

```
                    ┌─────────────────────────────────────────┐
                    │   SprintWeave Agent Pipeline             │
                    │   (RDA → RDE-1 → RDE-2 → RDE-3 → RDE-4)│
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌────────────┐ ┌────────────┐ ┌────────────┐
             │   RHOAI    │ │   Ollama   │ │ Cursor SDK │
             │ vLLM on OCP│ │ Local GPU  │ │   Cloud    │
             │            │ │            │ │            │
             │ Granite 8B │ │ qwen2.5    │ │ Claude 4   │
             │ Llama 3.2  │ │ :14b/:32b  │ │ GPT-4o     │
             │ any HF mdl │ │ Llama, etc │ │ Gemini     │
             └────────────┘ └────────────┘ └────────────┘
```

---

## RHOAI — Red Hat OpenShift AI (Recommended for Enterprise)

Runs the SprintWeave pipeline against a vLLM model server deployed on
Red Hat OpenShift AI. Uses the same pipeline runner as Ollama but targets a
remote RHOAI inference endpoint.

### Supported RHOAI Environments

| Environment | Source | Models | GPU |
|---|---|---|---|
| **Llama Stack on OpenShift** | [RHDP Catalog](https://catalog.demo.redhat.com) | Granite 3.2 8B + Llama 3.2 3B | vLLM on OCP GPU nodes |
| **RHOAI on OCP with NVIDIA GPUs** | RHDP Catalog | Deploy any model | NVIDIA L4 (24 GB) |
| **Red Hat OpenShift AI 3** | RHDP Catalog | Deploy any model | GPU SNO instance |
| **vLLM Playground** | RHDP Catalog | Any vLLM model | AWS GPU instance |
| **Your own RHOAI cluster** | Self-managed | Any HuggingFace model | Your GPU nodes |

### Quick Start

```powershell
# 1. Provision an RHOAI environment (e.g. Llama Stack on OpenShift from RHDP)
# 2. Log into the OCP cluster
oc login --token=<token> --server=https://api.<cluster>:6443

# 3. Auto-discover and test the vLLM endpoint
.\agents\rhoai\run-agents.ps1 discover
.\agents\rhoai\run-agents.ps1 test

# 4. Run the SprintWeave pipeline
.\agents\rhoai\run-agents.ps1 run
.\agents\rhoai\run-agents.ps1 run -Pipeline rda        # RDA only
.\agents\rhoai\run-agents.ps1 run -Pipeline rde        # RDE only
.\agents\rhoai\run-agents.ps1 run -Stage RDE-1         # Single stage
```

Or set the endpoint explicitly:

```powershell
$env:RHOAI_API_BASE = "https://granite-vllm-llama-serve.apps.cluster.example.com/v1"
.\agents\rhoai\run-agents.ps1 run
```

### Bash

```bash
# Auto-discover
./agents/rhoai/run-agents.sh discover
./agents/rhoai/run-agents.sh test

# Run
./agents/rhoai/run-agents.sh run
./agents/rhoai/run-agents.sh run --pipeline rda

# Or explicit endpoint
export RHOAI_API_BASE="https://granite-vllm-llama-serve.apps.cluster.example.com/v1"
./agents/rhoai/run-agents.sh run
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RHOAI_API_BASE` | Auto-detected via `oc` | vLLM route URL (e.g. `https://<route>/v1`) |
| `RHOAI_API_KEY` | `oc whoami -t` | Bearer token for vLLM endpoint |
| `RHOAI_MODEL` | `ibm-granite/granite-3.2-8b-instruct` | Model served by vLLM |

### Model Recommendations by VRAM

| GPU | VRAM | Recommended Model |
|---|---|---|
| NVIDIA L4 | 24 GB | `ibm-granite/granite-3.2-8b-instruct`, `qwen2.5-coder:14b` |
| NVIDIA A100 | 40–80 GB | `qwen2.5-coder:32b`, `meta-llama/Llama-3.1-70b-instruct-q4_0` |
| NVIDIA H100 | 80 GB | `meta-llama/Llama-3.1-70b-instruct`, `qwen2.5-coder:32b-fp16` |

### Llama Stack on OpenShift — What You Get

When provisioned from the RHDP catalog (`sandboxes-gpte.llamastack-on-ocp.prod`):

| Component | Detail |
|---|---|
| OpenShift | 4.18 |
| RHOAI | Red Hat OpenShift AI with workbench |
| vLLM (on-cluster) | IBM Granite 3.2 8B Instruct |
| vLLM (remote) | Meta Llama 3.2 3B Instruct |
| Llama Stack | Agent framework with tool-calling, RAG, MCP |
| MCP Servers | OpenShift MCP, Slack MCP |
| Workbench | Jupyter notebooks (Levels 0–6) in `llama-serve` project |
| Deploy Time | ~90 minutes |

The vLLM model server exposes an OpenAI-compatible `/v1/chat/completions`
endpoint with tool-calling (function-calling) support — exactly what the
SprintWeave pipeline requires.

#### Live Demo Showroom

When the environment is provisioned, a Showroom lab guide is available at:

```
https://showroom-showroom-<cluster-id>.apps.<cluster>.<sandbox>.opentlc.com/
```

The showroom provides a split-pane interface (documentation + embedded
terminal) and a series of progressive Jupyter notebooks:

| Level | Title | Scope |
|-------|-------|-------|
| 0 | Environment Setup | Verify RHOAI workbench connectivity |
| 1 | Simple RAG | Document ingestion, FAISS vector DB, `all-MiniLM-L6-v2` embeddings |
| 2 | Simple Agent + Web Search | Agent with Tavily web search tool |
| 3 | Advanced Agents — Prompt Chaining & ReAct | Location awareness, ReAct pattern for complex reasoning |
| 4 | RAG Agent | RAG integrated as a tool in the agent's decision loop |
| 5 | Agents + MCP | OpenShift MCP (pod status, logs) + Slack MCP (post messages) |
| 6 | Agents + MCP + RAG | Full automated incident response system |

#### Llama Stack Built-in Tools

The Llama Stack server deployed in the environment provides:

| Tool | Description |
|------|-------------|
| **RAG** | Document ingestion + semantic search (FAISS / Milvus), embeddings via `all-MiniLM-L6-v2` |
| **WebSearch** | Real-time web queries via Tavily Search API |

#### MCP Servers (Pre-deployed)

| Server | Capabilities |
|--------|-------------|
| **OpenShift MCP** | Manage pods, view logs, list namespaces, install Helm charts — no kubectl needed |
| **Slack MCP** | List channels, post messages, reply to threads, add reactions, retrieve history |

> **Note:** SprintWeave currently uses only the vLLM inference endpoint.
> The Llama Stack agent framework, RAG tools, and MCP servers are available
> in the environment for exploration and future integration.

---

## Ollama — Local GPU (No API Key)

Runs models locally on your GPU using Ollama. Self-contained — no cloud
dependency, no API key, no network required.

### Quick Start

```powershell
# 1. Install Ollama: https://ollama.com/download
# 2. Pull a model
ollama pull qwen2.5-coder:14b

# 3. Run
pip install openai pyyaml
python agents\ollama\run_pipeline.py

# Or use the helper
.\agents\ollama\run-agents.ps1 local
.\agents\ollama\run-agents.ps1 local -Pipeline rda
.\agents\ollama\run-agents.ps1 local -Model qwen2.5-coder:7b
```

### Containerized (Docker + GPU)

```powershell
.\agents\ollama\run-agents.ps1 build
.\agents\ollama\run-agents.ps1 run            # Requires --gpus all (NVIDIA)
```

### Model Recommendations by VRAM

| VRAM | Recommended Model | Quality |
|---|---|---|
| 8 GB | `qwen2.5-coder:7b` | Good |
| 16 GB | `qwen2.5-coder:14b` (recommended) | Very Good |
| 24 GB | `qwen2.5-coder:32b` (best quality) | Excellent |
| 48 GB | `qwen2.5-coder:32b-instruct-fp16` | Best |

### Compatible APIs

The Ollama pipeline runner (`ollama/run_pipeline.py`) is the shared backend
for both Ollama and RHOAI. It works with any OpenAI-compatible API:

| API | Endpoint | Notes |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | Default |
| vLLM | `http://localhost:8000/v1` | Used by RHOAI |
| LM Studio | `http://localhost:1234/v1` | |
| text-gen-webui | `http://localhost:5000/v1` | |
| OpenRouter | `https://openrouter.ai/api/v1` | Requires `--api-key` |

---

## Cursor SDK — Cloud (Requires API Key)

Uses the Cursor SDK to run agents via cloud-hosted models (Claude, GPT,
Gemini). Highest quality output but requires a Cursor subscription and
API key.

### Quick Start

```powershell
$env:CURSOR_API_KEY = "cursor_..."
pip install cursor-sdk

# Full pipeline
python agents\cursor\run_pipeline.py

# Or use the helper
.\agents\cursor\run-agents.ps1 local
.\agents\cursor\run-agents.ps1 local -Pipeline rda
```

### Containerized

```powershell
.\agents\cursor\run-agents.ps1 build
.\agents\cursor\run-agents.ps1 run
```

---

## Pipelines

All three runners execute the same pipelines:

| Pipeline | Stages | Description |
|----------|--------|-------------|
| `rhoso-delivery` | RDA-1 → RDA-2 → RDA-3 → RDE-1 → RDE-2 → RDE-3 → RDE-4 | RHOSO full end-to-end (7 stages) |
| `ocp-delivery` | ODA-1 → ODA-2 → ODA-3 → ODE-1 → ODE-2 → ODE-3 → ODE-4 | OCP full end-to-end (7 stages) |
| `full-delivery` | RDA-1..3 → RDE-1..4 → ODA-1..3 → ODE-1..4 | RHOSO + OCP combined (14 stages) |
| `rda` | RDA-1 → RDA-2 → RDA-3 | RHOSO CIQ schema + generator + workbooks (3 stages) |
| `rde` | RDE-1 → RDE-2 → RDE-3 → RDE-4 | RHOSO CPAT code only (4 stages) |
| `oda` | ODA-1 → ODA-2 → ODA-3 | OCP CIQ schema + generator + workbooks (3 stages) |
| `ode` | ODE-1 → ODE-2 → ODE-3 → ODE-4 | OCP CPAT code only (4 stages) |

Individual stages: `RDA-1`/`ODA-1` (Schema), `RDA-2`/`ODA-2` (Generator), `RDA-3`/`ODA-3` (Workbooks/shell), `RDE-1`/`ODE-1` (Ansible), `RDE-2`/`ODE-2` (Backend), `RDE-3`/`ODE-3` (Frontend), `RDE-4`/`ODE-4` (Docker)

### RHOSO Pipeline Output (Schema v1.4)

| Stage | Sub-stage | Generates | LLM? |
|-------|-----------|-----------|------|
| RDA-1 | Schema | `output/ciq-generators/rhoso_ciq_schema.py` (18 tables, 203 params, 38 validators) | Yes |
| RDA-2 | Generator | `output/ciq-generators/generate_rhoso_ciq_workbooks.py` + `requirements.txt` (9-sheet workbook, 14 cond. format rules) | Yes |
| RDA-3 | Workbooks | `output/ciq-workbooks/rhoso/` sample + template `.xlsx` (9 sheets each) | **No** — shell only |
| RDE-1 | Ansible | `output/cpat/ansible/` 25 tasks in 9 subdirs, 19 templates, ~170 defaults | Yes |
| RDE-2 | Backend | `output/cpat/backend/` Flask API (19 task tags), CIQ parser (18 tables) | Yes |
| RDE-3 | Frontend | `output/cpat/frontend/` React UI, 11 components, 19 deploy tasks | Yes |
| RDE-4 | Docker | `output/cpat/Dockerfile`, `bringup.sh`, `USAGE.md` | Yes |

### OCP Pipeline Output (Schema v1.1)

| Stage | Sub-stage | Generates | LLM? |
|-------|-----------|-----------|------|
| ODA-1 | Schema | `output/ciq-generators/ocp_ciq_schema.py` (14 param-tables, 4 row-tables, 129+48=177 fields, 54 CIQ_TYPES) | Yes |
| ODA-2 | Generator | `output/ciq-generators/generate_ocp_ciq_workbooks.py` + `requirements.txt` (10-sheet workbook, 18 Excel tables) | Yes |
| ODA-3 | Workbooks | `output/ciq-workbooks/ocp/` sample + template `.xlsx` (10 sheets each) | **No** — shell only |
| ODE-1 | Ansible | `output/cpat/ansible/playbooks/roles/ocp/` 26 tasks in 10 subdirs, 12 templates + `ocp_validate.yml` + `module_utils/ocp_ciq_schema.py` | Yes |
| ODE-2 | Backend | `output/cpat/backend/ciq_parser.py` (unified) + `ocp_ciq_schema.py` (COPY — no generator) | Yes |
| ODE-3 | Frontend | `output/cpat/frontend/src/components/OcpDeploymentAutomation.jsx` | Yes |
| ODE-4 | Docker | `output/cpat/Dockerfile`, `bringup.sh`, `USAGE.md` | Yes |

### Schema v1.4 — New Capabilities (Sep 2026)

| Capability | CIQ Table | Params | Templates | Tasks | Source |
|---|---|---|---|---|---|
| **Trident/NetApp CSI** | `rhoso_trident_storage` | 12 | `openstack_trident.yaml.j2` | `trident_storage_configuration.yml` | JIO `D1.3_NetApp/` |
| **Local Storage Operator** | `rhoso_lso_storage` | 7 | `openstack_lso.yaml.j2` | Added to `prerequisite_operator_installation.yml` | JIO `D0.6_LSO/` |
| **Observability Operator** | `rhoso_observability` | 5 | `openstack_observability_operator.yaml.j2` | `observability_configuration.yml` | JIO `D0.5_ObservabilityOperator/` |
| **Multipath Config** | `rhoso_multipath` | 4 | `openstack_multipath_config.yaml.j2` | In storage config | JIO `D1.3_NetApp/multi-path-config.conf` |

**v1.3 → v1.4 delta:** 175 → 203 params (+28) | 15 → 19 templates (+4) | 21 → 25 tasks (+4) | 8 → 9 workbook sheets (+Operators) | 15 → 18 CIQ tables (+3)

## Choosing a Runner

```
Need enterprise/team demo?  ──→  RHOAI   (agents/rhoai/)
Have a local GPU?           ──→  Ollama  (agents/ollama/)
Want best quality?          ──→  Cursor  (agents/cursor/)
Air-gapped environment?     ──→  RHOAI or Ollama
No GPU available?           ──→  Cursor
```

---

## Verified Walkthrough (Sep 23, 2026)

The RHOAI runner was tested end-to-end against a live **Llama Stack on
OpenShift** environment provisioned from the RHDP catalog.

### Cluster Login

```console
$ oc login --token=sha256~xxxxx --server=https://api.cluster-m8gk6.m8gk6.sandbox499.opentlc.com:6443 --insecure-skip-tls-verify

Logged into "https://api.cluster-m8gk6.m8gk6.sandbox499.opentlc.com:6443" as "admin" using the token provided.
You have access to 91 projects, the list has been suppressed.
Using project "default".
```

### Discover (auto-detect vLLM endpoint)

PowerShell:
```console
PS> .\agents\rhoai\run-agents.ps1 discover

Auto-discovering vLLM endpoint from OCP cluster...
Discovered: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
vLLM Endpoint: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1

Set it permanently:
  $env:RHOAI_API_BASE = "https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1"
```

Bash:
```console
$ sh run-agents.sh discover

Auto-discovering vLLM endpoint from OCP cluster...
Discovered: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1

vLLM Endpoint: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1

Set it permanently:
  export RHOAI_API_BASE="https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1"
```

### Test (list models + inference)

PowerShell:
```console
PS> .\agents\rhoai\run-agents.ps1 test

Auto-discovering vLLM endpoint from OCP cluster...
Discovered: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
Testing connection to RHOAI...
  Endpoint: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
  Model:    granite32-8b

Listing available models...
Available models:
  - granite32-8b

Testing inference...
  Model responded: Hello.
Inference working! Ready for SprintWeave pipeline.
```

Bash:
```console
$ sh run-agents.sh test

Auto-discovering vLLM endpoint from OCP cluster...
Discovered: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
Testing connection to RHOAI...
  Endpoint: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
  Model:    granite32-8b

Listing available models...
Connection successful (raw model data in response)
Testing inference (simple completion)...
Inference working! (response received)
```

### Cluster Routes Discovered

The auto-discovery found the vLLM model server route in the `istio-system`
namespace (KServe/Istio managed), not in `llama-serve` directly:

```console
$ oc get routes -n istio-system -o custom-columns="NAME:.metadata.name,HOST:.spec.host"

NAME                                                      HOST
granite32-8b-llama-serve                                  granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com
route-4ced5cb9-a5fb-4fb1-9630-c89756653139-356639616633   granite32-8b-predictor-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com
```

Other routes in `llama-serve` namespace (not vLLM — workbench, Llama Stack server, Streamlit UI):

```console
$ oc get routes -n llama-serve -o custom-columns="NAME:.metadata.name,HOST:.spec.host,SERVICE:.spec.to.name"

NAME                HOST                                                                            SERVICE
lab                 lab-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com                 lab-tls
llamastack-server   llamastack-server-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com   llamastack-server
streamlit           streamlit-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com           proxy
```

### Raw vLLM API Response

```console
$ curl -sk https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1/models \
    -H "Authorization: Bearer $(oc whoami -t)"

{"object":"list","data":[{"id":"granite32-8b","object":"model","created":1790161434,
"owned_by":"vllm","root":"/mnt/models","parent":null,"max_model_len":120000,...}]}
```

```console
$ curl -sk https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1/chat/completions \
    -H "Authorization: Bearer $(oc whoami -t)" \
    -H "Content-Type: application/json" \
    -d '{"model":"granite32-8b","messages":[{"role":"user","content":"Say hello in one word."}],"max_tokens":10}'

{"id":"chatcmpl-dc6dc733-...","object":"chat.completion","model":"granite32-8b",
"choices":[{"index":0,"message":{"role":"assistant","content":"Hello."},...}],
"usage":{"prompt_tokens":14,"total_tokens":17,"completion_tokens":3}}
```

### Pipeline Run — RDA on Granite 3.2 8B

```console
$ sh run-agents.sh run --pipeline rda

============================================================
CPAT Pipeline (Open-Source): rda — 1 stage(s)
Model:    granite32-8b
API Base: https://granite32-8b-llama-serve.apps.cluster-m8gk6.m8gk6.sandbox499.opentlc.com/v1
============================================================

[1/1] Stage: RDA
  [RDA] Iteration 1/40... text-only response, nudging to use tools (retry 1/2)
  [RDA] Iteration 2/40... text-only response, nudging to use tools (retry 2/2)
  [RDA] Iteration 3/40... done (no more tool calls)

⚠️ [RDA] Done in 59s — 0 verified, 2 missing
```

**Finding:** Granite 3.2 8B supports tool-calling for simple tasks (verified
with single-tool test) but cannot handle the full RDA code-generation pipeline.
The model describes tool calls in text/JSON instead of invoking the function-
calling protocol — a common limitation of 8B-parameter models with complex
multi-step prompts.

| Capability | Granite 3.2 8B | Minimum Recommended |
|---|---|---|
| Simple inference | ✅ Works | — |
| Single tool call | ✅ Works | — |
| Multi-step tool-calling pipeline | ❌ Text-only | 14B+ (qwen2.5-coder:14b) |
| Full RDA code generation (203 params, v1.4) | ❌ Abbreviated | 32B+ or Claude/GPT |

**Recommended runners for the full SprintWeave pipeline:**

| Runner | Model | Pipeline Support |
|--------|-------|-----------------|
| Cursor SDK | Claude / GPT | ✅ Full pipeline |
| Ollama (16+ GB VRAM) | qwen2.5-coder:14b | ✅ Full pipeline |
| Ollama (24+ GB VRAM) | qwen2.5-coder:32b | ✅ Full pipeline (best open-source) |
| RHOAI (Granite 8B) | granite32-8b | ⚠️ Simple tasks, demos, testing only |

---

## Agent Definitions (v1.4 RHOSO + v1.1 OCP)

The SprintWeave pipeline is driven by **5 agent rule files** in `.cursor/rules/`.
Each rule is loaded as a system prompt that tells the LLM how to behave at
each pipeline stage. When running outside Cursor (RHOAI/Ollama), these rules
are read from `context/pipelines.yaml` and injected as system messages.

| Agent | File | Pipelines |
|-------|------|-----------|
| Orchestrator | `agent-orchestrator.md` | All (coordinator) |
| RHOSO DA (RDA) | `agent-rhoso-da.md` | rhoso-delivery, rhoso-da, full-delivery |
| RHOSO DE (RDE) | `agent-rhoso-deployment-engineer.md` | rhoso-delivery, rhoso-de, full-delivery |
| OCP DA (ODA) | `agent-ocp-da.md` | ocp-delivery, ocp-da, full-delivery |
| OCP DE (ODE) | `agent-ocp-deployment-engineer.md` | ocp-delivery, ocp-de, full-delivery |

### Orchestrator (`agent-orchestrator.md`)

| Attribute | Value |
|---|---|
| **File** | `.cursor/rules/agent-orchestrator.md` |
| **Size** | 140 lines, ~1.3K tokens |
| **Role** | Pipeline coordinator — reads `context/pipelines.yaml`, matches user prompt to pipeline, sequences 7 stages (RDA-1/2/3 + RDE-1/2/3/4), reports progress |
| **Triggers** | "Run RHOSO delivery pipeline", "Run RHOSO DA pipeline", "Run RHOSO DE pipeline" |
| **Generates** | Nothing directly — delegates to RDA and RDE agents |
| **Updated** | **Sep 30, 2026** — Updated from 5 → 7 stages. RDA split into RDA-1 (Schema), RDA-2 (Generator), RDA-3 (Workbooks/shell). |

### RHOSO DA — Design Architect (`agent-rhoso-da.md`)

| Attribute | Value |
|---|---|
| **File** | `.cursor/rules/agent-rhoso-da.md` |
| **Size** | 310 lines, ~4.2K tokens |
| **Role** | Generates CIQ schema code, workbook generator scripts, and Excel workbooks. Now runs in **3 sub-stages** for improved reliability. |
| **Sub-stages** | **RDA-1** (Schema) → **RDA-2** (Generator) → **RDA-3** (Workbooks — shell, no LLM) |
| **Triggers** | "Generate CIQ", "CIQ workbook", "CIQ schema code" |
| **Schema** | **v1.4 — 18 tables, 203 parameters** |
| **Updated** | **Sep 30, 2026** — Split into 3 sub-stages. Added 4 new tables: `rhoso_trident_storage` (12), `rhoso_lso_storage` (7), `rhoso_observability` (5), `rhoso_multipath` (4). Updated `rhoso_services` to 44 params. Storage sheet includes 6 tables. New 9th Operators sheet. |

**RDA Sub-Stages:**

| Sub-stage | Generates | LLM? | Depends on |
|---|---|---|---|
| **RDA-1 Schema** | `rhoso_ciq_schema.py` (~1,200 lines) — 18 tables, 203 params, 38 CIQ_TYPES | Yes | Input docs + project artifacts |
| **RDA-2 Generator** | `generate_rhoso_ciq_workbooks.py` (~1,450 lines) + `requirements.txt` | Yes | Reads schema from RDA-1 |
| **RDA-3 Workbooks** | `sample-rhoso.ciq.xlsx` + `rhoso-ciq-template.xlsx` (9 sheets) | **No** — shell execution | Runs RDA-2 generator script |

**CIQ Tables (v1.4):**

| Table | Params | Content |
|-------|--------|---------|
| `rhoso_details` | 11 | Cluster, version, deployment mode, FIPS |
| `rhoso_access` | 3 | Kubeconfig, API URL, pull secret |
| `rhoso_disconnected` | 16 | Mirror registry, IDMS/ITMS, catalog sources |
| `rhoso_storage` | 2 | Storage class, backend |
| `rhoso_ceph_storage` | 12 | Ceph external, FSID, mon host, pools, RGW |
| `rhoso_trident_storage` | 12 | **NEW** — Trident CSI: image registry, backend, driver, LIFs, SVM |
| `rhoso_lso_storage` | 7 | **NEW** — LSO: storage class, device types, volume mode |
| `rhoso_control_plane` | 29 | VIPs, DNS, TLS, operator channel, messaging bus |
| `rhoso_services` | 44 | Service enable flags, HA operators, **LSO/Observability/Trident flags** |
| `rhoso_observability` | 5 | **NEW** — COO: channel, approval, monitoring stack |
| `rhoso_pv_sizing` | 10 | Galera, OVN, Glance, Telemetry storage |
| `rhoso_cinder_backend` | 8 | NetApp driver, protocol, vserver |
| `rhoso_multipath` | 4 | **NEW** — Multipath: enabled, secret, config |
| `rhoso_neutron_config` | 5 | MTU, API timeout, OVN, MAC binding |
| `rhoso_edpm_network_config` | 24 | Bridge, topology, bonding, DPDK, tuning |
| `rhoso_data_plane` | 14 | NodeSet, provisioning mode, SSH, secrets |
| `rhoso_networks` | 16 cols | Network rows (CIDR, VLAN, gateway, allocations) |
| `rhoso_data_plane_nodes` | 16 cols | Node rows (BMC, MACs, CPU pinning, boot mode) |

### RHOSO Deployment Engineer (`agent-rhoso-deployment-engineer.md`)

| Attribute | Value |
|---|---|
| **File** | `.cursor/rules/agent-rhoso-deployment-engineer.md` |
| **Size** | 343 lines, ~4K tokens |
| **Role** | Generates full CPAT source code in 4 sub-stages (Ansible, Backend, Frontend, Docker) |
| **Triggers** | "Scaffold CPAT", "generate CPAT", "add Ansible task" |
| **Updated** | **Oct 5, 2026** — Tasks reorganized into 9 functional subdirectories. 19 templates, 25 tasks, ~170 defaults. |

**Ansible Task Subdirectories (v1.4):**

| Subdirectory | Files | Purpose |
|---|---|---|
| `common/` | 3 | CIQ loading (`_load_ciq_context`), validation, CRD checks |
| `prerequisites/` | 3 | Pre-deploy checks, operator installation, disconnected prep |
| `secrets/` | 3 | OSP secret, DP secrets, Ceph secret generation |
| `storage/` | 3 | Persistent storage, Trident CSI, storage CR rendering |
| `network/` | 1 | NNCP, NAD, MetalLB, NetConfig preparation |
| `control_plane/` | 5 | OpenStack operator install, RHOCP prep, CP deploy/customize, CP CRs |
| `data_plane/` | 2 | NodeSet + Deployment CRs, DP deploy |
| `post_deployment/` | 2 | Validation, observability configuration |
| `manifests/` | 2 | Generate-for-review mode, disconnected CRs |

**v1.4 Changes:**

| Component | v1.3 | v1.4 | New additions |
|---|---|---|---|
| **Jinja Templates** | 15 | **19** | `openstack_lso.yaml.j2`, `openstack_observability_operator.yaml.j2`, `openstack_trident.yaml.j2`, `openstack_multipath_config.yaml.j2` |
| **Ansible Tasks** | 21 (flat) | **25 (9 subdirs)** | `trident_storage_configuration.yml`, `_generate_storage_crs.yml`, `observability_configuration.yml`, plus updated `prerequisite_operator_installation.yml` |
| **Defaults** | ~140 | **~170** | 30 new `rhoso_` variables for Trident, LSO, Observability, Multipath |
| **Backend Task Tags** | 16 | **19** | Tags now use subdirectory paths (e.g. `storage/trident_storage_configuration`) |
| **Frontend Deploy Tasks** | 16 | **19** | Matching backend task tags |
| **CIQ Parser Tables** | 12 supplemental | **15** | `rhoso_trident_storage`, `rhoso_lso_storage`, `rhoso_observability`, `rhoso_multipath` |

### OCP DA — Design Architect (`agent-ocp-da.md`)

| Attribute | Value |
|---|---|
| **File** | `.cursor/rules/agent-ocp-da.md` |
| **Size** | ~200 lines, ~3.5K tokens |
| **Role** | Generates OCP CIQ schema code, workbook generator scripts, and Excel workbooks. Runs in **3 sub-stages** mirroring RDA. |
| **Sub-stages** | **ODA-1** (Schema) → **ODA-2** (Generator) → **ODA-3** (Workbooks — shell, no LLM) |
| **Triggers** | "OCP CIQ", "OCP schema", "OCP workbook", "ODA" |
| **Schema** | **v1.1 — 14 param-tables (129 params) + 4 row-tables (48 cols) = 177 total fields, 54 CIQ_TYPES** |
| **Install Methods** | ABI, IPI-BM, UPI-BM, ABI-DC, SNO |
| **Updated** | **Oct 6, 2026** — Schema v1.0→v1.1. `ocp_cluster_details` 14→15 params (added CPU Partitioning Mode). `ocp_bastion` 8→9 params (added Bastion DNS). Networking before Proxy in table order. Generator exports `generate_ocp_ciq_workbook(values, output_path)` public API for env-specific workbooks (used by Troshka). Standalone generator is single source of truth — no generator in `cpat/backend/`. |

**ODA Sub-Stages:**

| Sub-stage | Generates | LLM? | Depends on |
|---|---|---|---|
| **ODA-1 Schema** | `ocp_ciq_schema.py` (~970 lines) — 14 param-tables, 4 row-tables, 54 CIQ_TYPES | Yes | OCP input docs (21 files) |
| **ODA-2 Generator** | `generate_ocp_ciq_workbooks.py` (~1,270 lines) + `requirements.txt` | Yes | Reads schema from ODA-1 |
| **ODA-3 Workbooks** | `sample-ocp.ciq.xlsx` + `ocp-ciq-template.xlsx` (10 sheets, 18 Excel tables) | **No** — shell execution | Runs ODA-2 generator script |

**Generator Public API (v1.1):**

| Function | Purpose |
|---|---|
| `generate_workbook(fill_sample=False)` → `Workbook` | Returns template or sample workbook (in-memory) |
| `generate_ocp_ciq_workbook(values=None, output_path="ocp-ciq-template.xlsx")` → `str` | Generates env-specific workbook from values dict, saves to path. Used by Troshka. |

**Schema Architecture (single source of truth):**

| Location | File | Role |
|---|---|---|
| `output/ciq-generators/ocp_ciq_schema.py` | **MASTER** | Standalone schema with own `CIQ_TYPES` dict (54 types). No external deps. |
| `output/cpat/backend/ocp_ciq_schema.py` | **COPY** | Imports `CIQ_TYPES` from `rhoso_ciq_schema`, adds OCP-specific types. Used by parser. |
| `output/cpat/ansible/module_utils/ocp_ciq_schema.py` | **COPY** | Same as backend but `from ansible.module_utils.rhoso_ciq_schema import CIQ_TYPES`. |

**OCP CIQ Param Tables (v1.1 — 14 tables, 129 params):**

| Table | Params | Content |
|-------|--------|---------|
| `ocp_cluster_details` | 15 | Cluster name, base domain, version, install method, platform, FIPS, CPU partitioning |
| `ocp_access` | 4 | Pull secret, SSH key, kubeconfig, credentials mode |
| `ocp_networking` | 12 | Cluster/service/machine CIDRs, OVN, dual-stack |
| `ocp_proxy` | 5 | HTTP/HTTPS proxy, no_proxy |
| `ocp_platform_baremetal` | 12 | API/Ingress VIP, provisioning network, DHCP range |
| `ocp_agent_config` | 10 | Rendezvous IP, NTP, trust bundle, proxy |
| `ocp_disconnected` | 14 | Mirror registry, IDMS/ITMS, image content sources |
| `ocp_mirror_registry` | 8 | Quay hostname, TLS, storage backend |
| `ocp_bastion` | 9 | Bastion host, DNS, disk, services |
| `ocp_load_balancer` | 8 | HAProxy/MetalLB, API/Ingress ports |
| `ocp_certificates` | 6 | API cert, wildcard cert, CA bundle |
| `ocp_storage` | 8 | Default StorageClass, CSI, LSO, ODF |
| `ocp_day2_operators` | 12 | NMState, MetalLB, SR-IOV, Multus, LSO, ODF, MCE |
| `ocp_ingress` | 6 | Ingress controller, wildcard, load balancer |

**OCP CIQ Row Tables (v1.1 — 4 tables, 48 cols):**

| Table | Cols | Content |
|-------|------|---------|
| `ocp_bmc_hosts` | 14 | BMC address, boot MAC, role, root device hint |
| `ocp_nmstate_interfaces` | 12 | Per-host NMState: ethernet/bond/VLAN configs |
| `ocp_compute_nodes` | 14 | Node hardware specs, MACs, labels |
| `ocp_dns_records` | 8 | api, api-int, *.apps, node DNS records |

**Workbook Sheets (v1.1 — 10 sheets):**

| # | Sheet | Tables |
|---|-------|--------|
| 1 | Versioning | Document metadata, sheet index, version history |
| 2 | Environment | ocp_cluster_details, ocp_access, ocp_proxy, ocp_disconnected, ocp_mirror_registry |
| 3 | Platform | ocp_platform_baremetal, ocp_agent_config, ocp_bastion, ocp_load_balancer |
| 4 | Networking | ocp_networking, ocp_certificates, ocp_ingress |
| 5 | Storage & Operators | ocp_storage, ocp_day2_operators |
| 6 | Nodes | ocp_bmc_hosts, ocp_nmstate_interfaces, ocp_compute_nodes (row tables) |
| 7 | DNS Records | ocp_dns_records (row table) |
| 8 | values | Hidden — dropdown lists (Name Manager named ranges) |
| 9 | Guidelines | Parameter catalog with types, conditions, descriptions |
| 10 | Operators | Day-2 operator reference |

**v1.0 → v1.1 delta:** ~180 → 177 total fields (restructured) | 8 → 10 sheets (+values, +Operators) | ~30 → 54 CIQ_TYPES | 0 → 18 Excel tables | Added DataValidation dropdowns, conditional formatting, named ranges | Generator now exports `generate_ocp_ciq_workbook()` public API

### OCP Deployment Engineer (`agent-ocp-deployment-engineer.md`)

| Attribute | Value |
|---|---|
| **File** | `.cursor/rules/agent-ocp-deployment-engineer.md` |
| **Size** | ~280 lines, ~3.5K tokens |
| **Role** | Generates CPAT OCP source code in 4 sub-stages (Ansible, Backend, Frontend, Docker) |
| **Triggers** | "ODE", "OCP Ansible", "OCP backend", "OCP frontend" |
| **Updated** | **Oct 6, 2026** — Backend no longer generates `ocp_ciq_generator.py` (generation is ODA-only at `ciq-generators/`). Backend generates `ocp_ciq_schema.py` (COPY synced from standalone master). Ansible generates `ocp_ciq_schema.py` in `module_utils/` (COPY with Ansible import paths). Frontend component renamed to `OcpDeploymentAutomation.jsx`. Added `ocp_validate.yml` playbook. 26 tasks in 10 subdirs, 12 templates. |

**ODE Sub-Stages:**

| Sub-stage | Generates | LLM? | Depends on |
|---|---|---|---|
| **ODE-1 Ansible** | `ansible/playbooks/roles/ocp/` (26 tasks, 10 subdirs), `ocp_validate.yml`, `ansible/module_utils/ocp_ciq_schema.py` | Yes | ODA-1 schema |
| **ODE-2 Backend** | `backend/ciq_parser.py` (unified RHOSO+OCP), `backend/ocp_ciq_schema.py` (COPY — no generator) | Yes | ODA-1 schema |
| **ODE-3 Frontend** | `frontend/src/components/OcpDeploymentAutomation.jsx` | Yes | ODE-2 backend API |
| **ODE-4 Docker** | `Dockerfile`, `bringup.sh`, `USAGE.md` | Yes | Full CPAT layout |

**OCP Ansible Task Subdirectories (26 tasks, 10 subdirs):**

| Subdirectory | Files | Purpose |
|---|---|---|
| `common/` | 3 | CIQ loading (`_load_ciq_context`), validation (`_validate_ciq`), prerequisite checks (`_verify_prerequisites`) |
| `prerequisites/` | 3 | Bastion prep, DNS/DHCP validation, NTP sync |
| `mirror/` | 3 | Quay mirror-registry install, oc-mirror, IDMS/ITMS |
| `install_config/` | 3 | install-config.yaml, agent-config.yaml, NMState configs |
| `ignition/` | 2 | Ignition configs (UPI), agent ISO (ABI) |
| `bootstrap/` | 2 | Bootstrap cluster, wait for bootstrap-complete |
| `cluster_config/` | 3 | CSR approval, authentication, day-2 operators |
| `network/` | 2 | MetalLB, SR-IOV/Multus post-install |
| `validation/` | 2 | Cluster health check, node readiness |
| `manifests/` | 2 | Generate-for-review mode, disconnected CRs |

**Templates (12):** `ocp_install_config.yaml.j2`, `ocp_agent_config.yaml.j2`, `ocp_nmstate_config.yaml.j2`, `ocp_platform_baremetal.yaml.j2`, `ocp_image_content_source.yaml.j2`, `ocp_catalog_source.yaml.j2`, `ocp_chrony_config.j2`, `ocp_haproxy_config.j2`, `ocp_dns_records.j2`, `ocp_day2_operator_sub.yaml.j2`, `ocp_sno_install_config.yaml.j2`, `ocp_mirror_imageset.yaml.j2`

**Backend Architecture (v1.1 — parse + validate only, no generation):**

| File | Role |
|---|---|
| `ciq_parser.py` | Unified parser — parses RHOSO+OCP CIQ `.xlsx` into Ansible-compatible dict |
| `ocp_ciq_schema.py` | Schema COPY (synced from `ciq-generators/` master). Imports `CIQ_TYPES` from `rhoso_ciq_schema`. |
| ~~`ocp_ciq_generator.py`~~ | **DELETED** — CIQ generation is ODA-only at `ciq-generators/`. Troshka imports directly from standalone. |

### Context Files

| File | Purpose | Updated |
|---|---|---|
| `context/pipelines.yaml` | Pipeline stage definitions — RHOSO (RDA-1/2/3, RDE-1/2/3/4) + OCP (ODA-1/2/3, ODE-1/2/3/4) + Full (14 stages). Schema sync note: `ciq-generators/` is single source of truth, no generator in `cpat/backend/`. | **Oct 6, 2026** — ODE stages updated: `ocp_ciq_schema.py` synced copies in Ansible+Backend, frontend→`OcpDeploymentAutomation.jsx`, added `ocp_validate.yml` |
| `context/templates/rhoso-deployment-engineer.md` | Extended context with code patterns, file blueprints | Contains full CPAT project blueprint |

### Input Files (Source Material)

| Directory | Files | Content | Coverage |
|---|---|---|---|
| `input/rhoso/docs/` | 9 PDFs | RHOSO 18.0 Plan, Install, Customizing, Storage, Disconnected, Multi-env, Validation | Schema v1.3 params |
| `input/rhoso/project-artifacts/jio/` | 114 files | JIO cloudmgmt + cloudxp deployment YAMLs | **v1.4: LSO, Observability, Trident, Multipath** |
| `input/rhoso/project-artifacts/core42/` | 16 files | Core42 HLDs (.docx), workshops (.pptx) | Partial (RHOSO HLD) |
| `input/ocp/docs/` | **21 files** | OCP 4.17–4.20 — Agent-based installer, bare metal, disconnected, storage, networking, edge, architecture, bastion prep, Quay mirror registry, blueprint xlsx | **Full OCP CIQ coverage** |

---

## Next Steps

### 1. Run SprintWeave Against Live RHOAI

```powershell
# RDA only — fastest validation (~5 min)
.\agents\rhoai\run-agents.ps1 run -Pipeline rda

# Full pipeline — end-to-end (~15-30 min)
.\agents\rhoai\run-agents.ps1 run

# Try Llama 3.2 3B for comparison
.\agents\rhoai\run-agents.ps1 run -Pipeline rda -Model "meta-llama/Llama-3.2-3B-Instruct"
```

### 2. Compare Output Quality Across Runners

Run the same pipeline on all three backends and compare output:

| Runner | Command | Expected Quality |
|--------|---------|-----------------|
| RHOAI (Granite 8B) | `.\agents\rhoai\run-agents.ps1 run` | Good |
| RHOAI (Llama 3.2 3B) | `.\agents\rhoai\run-agents.ps1 run -Model meta-llama/Llama-3.2-3B-Instruct` | Fair |
| Ollama (qwen2.5-coder:14b) | `.\agents\ollama\run-agents.ps1 local` | Very Good |
| Cursor SDK (Claude) | `.\agents\cursor\run-agents.ps1 local` | Excellent |

### 3. Explore the Lab Notebooks

Open the RHOAI workbench in the `llama-serve` project and walk through
Levels 0–6 to understand Llama Stack capabilities (RAG, agents, MCP)
that could enhance the SprintWeave pipeline.

### 4. Future Integration Opportunities

| Opportunity | Benefit | Effort |
|-------------|---------|--------|
| **Docling for PDF parsing** | Auto-extract CIQ params from RHOSO PDFs instead of hardcoding in agent rules. Makes schema updates automatic when Red Hat releases new versions. | Medium |
| **RAG for CIQ docs** | Feed customer CIQ documents into Llama Stack RAG so agents retrieve context automatically | Medium |
| **OpenShift MCP in RDE** | Let RDE agents verify deployments directly on the target cluster via MCP | Medium |
| **Slack MCP notifications** | Post pipeline progress and results to a team Slack channel | Low |
| **Llama Stack agents** | Replace raw chat completions with Llama Stack's agent framework for built-in tool-calling and ReAct | High |
| **Docling + RAG for model portability** | Slim agent rules to ~2K tokens (behavior only) + RAG for domain knowledge. Enables Granite 8B and Qwen 7B to run the pipeline. | High |
