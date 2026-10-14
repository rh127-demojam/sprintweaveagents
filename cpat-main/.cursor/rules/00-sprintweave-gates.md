---
description: "Quality gates, manual review, approval checkpoints between pipeline stages, gate configuration"
alwaysApply: false
---
# SprintWeave Quality Gates (Configurable)

## Scope

This rule is always active. It defines how quality gate checkpoints work between pipeline stages and after individual agent runs. Gates are configurable — they can be enabled/disabled globally, per-pipeline, or per-prompt.

---

## Gate Configuration

Read gate settings from `@context/team-config.yaml` under the `gates:` section:

```yaml
gates:
  enabled: true/false         # Master switch
  mode: pause-approve         # pause-approve | pause-edit | checklist | all
  apply_to: pipeline          # pipeline | all | none
  checklist:
    require_source_traceability: true
    require_pii_clean: true
    require_no_unverified: true
    require_min_items: true
  skip_agents: []             # Agents that auto-pass (no gate shown)
```

If `gates` section is missing from team-config, gates are **enabled** by default (mode: `pause-approve`, apply_to: `pipeline`).

---

## Per-Prompt Overrides

Users can override the team-config setting in any prompt. Per-prompt ALWAYS wins:

| User Says | Effect |
|-----------|--------|
| `"... with gates"` | Enable gates for this run (mode from team-config) |
| `"... with checklist"` | Enable gates in checklist mode |
| `"... with approval gates"` | Enable gates in pause-approve mode |
| `"... no gates"` | Disable gates for this run |
| `"... skip gate for [agent]"` | Skip gate after specific agent |

**Detection:** Check if the user's prompt contains these keywords BEFORE starting generation.

---

## Gate Modes

### Mode 1: pause-approve

Show a summary and ask for explicit approval before proceeding.

```
┌─────────────────────────────────────────────────┐
│  GATE: [Agent Name] Complete                    │
├─────────────────────────────────────────────────┤
│  Artifacts: N items generated                   │
│  Traceability: N/N items have source citations  │
│  PII Status: Clean / [N items flagged]          │
│  Quality: [brief assessment]                    │
│                                                 │
│  Action Required:                               │
│    • Approve  → proceed to next stage           │
│    • Reject   → re-generate with feedback       │
│    • Refine   → modify output, then re-gate     │
│                                                 │
│  Type: "approve", "reject: [reason]",           │
│        or a refinement command                  │
└─────────────────────────────────────────────────┘
```

**Behavior:**
- On "approve" / "yes" / "continue" / "proceed" / "next" → move to next agent
- On "reject" / "redo" + reason → re-run agent incorporating feedback
- On any refinement command (e.g., "split story #3") → apply refinement, show gate again

### Mode 2: pause-edit

Show full output and invite the user to refine before approving.

```
┌─────────────────────────────────────────────────┐
│  GATE: [Agent Name] — Review & Edit             │
├─────────────────────────────────────────────────┤
│  Output shown above. You can now:               │
│    • Refine: "Split story #4", "Add risk for X" │
│    • Approve: "approve" to proceed              │
│    • Reject: "reject: [reason]" to redo         │
│                                                 │
│  Take your time — next agent waits for you.     │
└─────────────────────────────────────────────────┘
```

**Behavior:**
- Show full markdown output first (as normal)
- Then show the gate prompt
- Allow unlimited refinement commands
- Only proceed on explicit "approve"

### Mode 3: checklist

Present a quality checklist. All required items must pass.

```
┌─────────────────────────────────────────────────┐
│  GATE: [Agent Name] — Quality Checklist         │
├─────────────────────────────────────────────────┤
│  [x] Source traceability: 12/12 items cited     │
│  [x] PII clean: No sensitive data detected      │
│  [x] No [UNVERIFIED] flags in output            │
│  [x] Minimum items: 12 generated (threshold: 1) │
│  [ ] Manual review: YOU confirm output quality  │
│                                                 │
│  Status: 4/5 automated checks passed            │
│  Action: Confirm manual review to proceed       │
│          or type a refinement command            │
└─────────────────────────────────────────────────┘
```

**Checklist items (auto-evaluated):**

