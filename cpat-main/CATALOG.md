# SprintWeave — Artifact Catalog

**AI Agents That Turn Documents into Delivery-Ready Artifacts** | 15 agents, 61 artifacts, zero install

> **How to use:** Drop documents into the `input/` folder, then copy any command below into Cursor chat.
> Replace `@doc` with `@input/` (whole folder) or `@input/your-file.pdf` (specific file).
> 
> **Browse categories:** Type `"show [category] options"` in chat for detailed examples.

---

## Requirements & Planning

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 1 | User Stories + Epics (with inline AC) | `Generate user stories from @doc` | Requirements Analyst |
| 2 | Non-Functional Requirements | `Generate NFRs from @doc` | Requirements Analyst |
| 3 | Sprint Plan | `Plan a sprint from these stories` | Sprint Coach |
| 4 | Story Estimation | `Estimate these stories` | Sprint Coach |
| 5 | Velocity Analysis | `Analyze velocity for sprint planning` | Sprint Coach |

---

## Architecture & Design

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 6 | Architecture Decision Record | `Generate ADR from @doc` | Solution Architect |
| 7 | API Specification | `Generate API spec from @doc` | Solution Architect |
| 8 | Data Model / ERD | `Generate data model from @doc` | Solution Architect |
| 9 | System Design | `Generate system design from @doc` | Solution Architect |
| 10 | Sequence Diagram | `Generate sequence diagram from @doc` | Solution Architect |

---

## Implementation

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 11 | Technical Tasks | `Break stories into tech tasks` | Technical Lead |
| 12 | Implementation Plan | `Generate implementation plan from @doc` | Technical Lead |
| 13 | Dependency Graph | `Show task dependencies` | Technical Lead |

---

## Testing & Quality

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 14 | Test Cases | `Generate test cases from @doc` | QA Architect |
| 15 | BDD Scenarios | `Generate BDD scenarios from @doc` | QA Architect |
| 16 | Test Plan | `Generate test plan from @doc` | QA Architect |
| 17 | Integration Tests | `Generate integration tests from stories` | QA Architect |
| 18 | Performance Tests | `Generate performance test cases from @doc` | QA Architect |

---

## Deployment & Operations

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 19 | Deployment Runbook | `Generate runbook from @doc` | DevOps Engineer |
| 20 | Method of Procedure (MoP) | `Generate MoP from @doc` | DevOps Engineer |
| 21 | Rollback Procedure | `Generate rollback procedure from @doc` | DevOps Engineer |
| 22 | Release Notes | `Generate release notes from @doc` | DevOps Engineer |
| 23 | Cloud Deployment MoP | `Generate cloud deployment MoP from @doc` | Cloud Deployment Engineer |
| 24 | Deployment Input Files | `Generate deployment input files from @doc` | Cloud Deployment Engineer |
| 25 | Cloud Troubleshooting Guide | `Generate cloud troubleshooting guide from @doc` | Cloud Deployment Engineer |
| 26 | Ansible Playbook | `Convert this runbook to Ansible playbook` | Automation Engineer |
| 27 | Monitoring Config | `Generate monitoring config from @doc` | SRE Engineer |
| 28 | Alerting Rules | `Generate alerting rules from @doc` | SRE Engineer |
| 29 | SRE Runbook | `Generate SRE runbook from @doc` | SRE Engineer |
| 30 | SLOs / SLIs | `Define SLOs from @doc` | SRE Engineer |

---

## RHOSO (Red Hat OpenStack Services on OpenShift)

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 31 | CIQ Parameter Reference | `Generate CIQ parameter reference from @cpat` | RHOSO DA |
| 32 | EDPM Topology Guide | `Generate EDPM topology guide for @topology` | RHOSO DA |
| 33 | Registration Input Files | `List registration input files from @cpat` | RHOSO DA |
| 34 | CIQ Field Guide | `Generate CIQ field guide from @cpat` | RHOSO DA |
| 35 | PDF-to-CIQ Gap Matrix | `Generate RHOSO PDF gap matrix from @RHOSO/` | RHOSO DA |
| 36 | CIQ Workbook (sample + template) | `Generate CIQ workbooks from @cpat` | RHOSO DA |
| 37 | CIQ Schema Code | `Generate CIQ schema code for [feature]` | RHOSO DA |
| 38 | CPAT Workflow MoP | `Generate CPAT deployment workflow from @cpat` | RHOSO Deployment Engineer |
| 39 | Manifest Catalog | `Generate manifest catalog from @cpat` | RHOSO Deployment Engineer |
| 40 | Deployment Task Brief | `Generate RHOSO deployment task brief from @cpat` | RHOSO Deployment Engineer |
| 41 | Cluster Commands Reference | `Generate cluster commands for @cpat` | RHOSO Deployment Engineer |
| 42 | CPAT Project Scaffold | `Scaffold CPAT project from @cpat` | RHOSO Deployment Engineer |
| 43 | CPAT Code Enhancement | `Add [feature] to CPAT codebase` | RHOSO Deployment Engineer |

---

## Documentation

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 44 | User Manual | `Generate user manual from @doc` | Technical Writer |
| 45 | Admin Guide | `Generate admin guide from @doc` | Technical Writer |
| 46 | Training Material | `Generate training material from @doc` | Technical Writer |
| 47 | FAQ | `Generate FAQ from @doc` | Technical Writer |

