---
description: "SprintWeave help, catalog, what can I do, available agents, first time, show options"
alwaysApply: false
---
# SprintWeave Welcome & Catalog

## When This Activates
Respond to:
- "What can SprintWeave do?"
- "What agents are available?"
- "Help", "SprintWeave help"
- "How do I generate stories/artifacts?"
- "Show me available artifacts"
- "What artifacts can I generate?"
- "Show [category] options" (e.g., "show design options", "show testing options")
- First-time interaction mentioning SprintWeave

## Response: Full Help

When user asks for general help or what SprintWeave can do, show the FULL CATALOG:

---

### SprintWeave - Document to SDLC Artifacts

Generate 61 artifact types from any technical document, right here in Cursor chat.

**Quick Start:** `Generate user stories from @your-file.pdf`

---

#### Requirements & Planning
| Artifact | Command |
|----------|---------|
| User Stories + Epics (with inline AC) | `Generate user stories from @doc` |
| Non-Functional Requirements | `Generate NFRs from @doc` |
| Sprint Plan | `Plan a sprint from these stories` |
| Story Estimation | `Estimate these stories` |
| Velocity Analysis | `Analyze velocity for sprint planning` |

#### Architecture & Design
| Artifact | Command |
|----------|---------|
| Architecture Decision Record | `Generate ADR from @doc` |
| API Specification | `Generate API spec from @doc` |
| Data Model / ERD | `Generate data model from @doc` |
| System Design | `Generate system design from @doc` |
| Sequence Diagram | `Generate sequence diagram from @doc` |

#### Implementation
| Artifact | Command |
|----------|---------|
| Technical Tasks | `Break stories into tech tasks` |
| Implementation Plan | `Generate implementation plan from @doc` |
| Dependency Graph | `Show task dependencies` |

#### Testing & Quality
| Artifact | Command |
|----------|---------|
| Test Cases | `Generate test cases from @doc` |
| BDD Scenarios | `Generate BDD scenarios from @doc` |
| Test Plan | `Generate test plan from @doc` |
| Integration Tests | `Generate integration tests from stories` |
| Performance Tests | `Generate performance test cases from @doc` |

#### Deployment & Operations
| Artifact | Command |
|----------|---------|
| Deployment Runbook | `Generate runbook from @doc` |
| Method of Procedure (MoP) | `Generate MoP from @doc` |
| Rollback Procedure | `Generate rollback procedure from @doc` |
| Release Notes | `Generate release notes from @doc` |
| Cloud Deployment MoP | `Generate cloud deployment MoP from @doc` |
| Deployment Input Files | `Generate deployment input files from @doc` |
| Cloud Troubleshooting Guide | `Generate cloud troubleshooting guide from @doc` |
| Ansible Playbook | `Convert this runbook to Ansible playbook` |
| Monitoring Config | `Generate monitoring config from @doc` |
| Alerting Rules | `Generate alerting rules from @doc` |
| SRE Runbook | `Generate SRE runbook from @doc` |
| SLOs / SLIs | `Define SLOs from @doc` |

#### Documentation
| Artifact | Command |
|----------|---------|
| User Manual | `Generate user manual from @doc` |
| Admin Guide | `Generate admin guide from @doc` |
| Training Material | `Generate training material from @doc` |
| FAQ | `Generate FAQ from @doc` |

#### Governance & Compliance
| Artifact | Command |
|----------|---------|
| Risk Assessment | `Generate risk assessment from @doc` |
| Compliance Checklist | `Generate compliance checklist from @doc` |
| Change Request | `Generate change request from @doc` |
| Impact Analysis | `Generate impact analysis from @doc` |

#### Proposal Response
| Artifact | Command |
|----------|---------|
| Proposal Outline | `Generate proposal outline from @rfp` |
| Compliance Matrix | `Generate compliance matrix from @rfp` |
| Executive Summary | `Generate executive summary from @rfp` |
| Technical Approach | `Generate technical approach from @rfp` |
| Win Themes | `Extract win themes from @rfp` |
| Clarification Requests | `Generate clarification questions from @rfp` |
| Management Approach | `Generate management approach from @rfp` |