| Check | How to Evaluate | Pass Condition |
|-------|-----------------|----------------|
| Source traceability | Count items with `[Source: ...]` citations | All items have citations |
| PII clean | Scan for patterns: IPs, emails, hostnames, credentials | No matches found |
| No [UNVERIFIED] | Search output for `[UNVERIFIED]` markers | Zero occurrences |
| Minimum items | Count generated artifacts (stories, tests, etc.) | At least 1 item generated |
| Manual review | User confirmation | User types "confirm" or "approve" |

**Behavior:**
- Auto-evaluate first 4 checks
- If any auto-check fails: flag it with `[ ]` and explain what failed
- Always require manual review confirmation (the 5th check)
- If auto-checks fail: user can still approve (override) or refine

### Mode 4: all

Combines all three — show checklist FIRST, then allow editing, then require explicit approval.

---

## When Gates Apply

### Pipeline Context (apply_to: pipeline)

Gates activate BETWEEN agents during orchestrated pipeline runs:

```
Agent 1 → GATE → Agent 2 → GATE → Agent 3 → ... → Final Summary
```

The orchestrator (`agent-orchestrator.md`) manages the gate flow:
1. Agent completes and shows output
2. Gate checkpoint displayed
3. Wait for user response
4. On approval → pass output to next agent
5. On reject/refine → loop back

**Exception:** Agents listed in `skip_agents` auto-pass without showing a gate.

### All Context (apply_to: all)

Gates also activate after standalone single-agent runs:
- User asks "Generate user stories from @doc"
- Agent generates output
- Gate checkpoint shown AFTER the Quality Summary
- User approves or refines
- Only then is the output considered "final"

### None (apply_to: none)

Same as `gates.enabled: false` — no gates shown anywhere.

---

## Gate in Single-Agent Runs

When a single agent runs (not part of a pipeline) and gates are enabled for `all`:

1. Agent completes its normal flow (Load → Analyze → Generate → Output → Excel → Quality Summary)
2. AFTER the Quality Summary, show the gate checkpoint
3. Wait for user action
4. On approval: confirm completion
5. On refinement: apply changes, regenerate gate

---

## Gate in Pipeline Runs

The orchestrator handles all gates during pipelines:

1. Run Agent N
2. Show Agent N output (abbreviated in pipeline context)
3. Show gate checkpoint for Agent N
4. Wait for user response
5. On approval: "Proceeding to Agent N+1..."
6. On reject: re-run Agent N with user feedback, then re-gate
7. On refine: apply refinement to Agent N output, then re-gate

**Pipeline-specific behavior:**
- Show which step you're on: "Gate 3/11: QA Architect"
- Show what's coming next: "Next: DevOps Engineer (deployment runbook)"
- Allow "approve all remaining" to skip future gates for this run
- Allow "skip" to auto-pass just this gate (without approving quality)

---

## Special Commands During Gates

| Command | Effect |
|---------|--------|
| `approve` / `yes` / `next` / `continue` | Pass this gate, proceed |
| `approve all` / `no more gates` | Pass this gate AND skip all remaining gates in this pipeline |
| `skip` | Skip this gate without quality endorsement (logged in summary) |
| `reject: [reason]` / `redo: [reason]` | Re-run this agent with the given feedback |
| `[any refinement]` | Apply refinement (e.g., "split story #3"), then show gate again |

---

## Gate Summary (End of Pipeline)

At the end of a gated pipeline, include a gate audit trail in the final summary:

```
Gate Audit:
  1. Requirements Analyst: Approved (1 refinement applied)
  2. Solution Architect: Approved
  3. Technical Lead: Approved
  4. QA Architect: Skipped (user override)
  5. DevOps Engineer: Approved (2 refinements applied)
  ...
  
  Gates passed: 9/11 | Skipped: 2 | Rejected+Retried: 1
```

---

## Rules

- Gates are ON by default — opt out with `no gates` or set `gates.enabled: false` in team-config
- Per-prompt override ALWAYS wins over team-config
- Never show a gate if `gates.enabled: false` AND no per-prompt override
- Gate checkpoints do NOT count as a separate "agent" — they're part of the flow
- Refinements during a gate use the same iterative refinement commands defined in each agent
- The gate does NOT re-run Excel export unless the refinement changes data
- PII redaction rules still apply to all gate output
- If team-config has no `gates:` section, treat as `gates.enabled: true` (mode: pause-approve, apply_to: pipeline)
