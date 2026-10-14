---
name: sprintweave-pipelines
description: >-
  Interactive pipeline management wizard for SprintWeave. Create, edit, copy,
  delete, promote, hide, and restore custom pipeline sequences in
  context/pipelines.yaml. Use when the user says "manage pipelines",
  "create pipeline", "edit pipeline", "delete pipeline", "restore default
  pipelines", or when the canvas sends a pipeline save/delete/promote command.
---

# SprintWeave Pipeline Management Wizard

Manage custom pipeline sequences stored in `context/pipelines.yaml`. Custom pipelines let teams define their own agent execution order without editing rule files.

## When to Activate

- User says "manage pipelines", "pipeline manager", "pipeline wizard"
- User says "create pipeline", "create a custom pipeline", "new pipeline"
- User says "edit pipeline [name]", "update pipeline [name]"
- User says "delete pipeline [name]", "remove pipeline [name]"
- User says "hide pipeline [name]" (for built-ins)
- User says "promote pipeline [name]"
- User says "restore default pipelines", "reset pipelines"
- Canvas dispatches: `Save this custom pipeline to context/pipelines.yaml and run sync: {json}`
- Canvas dispatches: `Delete custom pipeline "{name}" ...`
- Canvas dispatches: `Hide built-in pipeline "{name}" ...`
- Canvas dispatches: `Promote custom pipeline "{name}" ...`
- Canvas dispatches: `Restore default pipelines in context/pipelines.yaml`

## Configuration Files

| File | Purpose |
|------|---------|
| `context/pipelines.yaml` | Team custom pipeline store (editable) |
| `tools/pipelines-default.yaml` | Built-in pipeline definitions (read-only reference) |
| `tools/sync-pipeline-config.py` | Syncs YAML to canvas dashboard |

## Schema Reference

```yaml
# context/pipelines.yaml
version: 1
custom:
  - id: my-pipeline           # Slug, unique among custom entries
    name: "My Pipeline"       # Display name
    command: "Run my-pipeline on @input/"  # Launch phrase
    stages:                   # Ordered agent sequence
      - { abbrev: REQ, agent: "Requirements Analyst", output: "Stories" }
      - { abbrev: QA, agent: "QA Architect", output: "Tests" }
    based_on: standard        # (optional) Lineage when copied from built-in
    promoted: true            # (optional) Show as promoted in dashboard
deleted_builtin: []           # Built-in IDs to hide
```

## Available Agents

| Abbrev | Agent |
|--------|-------|
| REQ | Requirements Analyst |
| ARCH | Solution Architect |
| TECH | Technical Lead |
| QA | QA Architect |
| OPS | DevOps Engineer |
| CLD | Cloud Deployment Engineer |
| AUTO | Automation Engineer |
| SRE | SRE Engineer |
| DOC | Technical Writer |
| GOV | Governance Specialist |
| PM | Project Manager |
| SPR | Sprint Coach |
| RFP | Proposal Writer |

## Process

### Action: Create Pipeline

1. **Ask** (use AskQuestion if interactive):
   - Pipeline name (required)
   - Launch command — suggest pattern: `Run [slug] on @input/`
   - Stages — which agents, in what order, with output descriptions
2. **Generate** the `id` slug from the name (lowercase, hyphens, no spaces)
3. **Validate:**
   - `id` must be unique (not already in `custom` or built-in IDs)
   - At least 1 stage required
   - All agents must be from the available agents list
4. **Append** to `custom` array in `context/pipelines.yaml`
5. **Run sync:** `python tools/sync-pipeline-config.py`
6. **Confirm:** "Pipeline '[name]' created with [N] stages. Dashboard updated."

### Action: Edit Pipeline

1. **Read** `context/pipelines.yaml` and find the custom entry by `id` or `name`
2. **If not found:** Report error — only custom pipelines can be edited
3. **Show** current config and ask what to change
4. **Update** the entry in-place
5. **Run sync:** `python tools/sync-pipeline-config.py`
6. **Confirm:** "Pipeline '[name]' updated. Dashboard refreshed."

### Action: Copy Pipeline

1. **Identify** the source pipeline (can be built-in or custom)
2. **Create** a new custom entry with:
   - New unique `id` and `name` (append " (Copy)" or user's choice)
   - Same `stages` as source
   - `based_on: [source_id]`
3. **Append** to `custom` array
4. **Run sync**
5. **Confirm**

### Action: Delete Custom Pipeline

1. **Find** the custom entry by `id` or `name`
2. **Remove** from `custom` array
3. **Run sync**
4. **Confirm:** "Pipeline '[name]' deleted."

### Action: Hide Built-in Pipeline

1. **Validate** the ID exists in `tools/pipelines-default.yaml`
2. **Append** the ID to `deleted_builtin` array in `context/pipelines.yaml`
3. **Run sync**
4. **Confirm:** "Built-in pipeline '[name]' hidden. Use 'Restore default pipelines' to unhide."

### Action: Promote Custom Pipeline

1. **Find** the custom entry by `id`
2. **Set** `promoted: true` on the entry
3. **Run sync**
4. **Confirm:** "Pipeline '[name]' promoted. It now appears as a recommended pipeline."

### Action: Restore Defaults

1. **Reset** `context/pipelines.yaml` to:
   ```yaml
   version: 1
   custom: []
   deleted_builtin: []
   ```
2. **Run sync**
3. **Confirm:** "All custom pipelines removed and hidden built-ins restored. Dashboard shows default 7 pipelines."

### Action: Canvas JSON Save

When the canvas sends a JSON payload (from Pipeline Manager save button):

1. **Parse** the JSON payload
2. **Validate** required fields: `name`, `stages` (non-empty)
3. **Generate** `id` if not provided
4. **Upsert:** If `id` already exists in `custom`, update it. Otherwise append.
5. **Run sync**
6. **Confirm**

## Quick Mode

If the user provides all details upfront (e.g., "Create a custom pipeline with REQ, QA, OPS named Quick Validate"), extract all info and generate directly — only confirm before writing.

## Sync Command

After EVERY write to `context/pipelines.yaml`, always run:

```
python tools/sync-pipeline-config.py
```

This updates the canvas dashboard to reflect the latest pipeline definitions.

## Rules

- Never modify `tools/pipelines-default.yaml` — it is the canonical built-in source
- Always validate agent names against the available agents list
- Always run sync after writing pipelines.yaml
- Show the user what will be written before writing (quick confirmation)
- Keep command patterns ending with `on @input/` or `on @doc` for orchestrator matching
- Pipeline IDs must be URL-safe slugs (lowercase alphanumeric + hyphens)
