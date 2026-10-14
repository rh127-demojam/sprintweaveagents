# CPAT Review Package — Folder Structure
> **Two-folder build**: `sprintweave-web/` (engine) + `cpat-main/` (agents)
> **No dependency** on `sprintweave-agents/` — `cpat-main` is fully self-contained.

---

## Quick Build

```bash
# One-time: build the Docling base image (heavy, slow)
podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/YOUR_ORG/sprintweave-docling-base:latest .

# Every change: build the app image
podman build -f Dockerfile \
  --build-arg BASE_IMAGE=quay.io/YOUR_ORG/sprintweave-docling-base:latest \
  --build-arg PIPELINES=rhoso,ocp \
  -t quay.io/YOUR_ORG/sprintweave-cpat:latest .
```

## Bastion → OpenShift Deploy (Recommended)

```bash
# From bastion node (has podman + oc logged in):
export REGISTRY=quay.io/YOUR_ORG
export LLM_API_KEY=sk-your-key-here

# Full pipeline: build → push → create namespace/secret → deploy
./bringup.sh deploy

# Or step-by-step:
./bringup.sh build          # build image locally
./bringup.sh push           # push to Quay
./bringup.sh setup          # create OCP namespace + secrets
./bringup.sh apply          # apply manifests + rollout

# After code changes — quick redeploy:
./bringup.sh build && ./bringup.sh push && ./bringup.sh apply

# Air-gapped (no Quay access from bastion):
./bringup.sh export         # save .tar
scp sprintweave-rhoso-*.tar cloud-user@bastion:~/
# On bastion: podman load -i sprintweave-rhoso-*.tar
```

The root `Dockerfile` copies `cpat-main/` → `/app/sprintweave-agents/` inside the
container so the engine discovers rules, skills, context, and `pipelines.yaml`
from the standard path.

---

## Folder Map

```
CFP_NEW/
├── Dockerfile                  ← simplified build (replaces Dockerfile.bundle)
├── bringup.sh                  ← bastion build + OCP deploy script
├── REVIEW.md                   ← this file
│
├── sprintweave-web/            ← RUNTIME ENGINE (unchanged)
│   ├── api/
│   │   ├── worker.py           — pipeline execution engine
│   │   ├── cpat_deploy.py      — OpenShift deploy logic
│   │   ├── custom_agents.py    — custom agent CRUD + pipeline gen
│   │   └── ...
│   ├── ui/                     — Streamlit web UI
│   ├── llm/                    — LLM client abstraction
│   ├── prompts/                — system prompts
│   ├── deploy/                 — Kubernetes manifests
│   ├── scripts/                — helper scripts
│   ├── Dockerfile.bundle       — (legacy, uses AGENTS_SRC arg)
│   ├── Dockerfile.docling-base — base image with Docling + deps
│   └── requirements.txt
│
└── cpat-main/                  ← AGENT CONFIG (self-contained)
    ├── .cursor/
    │   ├── rules/              — agent rules (LLM reads these)
    │   │   ├── 00-sprintweave-*.md    (8 platform rules)
    │   │   ├── agent-orchestrator.md
    │   │   ├── agent-rhoso-da.md
    │   │   ├── agent-rhoso-deployment-engineer.md
    │   │   ├── agent-ocp-da.md
    │   │   └── agent-ocp-deployment-engineer.md
    │   └── skills/             — pipeline/gate/setup skills
    │       ├── sprintweave-setup/SKILL.md
    │       ├── sprintweave-pipelines/SKILL.md
    │       ├── sprintweave-gates/SKILL.md
    │       └── sprintweave-custom-agent/SKILL.md
    │
    ├── context/
    │   ├── pipelines.yaml      — ALL pipeline definitions (v3)
    │   │   (7 pipelines: rhoso-delivery, rhoso-da, rhoso-de,
    │   │    ocp-delivery, ocp-da, ocp-de, full-delivery)
    │   ├── team-config.yaml    — team roles & permissions
    │   ├── nrho-contract.yaml  — NRHO contract schema
    │   ├── glossary*.yaml      — 4 glossary files
    │   └── templates/
    │       ├── rhoso-da.md               — RHOSO DA template
    │       ├── rhoso-deployment-engineer.md — RHOSO DE template
    │       └── nrho-cpat-container/      — reference Dockerfile patterns
    │           ├── Dockerfile
    │           ├── docker/entrypoint.sh
    │           ├── bringup.sh
    │           ├── .dockerignore
    │           └── README.md
    │
    ├── agents/                 — standalone pipeline runners
    │   ├── cursor/             — Cursor-based runner
    │   ├── ollama/             — local Ollama runner
    │   └── rhoai/              — RHOAI runner
    │
    ├── output/                 — golden baseline output (167 files)
    │   ├── cpat/
    │   │   ├── backend/        — Python API (app.py, models, parsers)
    │   │   ├── frontend/       — React UI (JSX components)
    │   │   ├── ansible/        — RHOSO + OCP playbooks & templates
    │   │   ├── aap/            — AAP export (EE, cred types, templates)
    │   │   ├── docker/         — entrypoint.sh
    │   │   ├── Dockerfile
    │   │   └── bringup.sh
    │   └── pipeline-reports/   — DA/DE stage reports
    │
    ├── tools/
    │   ├── cpat-dashboard.canvas.tsx
    │   └── pipelines-default.yaml
    │
    ├── README.md
    └── CATALOG.md
```

---

## How It Works at Runtime

