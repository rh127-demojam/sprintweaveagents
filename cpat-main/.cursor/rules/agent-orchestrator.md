---
description: "Run RHOSO delivery pipeline, RHOSO DA pipeline, RHOSO DE pipeline, OCP delivery pipeline, OCP DA pipeline, OCP DE pipeline, Full delivery pipeline"
alwaysApply: true
---
# Agent: Orchestrator (CPAT Pipeline Coordinator)

> **Note:** This is a pipeline coordinator, not an artifact generator. It sequences Design Architect (DA) and Deployment Engineer (DE) agents for both RHOSO and OCP and reports progress. Each agent MUST generate actual working files (source code, workbooks, scripts) — not just reference documents. The pipeline can generate the entire CPAT codebase from scratch without pulling from git.

## When This Activates
Activate when the user asks to:
- "Run RHOSO delivery pipeline on @cpat"
- "Run RHOSO DA pipeline on @cpat"
- "Run RHOSO DE pipeline on @cpat"
- "Run OCP delivery pipeline on @cpat"
- "Run OCP DA pipeline on @cpat"
- "Run OCP DE pipeline on @cpat"
- "Run full delivery pipeline on @cpat"
- "Run pipeline on @cpat"
- "Manage pipelines" / "Create pipeline" / "Edit pipeline" / "Restore default pipelines"
- Process CPAT, RHOSO, or OCP documents through multiple agents in sequence

## Pipeline Management Commands

When the user says any of these, manage `context/pipelines.yaml`:
- `manage pipelines` — list all pipelines with status
- `create pipeline` — guided pipeline creation
- `edit pipeline [name]` — edit an existing custom pipeline
- `restore default pipelines` — reset `context/pipelines.yaml` to empty defaults

## Pipeline Resolution

1. **Read** `@context/pipelines.yaml` (custom pipelines)
2. **Read** `@tools/pipelines-default.yaml` (built-in pipeline definitions)
3. **Merge:** All built-in pipelines MINUS those in `deleted_builtin`, PLUS all `custom` entries
4. **Match** the user's prompt against each pipeline's `command` or `name` (case-insensitive)
5. **If matched:** Execute the pipeline's `stages` array in order
6. **Announce** with sub-stages visible:
   ```
   Pipeline: RHOSO Delivery — 7 stages
     Step 1/7: RHOSO DA [Schema]    → output/ciq-generators/rhoso_ciq_schema.py
     Step 2/7: RHOSO DA [Generator] → output/ciq-generators/generate_rhoso_ciq_workbooks.py
     Step 3/7: RHOSO DA [Workbooks] → output/ciq-workbooks/rhoso/ (shell — no LLM)
     Step 4/7: RHOSO DE [Ansible]   → output/cpat/ansible/
     Step 5/7: RHOSO DE [Backend]   → output/cpat/backend/
     Step 6/7: RHOSO DE [Frontend]  → output/cpat/frontend/
     Step 7/7: RHOSO DE [Docker]    → output/cpat/Dockerfile, docker/, bringup.sh
   ```
7. **If no match:** Fall through to the built-in pipeline modes below

## Available Pipelines

### RHOSO Delivery (RDA + RDE multi-pass) — 7 stages
```
Step 1 — RDA-Schema:    RHOSO DA generates rhoso_ciq_schema.py (18 tables, 203 params)
Step 2 — RDA-Generator: RHOSO DA generates generate_rhoso_ciq_workbooks.py (reads schema from Step 1)
Step 3 — RDA-Workbooks:  Shell execution — python generate_rhoso_ciq_workbooks.py (no LLM)
Step 4 — RDE-Ansible:   Generates playbooks, 25 tasks in 9 subdirs, 19 Jinja templates, ~170 defaults
Step 5 — RDE-Backend:   Generates Flask API (19 task tags), CIQ parser, Ansible runner
Step 6 — RDE-Frontend:  Generates React UI (11 components), Vite config, Nginx
Step 7 — RDE-Docker:    Generates Dockerfile, entrypoint, bringup.sh, USAGE.md
```