#### RHOSO (Red Hat OpenStack Services on OpenShift)
| Artifact | Command |
|----------|---------|
| CIQ Parameter Reference | `Generate CIQ parameter reference from @cpat` |
| EDPM Topology Guide | `Generate EDPM topology guide for @topology` |
| Registration Input Files | `List registration input files from @cpat` |
| CIQ Field Guide | `Generate CIQ field guide from @cpat` |
| PDF-to-CIQ Gap Matrix | `Generate RHOSO PDF gap matrix from @RHOSO/` |
| CIQ Workbook (sample + template) | `Generate CIQ workbooks from @cpat` |
| CIQ Schema Code | `Generate CIQ schema code for [feature]` |
| CPAT Workflow MoP | `Generate CPAT deployment workflow from @cpat` |
| Manifest Catalog | `Generate manifest catalog from @cpat` |
| Deployment Task Brief | `Generate RHOSO deployment task brief from @cpat` |
| Cluster Commands Reference | `Generate cluster commands for @cpat` |
| CPAT Project Scaffold | `Scaffold CPAT project from @cpat` |
| CPAT Code Enhancement | `Add [feature] to CPAT codebase` |

#### NRHO (Nokia Red Hat OpenShift via CPAT)
| Artifact | Command |
|----------|---------|
| AIQ Parameter / Register Pack | `Generate NRHO AIQ field guide from @input/` |
| AIQ Workbooks | `Generate NRHO AIQ workbooks from @input/` |
| CPAT Workflow MoP | `Generate NRHO CPAT deployment workflow from @input/` |
| CPAT Project Scaffold | `Scaffold NRHO CPAT from @input/` |
| NRHO Confluence architecture | `Generate NRHO Confluence architecture page` |

#### Communication
| Artifact | Command |
|----------|---------|
| Stakeholder Update | `Generate stakeholder update from @doc` |
| Status Report | `Generate status report from @doc` |
| Release Notes (user-facing) | `Generate release notes for stakeholders` |

#### Pipelines (generate multiple at once)
| Pipeline | Command | What You Get |
|----------|---------|-------------|
| Standard | `Run pipeline on @doc` | Stories → Tests → Runbook → Sprint Plan |
| Full | `Run full pipeline on @doc` | All 15 agents, 61 artifacts |
| RHOSO | `Run RHOSO pipeline on @cpat` | CIQ workbooks + CPAT scaffold + Manifests + Tests + Docs |
| NRHO | `Run NRHO pipeline on @input/` | **NDA → NDE** (+ optional AUTO/QA/DOC) |
| NRHO Delivery | `Run nrho-delivery on @input/` | **NDA → AIQ → NDE → CPAT** |
| Proposal Response | `Run proposal pipeline on @rfp` | Outline + compliance + win themes + approach |
| Requirements + Design | `Run requirements and design pipeline on @doc` | Stories + ADRs + API specs + tasks |
| Testing + Deployment | `Run testing and deployment pipeline on @doc` | Tests + runbook + monitoring + alerts |
| Governance | `Run governance pipeline on @doc` | Risks + compliance + change request + impact |
| Documentation | `Run documentation pipeline on @doc` | User manual + admin guide + training + FAQ |

---

**Batch Processing (multiple documents at once):**
- Drop files into the `input/` folder, then reference the folder:
  - `"Generate user stories from @input/"` — all files combined as one input
  - `"Run pipeline on @input/"` — full pipeline on merged documents
  - `"Process each file in @input/ separately"` — per-file artifacts
- Single file still works: `"Generate stories from @input/specific-file.pdf"`

