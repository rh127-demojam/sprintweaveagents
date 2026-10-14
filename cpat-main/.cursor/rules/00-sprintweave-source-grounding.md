---
alwaysApply: true
---
# SprintWeave Source Grounding (Always Active)

## Scope
This rule activates for ALL SprintWeave interactions. It ensures every generated artifact is grounded in the source document(s) — no hallucinated content, no fabricated facts, no invented procedures.

---

## 1. Source Grounding Mandate

Every claim, procedure, requirement, test case, or recommendation in SprintWeave output MUST be traceable to the source document(s). If content cannot be traced, it must be explicitly flagged.

### What Counts as "Grounded"
| Category | Grounded | Example |
|----------|----------|---------|
| **Direct extraction** | ✅ Yes | Procedure steps copied/paraphrased from source § 3.2 |
| **Reasonable inference** | ✅ Yes (flagged) | "Rollback likely needed" when source describes a risky change |
| **Domain best practice** | ⚠️ Conditional | Only if clearly labeled as "Best Practice — not in source" |
| **Fabricated detail** | ❌ Never | Inventing CLI commands, IP addresses, hostnames, configs not in source |
| **Assumed requirement** | ❌ Never | Adding requirements the source doesn't mention |

### The Core Rule
> **If it's not in the source document, don't state it as fact.**

---

## 2. Verification Markers (Mandatory)

When generating any artifact, use these markers to signal content confidence:

| Marker | When to Use | Example |
|--------|------------|---------|
| `[Source: Doc Title § X.Y]` | Content directly from source | Step extracted from § 3.1 |
| `[INFERRED]` | Reasonable inference from source context | "Backup recommended before upgrade [INFERRED]" |
| `[BEST PRACTICE]` | Industry standard not in source, clearly labeled | "Add health check after restart [BEST PRACTICE]" |
| `[UNVERIFIED]` | Cannot confirm from source, needs SME review | "Timeout may be configurable [UNVERIFIED]" |
| `[INSERT: description]` | Placeholder for info only the user/SME can provide | "[INSERT: actual database hostname]" |
| `[INCOMPLETE IN SOURCE]` | Source document is missing expected detail | "Recovery procedure [INCOMPLETE IN SOURCE]" |

### Rules for Markers
- Every artifact section MUST have at least one source citation
- `[UNVERIFIED]` items MUST be counted in the Quality Summary
- If more than 20% of content is `[UNVERIFIED]` or `[INFERRED]`, flag it prominently
- `[INSERT]` placeholders are MANDATORY instead of fabricating specific values

---

## 3. Fabrication Prevention

### NEVER Fabricate
- **Commands or CLI syntax** not present in the source document
- **IP addresses, hostnames, URLs, or ports** — use `[INSERT: hostname]` or `[REDACTED-IP]` instead
- **Configuration values or parameters** not mentioned in source
- **Metrics, thresholds, or SLA numbers** not stated in source
- **Timelines, durations, or deadlines** not in source — use `[ESTIMATE]` if inferring
- **Requirements** the source doesn't mention or imply
- **Test results or expected outputs** not derivable from source
- **Past performance or statistics** — use `[INSERT]` placeholders
- **Architecture details** (components, integrations) not described in source

### What to Do Instead of Fabricating
| Situation | Wrong | Right |
|-----------|-------|-------|
| Source lacks a CLI command | Invent a plausible command | `[INSERT: command to verify service status]` |
| Source doesn't specify a timeout | Write "timeout is 30s" | "Configure timeout per environment [INSERT: value]" |
| Source mentions a step without detail | Expand with assumptions | Flag: `[INCOMPLETE IN SOURCE — verify with SME]` |
| Source doesn't cover error handling | Invent error scenarios | "Error handling: [NOT COVERED IN SOURCE — recommend defining]" |
| Need a specific hostname | Make up a hostname | Use `[INTERNAL-HOST]` or `[INSERT: target hostname]` |

---

## 4. Gap Reporting (Mandatory)

Every generated artifact MUST include a gap report at the end identifying what the source document does NOT cover:

```
Source Gaps Identified:
  1. [topic/section] — not covered in source, recommended for completeness
  2. [topic/section] — partially covered, details missing for [aspect]
  3. [topic/section] — referenced but no procedure provided

Unverified items: N items flagged [UNVERIFIED]
Inferred items: N items flagged [INFERRED]
Placeholders: N items requiring user input [INSERT]

Recommendation: Review flagged items with SME before using in production.
```

If zero gaps exist, state: "No gaps identified — all content grounded in source."

---

## 5. Cross-Agent Consistency

When an agent consumes output from a prior agent in a pipeline:
- **Trust but verify** — if the prior agent's output contains `[UNVERIFIED]` or `[INFERRED]` markers, propagate them (don't silently drop them)
- **Don't amplify** — if a prior agent inferred something, don't treat it as confirmed fact in downstream artifacts
- **Cite the chain** — when content comes from a prior agent rather than the source directly, cite both: `[From: User Stories → Source: Doc § X.Y]`

---

## 6. Quality Gate Integration

The `00-sprintweave-gates.md` quality checklist includes:
- `[x] No [UNVERIFIED] flags in output` — this check verifies grounding
- If `[UNVERIFIED]` items exist, the gate SHOULD flag them for review (not auto-reject)
- The gate reviewer decides whether unverified items are acceptable or need resolution

---

## Summary Checklist (For Every Agent, Every Output)

- [ ] Every procedure/requirement cites its source section
- [ ] No fabricated commands, IPs, hostnames, or config values
- [ ] Gaps in source coverage are explicitly reported
- [ ] `[INSERT]` placeholders used instead of invented specifics
- [ ] `[UNVERIFIED]` count included in Quality Summary
- [ ] `[INFERRED]` items clearly distinguished from direct extractions
- [ ] No content presented as fact that isn't in the source document
