# Cursor-like RHOSO agent runtime

SprintWeave on OpenShift can run **RHOSO DA** and **RHOSO Deployment Engineer** with a
tool-calling loop (read/write/list files + `run_python`), closer to Cursor than one-shot chat.

## What you get

| Stage | Behavior |
|-------|----------|
| RHOSO DA | Docling-parses PDFs → agent writes `output/ciq-generators/`, Excel under `output/ciq-workbooks/`, reports under `output/pipeline-reports/rda/` |
| RHOSO DE | Agent writes CPAT tree under `output/cpat/` + `pipeline-reports/rde/` |
| AUTO / QA / DOC | Still one-shot markdown (legacy) |

Workspace on PVC:

```text
/data/jobs/<job_id>/workspace/
  input/     # from input set
  parsed/    # Docling markdown
  context/   # seeded from image agents
  output/    # real deliverables
/data/jobs/<job_id>/output/   # mirrored for download API
```

## Build (Docling base + thin app)

Docling is slow to install. Split into two images:

| Image | Dockerfile | When to rebuild |
|-------|------------|-----------------|
| `sprintweave-docling-base` | `Dockerfile.docling-base` | Rarely (Docling version bump) |
| `sprintweave-rhoso` | `Dockerfile.bundle` | Every code/agents change (fast) |

```bash
cd /path/to/CFP_NEW
ORG=rh_global_services_auto

# 1) Once — heavy (multi-GB, can take a long time)
podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/${ORG}/sprintweave-docling-base:latest .
podman push quay.io/${ORG}/sprintweave-docling-base:latest

# 2) Often — thin (only FastAPI/Streamlit + COPY code)
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=cpat-main \
  --build-arg PIPELINES=lab-requirements,rhoso \
  -t quay.io/${ORG}/sprintweave-rhoso:latest .
podman push quay.io/${ORG}/sprintweave-rhoso:latest
```

Create Quay repo `sprintweave-docling-base` (can be private). Build on WSL/bastion if corp proxy breaks pulls.

Same pattern for full agents: `AGENTS_SRC=sprintweave-agents` → tag `sprintweave:latest`.

## Deploy

```bash
# New project or update existing
oc apply -f sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml
# Ensure LLM secret exists; image name patched to your Quay path
oc set image deployment/sprintweave-api api=quay.io/YOUR_ORG/sprintweave-rhoso:latest -n sprintweave-rhoso
oc set image deployment/sprintweave-ui ui=quay.io/YOUR_ORG/sprintweave-rhoso:latest -n sprintweave-rhoso
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui -n sprintweave-rhoso
```

ConfigMap knobs (already in YAML):

- `LLM_MAX_TOKENS=8192`
- `LLM_TIMEOUT=600`
- `SPRINTWEAVE_USE_DOCLING=true`
- `SPRINTWEAVE_DOCLING_OCR=false` — text-layer PDFs; avoids RapidOCR under site-packages
- `SPRINTWEAVE_DOCLING_TABLES=false` — fewer HF model downloads
- `SPRINTWEAVE_REQUIRE_PARSED=true` — if Docling fails on all PDF/DOCX, job **fails immediately** (no LLM)
- API mounts `emptyDir` at `/opt/docling-cache` (writable by OpenShift UID)
- `SPRINTWEAVE_AGENT_MAX_STEPS=40`
- `LLM_PROVIDER=openai` (required for tool calls via MaaS/LiteLLM)

API pod requests **2Gi / up to 8Gi** memory.

## Smoke test

1. **Inputs** — create set `rhoso-test`, upload RHOSO PDFs (or a single small PDF first).
2. **Run** — RHOSO pipeline, gates **on**.
3. Wait for Docling + RDA agent (minutes). Logs show `[parsed]`, `[agent] step`, `[tool] write_file` / `run_python`.
4. At RDA gate — **Generated artifacts** should list `.py` / `.xlsx` / reports. Download zip.
5. Approve → RDE runs → look for `cpat/` paths.

