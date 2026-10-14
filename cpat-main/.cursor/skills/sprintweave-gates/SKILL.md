---
name: sprintweave-gates
description: >-
  Interactive gate policy configuration wizard for SprintWeave. Configures
  quality gates between pipeline stages — choose mode (approve/edit/checklist),
  scope (pipeline/all), checklist strictness, and agent skip-list. Use when the
  user says "configure gates", "setup quality gates", "enable gates",
  "gate settings", or "review checkpoints".
---

# SprintWeave Gate Policy Wizard

Guide the user through configuring quality gates in `context/team-config.yaml`. Gates add manual review checkpoints between pipeline stages and/or after individual agent runs.

## When to Activate

- User says "configure gates", "setup gates", "enable review gates"
- User says "I want approval between pipeline stages"
- User says "add manual review checkpoints"
- User says "gate settings", "gate policy", "quality checkpoints"

## Process

### Step 1: Check Current Config

Read `context/team-config.yaml`. Check if a `gates:` section exists.

- If exists and `enabled: true`: "Gates are ON in **{mode}** mode, applying to **{apply_to}**. Want to adjust or disable?"
- If exists and `enabled: false`: "Gates are currently disabled. Want to re-enable them?"
- If missing: "Gates are ON by default (pause-approve, pipeline scope). Want to confirm these defaults or adjust?"

### Step 2: Ask Questions (Use AskQuestion Tool)

#### Q1: Enable Gates
```
- Enable quality gates? yes | no
  (If "no" → write gates.enabled: false and stop)
```

#### Q2: Gate Mode
```
- What should happen at each checkpoint?
  • pause-approve — Show summary, ask Approve/Reject/Refine (fastest)
  • pause-edit — Show full output, allow edits, then approve (most thorough)
  • checklist — Auto-evaluate quality checks, require manual confirm (structured)
  • all — Checklist first, then allow edits, then require approval (strictest)
```

#### Q3: Scope
```
- Where should gates apply?
  • pipeline — Only between agents in pipeline runs (recommended)
  • all — After every agent run (including single-agent requests)
```

#### Q4: Checklist Configuration
```
- Which quality checks should gates verify? (multi-select)
  • Source traceability — every item cites its source section
  • PII clean — no sensitive data in output
  • No unverified content — no [UNVERIFIED] flags
  • Minimum items — at least 1 artifact generated
  (All are recommended)
```

#### Q5: Skip List
```
- Any agents that should auto-pass without a gate? (multi-select or "none")
  • Requirements Analyst
  • Solution Architect
  • Technical Lead
  • QA Architect
  • DevOps Engineer
  • Cloud Deployment Engineer
  • Automation Engineer
  • SRE Engineer
  • Technical Writer
  • Governance Specialist
  • Project Manager
  • Sprint Coach
  • Proposal Writer
```

### Step 3: Generate Config

Build the YAML section from answers:

```yaml
# Quality Gates — Manual review checkpoints
# Re-configure: Type "configure gates" in chat
# Per-prompt override: append "with gates" or "no gates" to any command
gates:
  enabled: {enabled}
  mode: {mode}
  apply_to: {apply_to}
  checklist:
    require_source_traceability: {traceability}
    require_pii_clean: {pii}
    require_no_unverified: {unverified}
    require_min_items: {min_items}
  skip_agents: {skip_list}
```

### Step 4: Write & Confirm

1. Show the generated `gates:` section in a code block
2. Ask: "Does this look right? I can adjust any setting."
3. On approval, append/replace the `gates:` section in `context/team-config.yaml`
4. Confirm: "Gate policy saved. Pipelines will now pause for review between stages."

### Step 5: Explain Usage

After writing, show the user how gates work:

```
Gate Policy Active:
  Mode: {mode}
  Scope: {apply_to}
  Skipped agents: {skip_list or "none"}

How to use:
  • Run any pipeline normally — gates appear automatically
  • Override per-prompt: "Run pipeline on @doc no gates" (disables for that run)
  • Override per-prompt: "Run pipeline on @doc with checklist" (force checklist mode)
  • Mid-pipeline: "approve all" skips remaining gates
  • Mid-pipeline: "skip" passes one gate without endorsement

Dashboard:
  • The Canvas dashboard shows gate status and per-pipeline toggles
```

## Quick Mode

If user provides details upfront (e.g., "Enable gates in checklist mode for pipelines only"), extract all available info and generate directly — only confirm before writing.

## Security Notes

- Gate config contains no secrets — safe to commit
- Gate audit trails in pipeline summaries do not include document content
- Skip-list is advisory only — users can always override per-prompt

## Rules

- Always show the final config before writing
- Never overwrite without confirmation
- Use AskQuestion for multi-choice fields when available
- Default recommendation: `mode: pause-approve`, `apply_to: pipeline`, all checklist items enabled, no skip agents
- Keep the conversation concise — don't over-explain unless asked