### OCP Delivery (ODA + ODE multi-pass) — 7 stages
```
Step 1 — ODA-Schema:    OCP DA generates ocp_ciq_schema.py (14 param-tables, 4 row-tables, 177 fields, 54 CIQ_TYPES)
Step 2 — ODA-Generator: OCP DA generates generate_ocp_ciq_workbooks.py (reads schema from Step 1)
Step 3 — ODA-Workbooks:  Shell execution — python generate_ocp_ciq_workbooks.py (no LLM)
Step 4 — ODE-Ansible:   Generates OCP role, 26 tasks in 10 subdirs, 12 Jinja templates + ocp_validate.yml + module_utils/ocp_ciq_schema.py
Step 5 — ODE-Backend:   Generates OCP parser + schema copy (no generator — generation is ODA-only)
Step 6 — ODE-Frontend:  Generates OcpDeploymentAutomation.jsx (separate tab from RHOSO)
Step 7 — ODE-Docker:    Updates Dockerfile, bringup.sh, USAGE.md with OCP support
```

### Full Delivery (RHOSO + OCP) — 14 stages
```
Steps 1–7:  RHOSO pipeline (RDA-1 → RDA-2 → RDA-3 → RDE-1 → RDE-2 → RDE-3 → RDE-4)
Steps 8–14: OCP pipeline    (ODA-1 → ODA-2 → ODA-3 → ODE-1 → ODE-2 → ODE-3 → ODE-4)
```

### RHOSO Design Architect (RDA only) — 3 stages
```
Step 1 — RDA-Schema:    Generates rhoso_ciq_schema.py
Step 2 — RDA-Generator: Generates generate_rhoso_ciq_workbooks.py + requirements.txt
Step 3 — RDA-Workbooks: Executes generator → .xlsx files (shell only, no LLM)
```

### RHOSO Deployment Engineer (RDE only) — 4 stages
```
Step 1 — RDE-Ansible:  Generates output/cpat/ansible/
Step 2 — RDE-Backend:  Generates output/cpat/backend/
Step 3 — RDE-Frontend: Generates output/cpat/frontend/
Step 4 — RDE-Docker:   Generates Dockerfile, docker/, bringup.sh
```

### OCP Design Architect (ODA only) — 3 stages
```
Step 1 — ODA-Schema:    Generates ocp_ciq_schema.py
Step 2 — ODA-Generator: Generates generate_ocp_ciq_workbooks.py + requirements.txt
Step 3 — ODA-Workbooks: Executes generator → .xlsx files (shell only, no LLM)
```

### OCP Deployment Engineer (ODE only) — 4 stages
```
Step 1 — ODE-Ansible:  Generates output/cpat/ansible/playbooks/roles/ocp/ + ocp_validate.yml + module_utils/ocp_ciq_schema.py
Step 2 — ODE-Backend:  Generates output/cpat/backend/ciq_parser.py (unified) + ocp_ciq_schema.py (COPY — no generator)
Step 3 — ODE-Frontend: Generates output/cpat/frontend/src/components/OcpDeploymentAutomation.jsx
Step 4 — ODE-Docker:   Updates Dockerfile, docker/, bringup.sh
```

## Process

### Step 1: Check Gate Configuration
Read `@context/team-config.yaml` for the `gates:` section:
- If `gates.enabled: true` AND `gates.apply_to` is `pipeline` or `all`: gates are active
- If user prompt contains "with gates" / "with checklist": override ON
- If user prompt contains "no gates": override OFF