---

## Governance & Compliance

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 48 | Risk Assessment | `Generate risk assessment from @doc` | Governance Specialist |
| 49 | Compliance Checklist | `Generate compliance checklist from @doc` | Governance Specialist |
| 50 | Change Request | `Generate change request from @doc` | Governance Specialist |
| 51 | Impact Analysis | `Generate impact analysis from @doc` | Governance Specialist |

---

## Proposal Response

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 52 | Proposal Outline | `Generate proposal outline from @rfp` | Proposal Writer |
| 53 | Compliance Matrix | `Generate compliance matrix from @rfp` | Proposal Writer |
| 54 | Executive Summary | `Generate executive summary from @rfp` | Proposal Writer |
| 55 | Technical Approach | `Generate technical approach from @rfp` | Proposal Writer |
| 56 | Win Themes | `Extract win themes from @rfp` | Proposal Writer |
| 57 | Clarification Requests | `Generate clarification questions from @rfp` | Proposal Writer |
| 58 | Management Approach | `Generate management approach from @rfp` | Proposal Writer |

---

## Communication & Reporting

| # | Artifact | Command | Agent |
|---|----------|---------|-------|
| 59 | Stakeholder Update | `Generate stakeholder update from @doc` | Project Manager |
| 60 | Status Report | `Generate status report from @doc` | Project Manager |
| 61 | Release Notes (user-facing) | `Generate release notes for stakeholders` | Project Manager |

---

## Pipelines (Multiple Artifacts at Once)

| Pipeline | Command | What You Get |
|----------|---------|-------------|
| **Standard** | `Run pipeline on @doc` | Stories → Tests → Runbook → Sprint Plan |
| **Full** | `Run full pipeline on @doc` | All 15 agents, 61 artifacts |
| **RHOSO** | `Run RHOSO pipeline on @cpat` | CIQ (9 tables, 82 params) + Manifests (15 templates) + Tests + Docs |
| **RHOSO Delivery** | `Run rhoso-delivery on @input/` | CIQ Params + CIQ Workbooks + Workflow MoP + CPAT Scaffold (~100 defaults) |
| **Proposal Response** | `Run proposal pipeline on @rfp` | Outline + Compliance + Win Themes + Approach |
| **Requirements + Design** | `Run requirements and design pipeline on @doc` | Stories + ADRs + API specs + tasks |
| **Testing + Deployment** | `Run testing and deployment pipeline on @doc` | Tests + runbook + monitoring + alerts |
| **Governance** | `Run governance pipeline on @doc` | Risks + compliance + change request + impact |
| **Documentation** | `Run documentation pipeline on @doc` | User manual + admin guide + training + FAQ |

| **Custom** | `Run [name] on @doc` | Your defined agent sequence |

### Pipeline Manager

| Action | Command |
|--------|---------|
| Open wizard | `Manage pipelines` |
| Create | `Create a custom pipeline with REQ, QA, OPS named "Quick Validate"` |
| Edit | `Edit pipeline [name]` |
| Delete | `Delete pipeline [name]` |
| Hide built-in | `Hide pipeline [name]` |
| Promote | `Promote pipeline [name]` |
| Restore all | `Restore default pipelines` |
| Sync to canvas | `python tools/sync-pipeline-config.py` |

Custom pipelines persist in `context/pipelines.yaml`. The Canvas dashboard Pipeline Manager provides visual create/edit/copy/delete/promote/restore actions.

---

## Output — Excel Auto-Generated

Every generation automatically produces a formatted `.xlsx` file in `sprintweave-output/`:
- One sheet per artifact type (Stories, Tests, Risks, etc.)
- Headers, auto-filters, alternating rows, priority color coding
- Summary sheet with source info and row counts
- **One-time setup:** `pip install openpyxl`

## After Generation (Works with Any Artifact)

| Action | Command |
|--------|---------|
| Refine | `"Split story #4"`, `"Add risk for [scenario]"`, `"Tighten SLO to 99.99%"` |
| Export to JSON | `"Give me JSON"` |
| Export to Jira | `"Format for Jira"` |
| Export to Confluence | `"Format for Confluence"` |
| Run next agent | `"Now generate test cases from these stories"` |

---

## Multiple Documents

You can reference multiple files in a single request:

| Pattern | Example |
|---------|---------|
| **Combine** (merge into one output) | `Generate stories from @requirements.pdf and @architecture.docx` |
| **Compare** (find differences) | `Compare @old-spec.pdf with @new-spec.pdf and show changes` |
| **Complement** (enrich from multiple sources) | `Generate runbook from @design.pdf @config.md @network.pptx` |
| **Add context** (after initial generation) | `Also consider @meeting-notes.md` |

Each artifact will cite which document it came from. Conflicts between documents are flagged automatically.

---

## Tips

- **First time?** Just type: `Generate user stories from @your-file.pdf`
- **Multiple docs?** Just add more: `@doc1.pdf @doc2.docx @doc3.md`
- **Not sure which agent?** Type: `What can SprintWeave do?`
- **Large document?** Say: `Process only section 3 from @doc`
- **Want everything?** Say: `Run full pipeline on @doc`
- **Customize output?** Edit `context/team-config.yaml` for your team