Cheap check: Lab Requirements (one RDA-style stage) with one small PDF before the full 9-doc pack.

## Closer-to-Cursor behavior (current)

- **Cursor-like edits (Lab + full RHOSO):** same tools for **RHOSO DA** and all **RDE-1…4** passes — `append_file` + `str_replace` (hunks) plus capped `write_file`. Not Lab-only. Agent rules and stage prompts tell the model to skeleton → hunks, never full-file rewrite loops.
- **History compaction:** before each LLM step, older tool results (beyond last `SPRINTWEAVE_AGENT_COMPACT_KEEP_TURNS`, default 3) are replaced with one-line summaries so prompt size stays roughly flat. Disable with `SPRINTWEAVE_AGENT_COMPACT=false`.
- **Anti-explore thrash:** `SPRINTWEAVE_AGENT_PYTHON_INLINE=false` (default) blocks `run_python(code=...)`; only `script_path=` after a written generator. Parsed dumps via inline Python are refused even if inline is on. After step 3 with no `output/` write, a force-write nudge is injected.
- **Full context upfront (like Cursor @file):** For Lab, the entire parsed document is sent inline in the first user message — the model never needs to `read_file` or `search_files`. This is why Cursor is cheap: one big prompt → write → done (3 steps), instead of 20 tool rounds to discover content. `SPRINTWEAVE_TEXT_MAX=60000` (default) controls per-file size. For RHOSO DA/DE, up to 40k of sources are sent inline.
- **Single-shot (no tool steps):** `SPRINTWEAVE_LAB_SINGLE_SHOT`, `SPRINTWEAVE_RDA_SINGLE_SHOT`, `SPRINTWEAVE_RDE_SINGLE_SHOT` (all default true). Lab/RDA/RDE use 1–2 LLM calls per stage; worker writes files from `### FILE: path` bundles. Falls back to the tool loop if the call fails. This is the main cost cut vs 25 steps × 4 RDE passes.
- **Cursor prompt on Run:** default command like `Run RHOSO delivery pipeline on @cpat` plus `@` chips (`@cpat`, `@input`, `@context`, `@file`). Sent to agents as the user prompt.
- **Stop:** Job page **Stop** button → `POST /v1/jobs/{id}/cancel`. Halts between agent steps (status `cancelled`). Cannot abort an in-flight MaaS HTTP call.
- **Skills:** `.cursor/skills/*/SKILL.md` seeded into the job workspace and injected into the agent system prompt. RHOSO images overlay skills from `sprintweave-agents` at build time.
- **RDE multi-pass:** RHOSO Deployment Engineer runs four agent loops — Ansible → Backend → Frontend → Docker/reports — like Cursor sub-stages.
- **Tools:** `list_dir`, `read_file`, `write_file`, `append_file`, `str_replace`, `delete_file`, `run_python`, `search_files`.

### Verify MaaS tool calling

Before a long RHOSO run, confirm the gateway returns `tool_calls`:

```bash
cd sprintweave-web
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://maas-.../v1
export LLM_API_KEY=...
export LLM_MODEL=claude-opus-4-6
python scripts/smoke_tool_calling.py
```

`PASS` = safe to run agent stages. `FAIL` with no tool_calls = fix LiteLLM/MaaS tool support first.

## Limits (not full Cursor)

- No IDE, no MCP, no mid-loop chat except **gate follow-up**.
- Tools are jailed to the job workspace; only `run_python` (no arbitrary shell).
- Cost/time much higher than the old markdown-only stages (RDE = 4 agent loops).
- Model must support OpenAI tool calling through your LiteLLM/MaaS gateway.

## Verify in cluster

```bash
oc logs -f deploy/sprintweave-api -n sprintweave-rhoso
oc rsh deploy/sprintweave-api -- ls -R /data/jobs/<job_id>/output | head -80
```