**After any generation:**
- Excel file auto-generated in `sprintweave-output/` (formatted .xlsx with filters)
- Refine: `"Split story #4"`, `"Add risk for X"`, `"Add endpoint for Y"`
- Export: `"Format for Jira"` / `"Format for Confluence"` / `"Give me JSON"`
- Chain: `"Now generate test cases from these stories"`

**Quality Gates (optional):**
- Enable: `"Configure gates"` or toggle in Canvas Dashboard
- Per-prompt: append `"with gates"` to any pipeline command
- Modes: pause-approve | pause-edit | checklist | all (strictest)
- Mid-gate: `"approve"`, `"approve all"`, `"skip"`, `"reject: [reason]"`

**Full catalog reference:** Open `CATALOG.md` in the file explorer for a printable version.

---

## Response: Category Browse

When user says "show [category] options", show only that category's table with detailed examples:

**Category keywords mapping:**
- "requirements" / "planning" / "stories" → Requirements & Planning section
- "design" / "architecture" / "API" → Architecture & Design section
- "implementation" / "tasks" / "dev" → Implementation section
- "testing" / "QA" / "test" → Testing & Quality section
- "deployment" / "operations" / "runbook" / "SRE" / "monitoring" → Deployment & Operations section
- "RHOSO" / "CIQ" / "EDPM" / "CPAT" / "OpenStack" / "manifest" / "scaffold" / "workbook" → RHOSO section
- "NRHO" / "AIQ" / "NDA" / "NDE" → NRHO section
- "documentation" / "manual" / "guide" / "FAQ" → Documentation section
- "governance" / "compliance" / "risk" / "change" → Governance & Compliance section
- "proposal" / "RFP" / "RFQ" / "RFI" / "bid" / "tender" / "compliance matrix" → Proposal Response section
- "communication" / "status" / "report" → Communication section

For category responses, include 2-3 real usage examples showing the kind of output they'll get.

---

## Response: First-Time Interaction

When this appears to be the user's FIRST interaction with SprintWeave (no prior artifacts generated in this chat):

Show a SHORT welcome + top 5 most common commands + Canvas mention:

```
Welcome to SprintWeave! Generate SDLC artifacts from any document in chat.

Visual Dashboard: Type "Open the SprintWeave dashboard" for a clickable launcher
Team Setup: Type "Setup SprintWeave for my team" to configure your domain/framework
Custom Agents: Type "Create a new agent for [domain]" to build your own
Quality Gates: Type "Configure gates" for manual review between pipeline stages

Most popular:
  1. Generate user stories from @input/
  2. Generate test cases from @input/
  3. Generate runbook from @input/
  4. Run full pipeline on @input/ (all artifacts at once)
  5. Run pipeline on @input/ with gates (manual review between stages)

Type "help" for the full catalog (61 artifact types).
Drop documents into input/ folder, then use @input/ — or reference a single file: @input/spec.pdf
```

## Canvas Dashboard Setup

When user says "Open the SprintWeave dashboard", "Create the dashboard", "Show me the canvas", or "I want the visual launcher":

1. Check if the canvas file already exists at the workspace's canvases directory
2. If not, create it by writing the `sprintweave-dashboard.canvas.tsx` file from `tools/sprintweave-dashboard.canvas.tsx` to the canvases directory
3. Provide the link to open it

The canvas path follows Cursor's internal workspace slug convention. To find the correct path, check `~/.cursor/projects/` for a folder matching the current workspace, then write to its `canvases/` subfolder. The source template is at `tools/sprintweave-dashboard.canvas.tsx`.

---

## Data Handling Disclosure

Always include at the bottom of help responses:

```
Privacy: Documents processed by Cursor's AI (same as your code).
PII (IPs, hostnames, credentials) auto-redacted from output.
Source Grounding (00-sprintweave-source-grounding.md):
  All output traceable to source — no hallucinated content.
  Unverifiable items flagged as [UNVERIFIED], gaps explicitly reported.
Requirement: Enable Privacy Mode for sensitive documents.
```