1. **Engine starts** — `streamlit run ui/app.py` inside `sprintweave-web/`.
2. **Worker reads agents** — `worker.py` looks at `SPRINTWEAVE_AGENTS_DIR`
   (`/app/sprintweave-agents/` = `cpat-main/` at build time):
   - Loads `.cursor/rules/*.md` as agent system prompts.
   - Loads `.cursor/skills/*/SKILL.md` for pipeline/gate knowledge.
   - Copies `context/` into each job workspace (templates, glossaries, pipelines.yaml).
3. **Pipeline config** — `context/pipelines.yaml` declares every stage:
   ```yaml
   - abbrev: RDE-2
     agent: "RHOSO Deployment Engineer"
     sub_stage: "Backend"
     generates: ["output/cpat/backend/"]
     validators: [python_syntax, python_imports]
     layer: backend
   ```
4. **Generate → Validate → Fix loop** — For each sub-stage:
   - LLM generates code following agent rules.
   - `worker.py` runs validators (ast.parse, import resolution, JSX checks, etc.).
   - Errors are fed back to LLM for self-correction (up to 3 rounds).
5. **Deploy** — `cpat_deploy.py` reads `deploy_spec` from pipelines.yaml and
   pushes a binary build to OpenShift.

---

## Key Design Decisions

| Decision | Why |
|---|---|
| **No golden templates injected into workspace** | All code is AI-generated from scratch. Agent rules contain reference patterns the LLM reads as context. Colleagues can verify everything comes from the LLM. |
| **Data-driven pipelines** | Stages, validators, and deploy specs live in `pipelines.yaml`, not hardcoded in `worker.py`. Adding a new pipeline = adding YAML, not touching engine code. |
| **Validator registry** | Generic validators (python_syntax, python_imports, dockerfile, etc.) are mapped by name. Pipeline config declares which to run. No agent-specific `if/elif` chains. |
| **Reference patterns in agent rules** | Instead of bypassing the LLM with pre-baked files, Dockerfile/entrypoint patterns live inside the agent rule markdown. LLM reads them as context, generates from scratch, validate→fix loop catches deviations. |
| **OpenShift-safe defaults** | Port 8080, no chmod on mount root, nginx temp dirs under /tmp, random non-root UID support. All enforced by validators. |

---

## What Changed from sprintweave-agents

`cpat-main` absorbs only the **platform-level** pieces from `sprintweave-agents`:
- 8 platform rules (`00-sprintweave-*.md`) — security, grounding, gates, etc.
- 4 skills — setup, pipelines, gates, custom-agent.
- 4 glossary files — cloud, platform, generic, master.
- `nrho-contract.yaml` — RHOSO contract schema.

All generic agents (technical-writer, sre-engineer, sprint-coach, etc.) are
**NOT included** — only the 4 CPAT agents (RHOSO DA, RHOSO DE, OCP DA, OCP DE)
plus the orchestrator.

---

## Quality Improvements — Why RHOSO Code Will Be Better

The following changes directly improve the quality of LLM-generated code:

### 1. Validate → Fix Loop (Biggest Impact)
Each sub-stage now runs up to **3 rounds** of validation + LLM self-correction:
```
LLM generates code → validators run → errors fed back to LLM → LLM fixes → re-validate
```
**Validators** (from `pipelines.yaml` per stage):
| Validator | What it catches |
|---|---|
| `python_syntax` | `ast.parse` every `.py` — catches truncated functions, bad indentation, missing colons |
| `python_imports` | Resolves `from X import Y` across modules — catches missing symbols, circular imports |
| `frontend_jsx` | Brace/paren balance — catches truncated React components |
| `dockerfile` | ENTRYPOINT/CMD present, no `COPY 2>/dev/null`, EXPOSE correct |
| `entrypoint_sh` | `set -e` present, no fatal `chmod` on mount root |
| `nginx_conf` | Config exists, `listen 8080` (not 80) |
| `yaml_lint` | YAML syntax check on all `.yaml` files |

### 2. Higher Token Limits
| Setting | Old | New | Effect |
|---|---|---|---|
| `LLM_MAX_TOKENS` | 2048 | **32768** | LLM can write complete files without truncation |
| `AGENT_MAX_STEPS` | 60 | **80** | More iterations to get code right |
| `ANSIBLE_ROUND_STEPS` | 25 | **30** | More rounds for complex Ansible templates |
| `ANSIBLE_MAX_ROUNDS` | 12 | **15** | More passes on the Ansible sub-stage |
| `TOOL_RESULT_MAX` | 40000 | **60000** | LLM sees more context from file reads |
| `TEXT_MAX` | 60000 | **80000** | Larger input documents supported |
| `AGENT_PROMPT_MAX` | 12000 | **16000** | Longer agent rules with reference patterns |

### 3. Reference Patterns in Agent Rules
Instead of hardcoded sanitizers fixing broken code *after* generation, the agent
rules now contain **Dockerfile, entrypoint.sh, nginx.conf** reference patterns.
The LLM reads these patterns as context and generates OpenShift-safe code from
the start:
- Port 8080 (not 80)
- No `chmod` on mount root under `set -e`
- nginx temp dirs under `/tmp`
- Random non-root UID support

### 4. Data-Driven Pipeline Config
`pipelines.yaml` declares exactly what each stage generates and which validators
to run. No hardcoded if/elif chains in worker.py means:
- Each stage gets the right validators (not a one-size-fits-all set)
- New stages can be added in YAML without touching Python
- Stage ordering and dependencies are explicit

### Net Effect
With these changes, a typical RHOSO pipeline run:
1. **Generates cleaner code** — LLM has reference patterns + longer context
2. **Catches errors early** — validators run after every sub-stage
3. **Self-corrects** — validation errors go back to LLM for 3 fix rounds
4. **Builds on OpenShift** — Dockerfile/entrypoint are OpenShift-safe from generation