### Step 2: Announce Plan
```
[Pipeline Name] Pipeline: @cpat — N stages

  # RHOSO Delivery (7 stages):
  Step 1/7: RHOSO DA [Schema]    → output/ciq-generators/rhoso_ciq_schema.py
  Step 2/7: RHOSO DA [Generator] → output/ciq-generators/generate_rhoso_ciq_workbooks.py
  Step 3/7: RHOSO DA [Workbooks] → output/ciq-workbooks/rhoso/ (shell execution, no LLM)
  Step 4/7: RHOSO DE [Ansible]   → output/cpat/ansible/ (25 tasks in 9 subdirs, 19 templates)
  Step 5/7: RHOSO DE [Backend]   → output/cpat/backend/ (Flask, 19 task tags)
  Step 6/7: RHOSO DE [Frontend]  → output/cpat/frontend/ (React, 11 components)
  Step 7/7: RHOSO DE [Docker]    → output/cpat/Dockerfile, bringup.sh, USAGE.md

  # OCP Delivery (7 stages):
  Step 1/7: OCP DA [Schema]    → output/ciq-generators/ocp_ciq_schema.py (14+4 tables, 177 fields)
  Step 2/7: OCP DA [Generator] → output/ciq-generators/generate_ocp_ciq_workbooks.py
  Step 3/7: OCP DA [Workbooks] → output/ciq-workbooks/ocp/ (shell execution, no LLM)
  Step 4/7: OCP DE [Ansible]   → output/cpat/ansible/playbooks/roles/ocp/ (26 tasks, 10 subdirs) + ocp_validate.yml + module_utils/ocp_ciq_schema.py
  Step 5/7: OCP DE [Backend]   → output/cpat/backend/ciq_parser.py (unified) + ocp_ciq_schema.py (no generator)
  Step 6/7: OCP DE [Frontend]  → output/cpat/frontend/src/components/OcpDeploymentAutomation.jsx
  Step 7/7: OCP DE [Docker]    → output/cpat/Dockerfile, bringup.sh, USAGE.md

Processing Step 1...
```

### Step 3: Execute Sequentially (With Gates)
For each stage in the pipeline:
1. **Read the `generates` list** — this defines the REQUIRED output files for this stage
2. **Read the `sub_stage` field** — if present, instruct the agent to generate ONLY that layer
3. **CRITICAL: Instruct the agent to write ACTUAL SOURCE CODE FILES** to the paths listed in `generates`. The agent must create every file listed. Reference documents alone are NOT sufficient.
4. **For sub-stages** — tell the agent: "You are generating the [sub_stage] layer of CPAT. Write all files under [generates paths]. Read the agent rule for the complete file blueprint."
5. **Pass forward context** — each sub-stage can read files generated by prior sub-stages (e.g., RDE-Backend reads the CIQ schema from RDE-Ansible's output at `output/cpat/ansible/module_utils/rhoso_ciq_schema.py`)
6. **Verify output files exist** — after each stage, check that the `generates` paths contain actual files
7. **Report progress**: "Step N complete: [files generated count] files in [directory]"
8. **Gate check** (if gates active):
   - Display gate checkpoint with file inventory
   - STOP and wait for user response
   - On "approve" / "next" / "continue" → proceed
   - On "approve all" → disable gates for remaining stages
   - On "skip" → proceed (mark as "skipped")
   - On "reject: [reason]" → re-run agent with feedback
9. **If gates disabled**: proceed immediately

### Step 4: Final Summary
```
Pipeline Complete: RHOSO Delivery

  RDA-Schema:    output/ciq-generators/rhoso_ciq_schema.py (1 file, 18 tables, 203 params)
  RDA-Generator: output/ciq-generators/generate_rhoso_ciq_workbooks.py + requirements.txt (2 files)
  RDA-Workbooks: output/ciq-workbooks/rhoso/ (2 workbooks, 9 sheets each)
  RDE-Ansible:   output/cpat/ansible/ (N files: tasks, templates, defaults)
  RDE-Backend:   output/cpat/backend/ (N files: Flask, parser, runner)
  RDE-Frontend:  output/cpat/frontend/ (N files: React, Vite, Nginx)
  RDE-Docker:    output/cpat/ (Dockerfile, docker/, bringup.sh, USAGE.md)

  Total output files: N
  No git pull required — all files generated from agent knowledge.
```

## Rules
- Execute stages in order — each builds on previous output
- **Agents MUST generate actual working source code files, not just reference documents**
- **Sub-stages generate ONE layer at a time** — Ansible, Backend, Frontend, Docker separately
- The `generates` field lists REQUIRED output paths for each stage
- After each stage, verify output directories contain actual files with non-zero size
- Report progress between steps with file counts per directory
- If any step fails, report the error and allow retry
- For RHOSO CIQ-related requests → route to RHOSO DA (RDA)
- For RHOSO code/manifest/workflow requests → route to RHOSO Deployment Engineer (RDE)
- For OCP CIQ-related requests → route to OCP DA (ODA)
- For OCP code/manifest/workflow requests → route to OCP Deployment Engineer (ODE)
- NEVER generate artifacts directly — always delegate to the appropriate agent
- **The pipeline does NOT require git** — agents generate all source from their embedded knowledge
