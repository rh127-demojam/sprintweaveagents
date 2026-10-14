# GTS Innovation & Automation Dashboard

> **Single-page Confluence dashboard** — all initiative progress, savings, readiness, and executive metrics in one place.

---

## Section 0 — Welcome & Baseline

Welcome to the **GTS Innovation & Automation Hub**. This space serves as the central repository for all innovation and automation initiatives driven by the GTS team. Here you will find summaries of current initiatives, roadmaps of automation features delivered, sprint progress, and key metrics — providing a single view into the work being done to accelerate telco cloud deployments.

**The Innovation and Automation Team of Global Telco Services (GTS)** is a specialized team within Red Hat that delivers end-to-end customization, automation, AI-driven engineering, and deployment solutions of cloud infrastructure for telcos worldwide.

> Upload `sprintweave-architecture-diagram.png` from the Dashboard folder to Confluence: drag-and-drop the image onto the page or use **+** → **Files and images** → upload.

### The Baseline

> Add as an **Info macro** (`/info`):

All savings and comparisons on this dashboard measure against one consistent baseline:

```
BASELINE = Manually developing CPAT (writing playbooks, schemas, templates, Flask/React app by hand)
COMPARISON = SprintWeave-generated CPAT (RDA + RDE agents auto-generate the same 10 components)
```

| | WITHOUT SprintWeave (Baseline) | WITH SprintWeave (This Initiative) |
|---|---|---|
| **What** | Build CPAT manually — playbooks, schemas, templates, app, container | SprintWeave agents generate CPAT automatically |
| **Who** | Engineers writing code by hand | RDA Agent (blueprinting) + RDE Agent (deployment) |
| **How long** | Weeks to months per component | Days — agents generate from docs/schemas |
| **Delivery** | Customer waits for manual CPAT build | CPAT ready faster — customer gets automation sooner |

> **Note:** NCS was deployed using NDAT, CBIS using CDAT — legacy tools built entirely manually (no agents). The baseline comparison applies only to CPAT (RHOSO/NRHO). Legacy tools appear in Section 4 for project-level deployment savings context.

---

## Section 1 — Executive Summary

> Use a **4-column layout** (`/layout` → 4 columns) with colored **Panel macros** (`/panel`).

**Column 1 — Initiative Status** (Green panel)

```
SprintWeave: DELIVERED (100%)
RDA Agent: IN PROGRESS
RDE Agent: IN PROGRESS
CPAT v1.0: Oct 2026
```

> Auto-fetch with JIRA count macros:

| Metric | JQL |
|--------|-----|
| SprintWeave Done | `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain) AND statusCategory = Done` |
| RDA Done / Total | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) AND statusCategory = Done` / `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq)` |
| RDE Done / Total | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) AND statusCategory = Done` / `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` |

**Column 2 — CPAT Dev Savings** (Blue panel)

```
Heading 1: <Z>% faster
Body: CPAT development effort reduced from <X> to <Y> MWD
      using SprintWeave agents (RDA + RDE)
Source: DB2 Section A totals
```

**Column 3 — Deployment Impact** (Purple panel)

```
Heading 1: 265+ clusters
Body: Total clusters automated across NCS + CBIS
      <Z> MWW total savings
Source: DB1 Calculate → Sum
```

**Column 4 — Delivery Speed** (Yellow panel)

```
Heading 1: 3 weeks faster
Body: CPAT delivered 3 weeks sooner than manual estimate
Source: DB2 Section B
```

### Product Status at a Glance

| Product | Tool | Built With | Status | Clusters | CPAT Dev Savings | Deployment Savings |
|---------|------|------------|--------|----------|------------------|--------------------|
| **NCS** | NDAT | Manual | Delivered | 228 | N/A (legacy) | from DB1 |
| **CBIS** | CDAT + AAP | Manual | Delivered | 37 | N/A (legacy) | from DB1 |
| **NRHO** | CPAT (adapted) | SprintWeave | Delivered (NAM) | from DB1 | from DB2 | from DB1 |
| **RHOSO** | CPAT | SprintWeave (RDA+RDE) | In Progress | — | from DB2 | — |

---

## Section 2 — Development Progress

### Current Initiatives

| Project | Description | Platform | Status | JIRA |
| --- | --- | --- | --- | --- |
| **SprintWeave Framework** | AI-powered SDLC agent framework with Cursor-based intelligent agents, pipeline orchestration, quality gates, and canvas dashboard | Cursor AI | Done | [TMERAWORK1 Epics](https://issues.redhat.com/issues/?jql=project%20%3D%20TMERAWORK1%20AND%20type%20%3D%20Epic%20AND%20labels%20in%20(sprintweave-core%2C%20sprintweave-engine%2C%20sprintweave-tools%2C%20sprintweave-domain)) |
| **RHOSO Deployment Engineer (RDE) Agent** | Deployment Automation — Ansible manifest generation, workflows, Flask/React UI, and containerized toolchain for RHOSO | RHOSO | In Progress | [TMERAWORK1 Epics](https://issues.redhat.com/issues/?jql=project%20%3D%20TMERAWORK1%20AND%20type%20%3D%20Epic%20AND%20labels%20in%20(rhoso-ansible%2C%20rhoso-manifests%2C%20rhoso-app)) |
| **RHOSO Design Architect (RDA) Agent** | Blueprinting Engine — CIQ schema design & validation, workbook generation & parsing, gap analysis, deployment-ready configurations | RHOSO | In Progress | [TMERAWORK1 Epics](https://issues.redhat.com/issues/?jql=project%20%3D%20TMERAWORK1%20AND%20type%20%3D%20Epic%20AND%20labels%20in%20(rhoso-schema%2C%20rhoso-ciq)) |
| **→ CPAT** | **Output:** Cloud Platform Automation Tool — the combined product of RDA (Blueprinting) + RDE (Deployment Automation). Future: NRHO, OCP, AAP | RHOSO (current) | In Progress | [All CPAT Tickets](https://issues.redhat.com/issues/?jql=project%20%3D%20TMERAWORK1%20AND%20labels%20%3D%20rhoso-cpat) |

### Initiative Panels

> Use a **3-column layout** (`/layout` → 3 columns) with **Panel macros** (`/panel`).

**Column 1 — SprintWeave** (Blue panel)

Panel title: **SprintWeave Framework**

|               |                       |
| ------------- | --------------------- |
| **Platform**  | Cursor AI             |
| **Delivered** | Jun 15 – Jul 31, 2026 |
| **Status**    | Done                  |

**Scope (use JIRA count macros — set Display → "Total issue count"):**

| Metric | JQL |
| --- | --- |
| Epics | `project = TMERAWORK1 AND type = Epic AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` |
| Stories | `project = TMERAWORK1 AND type = Story AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` |
| Sub-tasks | `project = TMERAWORK1 AND type = Sub-task AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` |
| **Total** | `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` |

**Key Capabilities:** Rules-based multi-agent architecture, Pipeline engine, Quality/security gates, Canvas dashboard, Artifact export, Context management, Custom agent & skill system

**Column 2 — RDA Agent** (Yellow panel)

Panel title: **RHOSO Design Architect (RDA) Agent → Blueprinting Engine**

|                |                       |
| -------------- | --------------------- |
| **Powered by** | SprintWeave Framework |
| **Platform**   | RHOSO                 |
| **Status**     | In Progress           |

**Scope:**

| Metric | JQL |
| --- | --- |
| Epics | `project = TMERAWORK1 AND type = Epic AND labels in (rhoso-schema, rhoso-ciq)` |
| Stories | `project = TMERAWORK1 AND type = Story AND labels in (rhoso-schema, rhoso-ciq)` |
| Sub-tasks | `project = TMERAWORK1 AND type = Sub-task AND labels in (rhoso-schema, rhoso-ciq)` |
| **Total** | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq)` |

**Progress:**

| Status | JQL |
| --- | --- |
| Done | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) AND statusCategory = Done` |
| In Progress | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) AND statusCategory = "In Progress"` |
| Pending | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) AND status = "Pending"` |

**Key Capabilities:** CIQ Schema & Validation (152+ params, 40+ types), CIQ Workbook Generation & Parsing, Project-Specific CIQ Generation, Gap Analysis & Schema Extension

**Column 3 — RDE Agent** (Green panel)

Panel title: **RHOSO Deployment Engineer (RDE) Agent → Deployment Automation**

|                |                       |
| -------------- | --------------------- |
| **Powered by** | SprintWeave Framework |
| **Platform**   | RHOSO (current)       |
| **Target**     | Oct 2026              |
| **Status**     | In Progress           |

**Scope:**

| Metric | JQL |
| --- | --- |
| Epics | `project = TMERAWORK1 AND type = Epic AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` |
| Stories | `project = TMERAWORK1 AND type = Story AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` |
| Sub-tasks | `project = TMERAWORK1 AND type = Sub-task AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` |
| **Total** | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` |

**Progress:**

| Status | JQL |
| --- | --- |
| Done | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) AND statusCategory = Done` |
| In Progress | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) AND statusCategory = "In Progress"` |
| Pending | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) AND status = "Pending"` |

**Key Capabilities:** Ansible CIQ Context Loading, Manifest Generation (CP, DP, Network, Disconnected), Ansible Workflow & Orchestration, Flask Backend REST API, React Frontend UI, Container Build & Lifecycle

> **CPAT** = the combined output of RDA (Blueprinting) + RDE (Deployment Automation). Future: NRHO, OCP, AAP.

### JIRA Charts

> Use a **3-column layout** for Row 1, **2-column layout** for Row 2. Type `/jira chart` → configure as below. Width: **400**, Height: **300**.

**Row 1 — Status by Project (3-column):**

| Column | Chart Title | Type | JQL | Statistic |
| --- | --- | --- | --- | --- |
| Left | SprintWeave Framework | Pie Chart | `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` | Statuses |
| Center | RDA Agent (Blueprinting) | Pie Chart | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq)` | Statuses |
| Right | RDE Agent (Deployment) | Pie Chart | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app)` | Statuses |

**Row 2 — Overall (2-column):**

| Column | Chart Title | Type | JQL | Config |
| --- | --- | --- | --- | --- |
| Left | All Tickets by Priority | Pie Chart | `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library)` | Statistic: Priorities |
| Right | Created vs Resolved (8 weeks) | Created vs Resolved | `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library)` | Period: Weekly, Days: 56 |

### JIRA Issue Tables

> Use **Expand macros** (`/expand`) for each table to keep the page clean.

**Expand: "CPAT Open Issues"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library) AND statusCategory != Done ORDER BY priority DESC`
Columns: Key, Summary, Status, Priority, Assignee | Max: 30

**Expand: "All Epics (28)"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library) AND type = Epic ORDER BY key ASC`
Columns: Key, Summary, Status, Labels, Story Points | Max: 28

**Expand: "In Progress Now"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library) AND statusCategory = "In Progress" ORDER BY priority DESC`
Columns: Key, Summary, Status, Priority, Assignee | Max: 30

**Expand: "Recently Completed"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (NF_GTS, NF_Library) AND statusCategory = Done ORDER BY updated DESC`
Columns: Key, Summary, Updated, Assignee | Max: 20

**Expand: "RDA Agent Tickets"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) ORDER BY status ASC`

**Expand: "RDE Agent Tickets"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) ORDER BY status ASC`

**Expand: "SprintWeave Tickets (All Done)"**

Type `/jira` → JQL: `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)`

### Epic Breakdown

> Use **Expand macros** for each workstream.

**Expand: "SprintWeave Framework — 11 Epics (108 SP) — All Complete"**

| Epic | JIRA Key | Stories | Sub-tasks | Total | SP |
| --- | --- | --- | --- | --- | --- |
| Framework Core Architecture | TMERAWORK1-356 | 3 | 6 | 10 | 11 |
| Agent Definition Framework | TMERAWORK1-381 | 3 | 5 | 9 | 16 |
| Context & Knowledge Management | TMERAWORK1-382 | 2 | 2 | 5 | 5 |
| Pipeline Engine & Orchestrator | TMERAWORK1-383 | 2 | 4 | 7 | 8 |
| Quality, Security & Gate System | TMERAWORK1-384 | 4 | 2 | 7 | 12 |
| Artifact Export & Excel Generation | TMERAWORK1-385 | 3 | 1 | 5 | 11 |
| Custom Agent & Skill System | TMERAWORK1-386 | 2 | 2 | 5 | 6 |
| Canvas Dashboard | TMERAWORK1-387 | 2 | 2 | 5 | 8 |
| Domain Agent Rules & Templates | TMERAWORK1-388 | 2 | 6 | 9 | 10 |
| Domain Pipeline Configuration | TMERAWORK1-389 | 3 | 0 | 4 | 5 |
| Agent Knowledge Enhancement from Reference Deployments | TMERAWORK1-390 | 4 | 6 | 11 | 16 |
| **Total** | | **30** | **36** | **77** | **108** |

**Expand: "RDA Agent — 7 Epics (74 SP)"**

| Epic | JIRA Key | Status | Stories | Sub-tasks | Total | SP |
| --- | --- | --- | --- | --- | --- | --- |
| CIQ Schema & Validation Framework | TMERAWORK1-391 | Done | 5 | 3 | 9 | 16 |
| CIQ Excel Workbook Generation | TMERAWORK1-393 | Done | 3 | 0 | 4 | 11 |
| CIQ Workbook Parser with Header Normalization | TMERAWORK1-392 | Done | 3 | 0 | 4 | 10 |
| CIQ Input Validation in Ansible Pipeline | TMERAWORK1-394 | Done | 1 | 0 | 2 | 5 |
| Project-Specific CIQ Generation from Existing Deployments | TMERAWORK1-395 | In Progress | 3 | 0 | 4 | 11 |
| RHOSO Documentation Gap Analysis & Schema Extension | TMERAWORK1-396 | In Progress | 3 | 0 | 4 | 13 |
| RHOSO Lab Requirements Documentation | TMERAWORK1-397 | In Progress | 2 | 0 | 3 | 8 |
| **Total** | | | **20** | **3** | **30** | **74** |

**Expand: "RDE Agent — 10 Epics (114 SP)"**

| Epic | JIRA Key | Status | Stories | Sub-tasks | Total | SP |
| --- | --- | --- | --- | --- | --- | --- |
| Ansible CIQ Context Loading & Variable Defaults | TMERAWORK1-398 | Done | 2 | 6 | 9 | 10 |
| RHOSO Network Infrastructure Manifest Generation | TMERAWORK1-399 | Done | 1 | 4 | 6 | 8 |
| Jinja2 Boolean Coercion Bug Fix | TMERAWORK1-406 | Done | 1 | 3 | 5 | 3 |
| OpenStack Control Plane Manifest Generation | TMERAWORK1-400 | Done | 3 | 10 | 14 | 18 |
| RHOSO Data Plane Manifest Generation | TMERAWORK1-401 | Done | 3 | 7 | 11 | 18 |
| Disconnected Environment Manifest Generation | TMERAWORK1-405 | Done | 1 | 3 | 5 | 5 |
| Ansible Deployment Workflow & Task Orchestration | TMERAWORK1-402 | Done | 3 | 11 | 15 | 15 |
| CPAT Flask Backend REST API | TMERAWORK1-403 | In Progress | 3 | 7 | 11 | 14 |
| CPAT React Frontend UI | TMERAWORK1-404 | In Progress | 3 | 8 | 12 | 18 |
| Container Build & Lifecycle Management | TMERAWORK1-407 | Pending | 1 | 3 | 5 | 5 |
| **Total** | | | **21** | **62** | **93** | **114** |

### Timeline & Milestones

> Use an **Expand macro** titled "Timeline & Milestones".

**Timeline: Jun 2026 – Oct 2026**

| Phase | Start | End | Duration | Status |
| --- | --- | --- | --- | --- |
| **SprintWeave Framework** | Jun 15, 2026 | Jul 31, 2026 | 7 weeks | Done |
| **RDA Agent** | Aug 3, 2026 | Sep 10, 2026 | 5.5 weeks | In Progress |
| **RDE Agent** | Aug 3, 2026 | Oct 9, 2026 | 10 weeks | In Progress |

**Key Milestones:**

| Milestone | Date | Status |
| --- | --- | --- |
| SprintWeave Framework Complete | Jul 31, 2026 | Done |
| CIQ Schema & Parser Ready | Aug 18, 2026 | Done |
| All Manifest Templates Complete | Sep 5, 2026 | Done |
| **CPAT v1.0 Release Ready** | **Oct 9, 2026** | **Pending** |

### Overall Progress Metrics

| Metric | Value |
| --- | --- |
| **Total Epics** | 28 |
| **Total Stories** | 71 |
| **Total Sub-tasks** | 101 |
| **Total Tickets** | 200 |
| **Total Story Points** | 296 |
| **Completion** | 79% |
| **Projected Completion** | Oct 2026 |

**Status Distribution:**

| Status | Epics | Tickets |
| --- | --- | --- |
| Done | 17 | 114 |
| In Progress | 6 | 40 |
| Pending | 5 | 46 |
| **Total** | **28** | **200** |

---

## Section 3 — CPAT Development Savings

> **Baseline comparison section.** This is where the Manual CPAT vs SprintWeave CPAT comparison is shown.

> Add as an **Info macro** (`/info`):
> **Baseline:** Manual CPAT development — engineers writing playbooks, schemas, templates, Flask/React app by hand
> **Comparison:** SprintWeave-generated CPAT — RDA + RDE agents auto-generating the same 10 components

### KPI Panels

> Use a **3-column layout** with **Panel macros**.

**Column 1 — Manual CPAT Development** (Red panel)

```
Heading 1: <X> MWD
Body: Total effort to build CPAT from scratch manually
10 components — all hand-coded
```

**Column 2 — SprintWeave CPAT Development** (Green panel)

```
Heading 1: <Y> MWD
Body: Total effort with SprintWeave agents (RDA + RDE)
10 components — auto-generated
```

**Column 3 — Effort Reduction** (Blue panel)

```
Heading 1: <Z>% faster
Body: SprintWeave saves <X-Y> MWD in building CPAT
```

> Values read from DB2 Section A **Calculate → Sum** totals at the bottom of the table.

### Dev Effort Comparison Chart

> Google Sheets chart embedded as iframe (see Google Sheets Iframes section below).

1. Chart is created in Google Sheets from the "CPAT Development Efforts" data in the Statistical Data sheet
2. Grouped bar chart: each component shows two bars — Manual (red) vs SprintWeave (green)
3. The gap between bars = effort saved
4. Embed via `/iframe` macro in Confluence — chart auto-updates when you edit Google Sheets

### Component Effort Table

> Google Sheets cell range embedded as iframe — shows live data from the spreadsheet.

Shows all 10 CPAT components with: CPAT Component, Agent, Manual Dev (MWD), SprintWeave Dev (MWD), Effort Saved (MWD), Effort Saved %, What SprintWeave Does

### Side-by-Side Comparison (Static Table)

| Dimension | Manual CPAT Development | SprintWeave-Generated CPAT |
|-----------|------------------------|---------------------------|
| **Who builds** | Engineers manually | SprintWeave agents (RDA + RDE) |
| **CIQ Schema** | Manual — weeks of effort | RDA Agent: 152+ params, 40+ types, regex |
| **CIQ Workbooks** | Manual Excel creation | RDA Agent: auto-generated with validation |
| **Blueprinting** | Manual gap analysis | RDA Agent: structured blueprints + gap analysis |
| **Playbooks & Templates** | From scratch | RDE Agent: 18 tasks, 15 templates, ~100 defaults |
| **Web Application** | Manual Flask + React | RDE Agent: 18 routes, 11 components |
| **Container Packaging** | Manual Dockerfile | RDE Agent: Dockerfile, entrypoint, bringup |
| **Total dev effort** | `<X>` MWD | `<Y>` MWD — **`<Z>%` reduction** |

---

## Section 4 — Project Deployment Savings

> Per-cluster effort savings in actual customer projects using automation.

### KPI Panels

> Use a **3-column layout** with **Panel macros**.

**Column 1 — Clusters Automated** (Blue panel)

```
Heading 1: 265+
Body: Total clusters deployed using automation across NCS + CBIS
```

**Column 2 — Effort Saved** (Green panel)

```
Heading 1: 265 MWW
Body: Total Man-Working-Weeks saved across all projects
```

**Column 3 — Average Savings** (Purple panel)

```
Heading 1: 50%
Body: Average per-cluster effort reduction with automation
```

> Values read from DB1 column-level **Calculate → Sum/Average** summaries.

### Charts

> Use a **2-column layout**. Both charts are Google Sheets iframes (see Google Sheets Iframes section below).

**Left column — Savings by Project (Bar chart):**

1. `/iframe` → paste the published Savings by Project bar chart URL from Google Sheets

**Right column — Savings by Product (Pie chart):**

1. `/iframe` → paste the published Savings by Product pie chart URL from Google Sheets

> Both charts auto-update when you edit the Google Sheet.

### Detailed Project Table

> Google Sheets cell range iframe showing Project Delivery Savings data (wrap in **Expand macro** titled "Detailed Project Data" if you want it collapsible).

Shows: Project, Customer, Product, Release, Clusters, WITHOUT (MWD), WITH (MWD), Savings (MWD), Savings %, Total Savings (MWW)

### Important Note

> Add as an **Info macro** (`/info`):

The savings shown represent the total cluster-level savings achieved through automation. This initiative accelerated the **availability** of automation. Without it, automation would have arrived later and a portion of clusters would have been deployed manually. Since we cannot predict which clusters would have gone manual, the tables show the **full automation savings with this contextual note**.

---

## Section 5 — CPAT Delivery Readiness

> From the moment an automation requirement comes in, how fast do we deliver CPAT?

### KPI Panels

> Use a **2-column layout** with **Panel macros**.

**Column 1 — Manual Lead Time** (Red panel)

```
Heading 1: 4 weeks
Body: Estimated lead time to deliver CPAT manually
```

**Column 2 — SprintWeave Lead Time** (Green panel)

```
Heading 1: 1 week
Body: Actual lead time from requirement to CPAT delivery
Lead time saved: 3 weeks
```

### What the Lead Time Covers

> Use an **Expand macro** titled "Lead Time Activities — Manual vs SprintWeave"

**Manual Lead Time (4 weeks):**

| Week | Activity |
|------|----------|
| Week 1 | Requirements gathering, architecture review, CIQ design from scratch |
| Week 2 | Hand-code playbooks, templates, defaults; write Jinja2 manifests |
| Week 3 | Build Flask API routes, React UI components, container packaging |
| Week 4 | Integration testing, validation, customer-specific fixes, handover |

**SprintWeave Lead Time (1 week):**

| Day | Activity |
|-----|----------|
| Day 1-2 | **Agent fine-tuning** — Adapt RDA/RDE agent rules and knowledge base to match customer-specific requirements (deployment mode, network topology, storage backend, service selection). Update CIQ schema if new parameters are needed. |
| Day 3 | **Agent execution** — Run RDA Agent (CIQ schema → workbook → parser → blueprinting) + RDE Agent (playbooks → templates → defaults → API → UI → container). Agents generate all 10 CPAT components. |
| Day 4 | **Validation & testing** — Verify generated manifests against customer architecture, run playbook dry-runs, validate CIQ inputs, review generated code. |
| Day 5 | **Handover** — Package CPAT container, deliver to customer, walkthrough of CIQ inputs and deployment workflow. |

**Agent fine-tuning highlights:**
- Update agent context files with customer-specific RHOSO documentation and deployment guides
- Adjust CIQ schema parameters for customer's infrastructure (e.g., add new Cinder driver, custom network config)
- Tune template generation rules if customer needs non-standard manifest patterns
- Feed reference deployments from similar customers into agent knowledge base for improved output quality
- Fine-tuning is a **1-2 day activity** — not rebuilding agents, just adjusting their inputs and rules

### End-to-End Delivery Timeline — Requirement to Initial CPAT Cut

> Use an **Expand macro** titled "Full Delivery Timeline — Requirement to Production-Ready CPAT"

The lead times in Table 3 (1 week SprintWeave / 4 weeks manual) cover **our-side CPAT work only**. The full end-to-end timeline adds requirements gathering, customer environment readiness, and handover.

**SprintWeave E2E Timeline (~2 weeks):**

| Phase | Day | Duration | Owner | Activities | Parallel? |
|-------|-----|----------|-------|------------|-----------|
| **1. Requirements Gathering** | Day 1-3 | 3 days | GTS + Customer | Collect deployment architecture (connected/disconnected, storage, network topology, compute scale). Receive customer RHOSO docs, HLD, network diagrams. | — |
| **2. Agent Fine-tuning** | Day 2-4 | 2 days | GTS (DA/DE) | Adapt RDA/RDE agent rules and knowledge base. Update CIQ schema if new parameters needed. Feed customer reference docs into agent context. | Overlaps Phase 1 |
| **3. CPAT Generation** | Day 4-5 | 1 day | SprintWeave Agents | Run RDA Agent (schema → workbook → parser → blueprinting) + RDE Agent (playbooks → templates → defaults → API → UI → container). | — |
| **4. CIQ Population** | Day 4-6 | 2 days | GTS + Customer | Fill CIQ workbook with customer-specific values (IPs, VLANs, hostnames, credentials, storage config). Validate inputs against schema. | Overlaps Phase 3 |
| **5. Validation & Testing** | Day 6-7 | 2 days | GTS (DE) | Verify generated manifests against customer architecture. Playbook dry-runs. CIQ validation. Fix any mismatches. | — |
| **6. Customer Env Readiness** | Day 1-7 | 5 days | Customer + GTS | RHOCP cluster running (OCP 4.14+), bastion with Podman, kubeconfig, pull-secret, SSH keys, network connectivity. | **Fully parallel** with Phases 1-5 |
| **7. Handover & Onboarding** | Day 8-9 | 2 days | GTS → Customer | Deploy CPAT container on bastion. Walkthrough of CIQ, deployment workflow, manifest review. First dry-run. | — |
| | | **~2 weeks (9 working days)** | | | |

> Our-side work (Phases 2-5) = **5 days = 1 week** — matches Table 3 SprintWeave lead time.
> Matches Table 2: SprintWeave = 9 MWD — includes agent fine-tuning + generation + validation overhead.

**Manual E2E Timeline (~5 weeks):**

| Phase | Day | Duration | Owner | Activities | Parallel? |
|-------|-----|----------|-------|------------|-----------|
| **1. Requirements Gathering** | Day 1-3 | 3 days | GTS + Customer | Same as SprintWeave — architecture review, docs collection. | — |
| **2. CIQ Schema Design** | Day 4-7 | 4 days | GTS (DA) | Design 13 input tables, 152+ parameters, type definitions, regex validation — all from scratch. | — |
| **3. CIQ Workbook & Parser** | Day 6-9 | 4 days | GTS (DA) | Build Excel workbook generator, parser with header normalization. | Overlaps Phase 2 |
| **4. Blueprinting** | Day 9-11 | 3 days | GTS (DA) | Gap analysis framework, project-specific CIQ generation. | — |
| **5. Playbooks & Templates** | Day 11-16 | 6 days | GTS (DE) | Hand-code 18 task files, 15 Jinja2 templates for all deployment phases. | — |
| **6. Defaults & Variables** | Day 15-16 | 2 days | GTS (DE) | Write ~100 defaults from CIQ parameter types. | Overlaps Phase 5 |
| **7. Flask Backend API** | Day 17-19 | 3 days | GTS (DE) | Build 18 routes with streaming, deployment management. | — |
| **8. React Frontend UI** | Day 18-19 | 2 days | GTS (DE) | Build 11 components with Vite. | Overlaps Phase 7 |
| **9. Container Packaging** | Day 20 | 1 day | GTS (DE) | Dockerfile, entrypoint, bringup script. | — |
| **10. Integration Testing** | Day 20-22 | 3 days | GTS (DE) | End-to-end testing, CIQ validation, manifest verification, bug fixes. | — |
| **11. Customer Env Readiness** | Day 1-7 | 5 days | Customer + GTS | Same as SprintWeave — RHOCP cluster, bastion, credentials. | **Fully parallel** with Phases 1-10 |
| **12. Handover & Onboarding** | Day 23-24 | 2 days | GTS → Customer | Same as SprintWeave — deploy, walkthrough, first run. | — |
| | | **~5 weeks (24 working days)** | | | |

> Our-side work (Phases 2-10) = **~20 days = 4 weeks** — matches Table 3 Manual lead time.
> Matches Table 2: Manual = 25 MWD (5 weeks sequential, compressed to 4 weeks calendar with parallelism).

**Side-by-side timeline view:**

```
                    Week 1          Week 2          Week 3          Week 4          Week 5
                    D1--D5          D6--D10         D11-D15         D16-D20         D21-D25

SPRINTWEAVE:
Requirements        [======]
Agent Fine-tuning     [======]
CPAT Generation          [===]
CIQ Population           [======]
Validation                    [======]
Customer Env Ready  [=========================]  (parallel)
Handover                              [=====]
                                           ^ CPAT READY (Day 9)

MANUAL:
Requirements        [======]
CIQ Schema Design       [=========]
CIQ Workbook/Parser      [=========]
Blueprinting                    [======]
Playbooks/Templates                 [===============]
Defaults/Variables                          [====]
Flask API                                       [======]
React UI                                         [====]
Container                                             [=]
Integration Test                                      [======]
Customer Env Ready  [=============]  (parallel)
Handover                                                   [=====]
                                                                ^ CPAT READY (Day 24)
```

**Summary:**

| Metric | SprintWeave | Manual | Savings |
|--------|-------------|--------|---------|
| Requirements Gathering | 3 days | 3 days | Same |
| **Our-side CPAT work (Table 3)** | **5 days (1 wk)** | **20 days (4 wks)** | **3 weeks** |
| Customer Env Readiness | 5 days (parallel) | 5 days (parallel) | Same |
| Handover & Onboarding | 2 days | 2 days | Same |
| **E2E Total** | **~2 weeks** | **~5 weeks** | **~3 weeks saved** |
| **Key accelerator** | Agents generate 10 components in 1 day | Engineers hand-code each component over 3+ weeks | — |

> **Consistency check:** Table 2 (25 MWD manual / 10 MWD SprintWeave) → Table 3 (4 wks / 1 wk our-side) → E2E (5 wks / 2 wks total). All aligned.

### Lead Time Comparison Chart

> Google Sheets chart embedded as iframe (see Google Sheets Iframes section below).

1. `/iframe` → paste the published Lead Time Comparison bar chart URL from Google Sheets
2. Each customer shows two bars: Manual Estimate vs Actual Lead Time
3. Chart auto-updates when you edit the Google Sheet

### Customer Delivery Table

> Google Sheets cell range iframe showing Customer Readiness data.

Shows: Customer/Project, Product, Release, Lead Time (Wks), Manual Estimate (Wks), Lead Time Saved (Wks)

---

## Section 6 — Blueprint Reuse & Legacy

### Blueprint Availability

| Product | Release | CPAT Components Ready | Built By | Delivery Lead Time | Reused From |
|---------|---------|----------------------|----------|-------------------|-------------|
| RHOSO | 18.0 | Full CPAT stack (CIQ + Playbooks + Templates + App + Container) | SprintWeave agents (RDA + RDE) | `<weeks>` | New — from RHOSO docs |
| NRHO | — | Full CPAT adapted | SprintWeave agents | `<weeks>` | RHOSO CPAT |
| NCS | 25.7 | CIQ + Playbooks (built manually as NDAT) | Manual | `<weeks>` | Previous NCS release |
| CBIS | 25 | CIQ + Playbooks + AAP (built manually as CDAT) | Manual | `<weeks>` | Previous CBIS release |

> **Note:** NCS/CBIS rows are legacy reference points. SprintWeave agents only apply to RHOSO and NRHO CPAT.

### Cross-Project Reusability

| Blueprint | Built By | Originally For | Reused Across | Clusters |
|-----------|----------|---------------|--------------|----------|
| NCS CIQ + NDAT | Manual | T-Mobile USD | AT&T, Bytel, TMO Mobility, Signaling, NPC | 228+ |
| CBIS CIQ + CDAT/AAP | Manual | T-Mobile SDL | OneWeb, SFR France, Bouygues Telecom | 37+ |
| RHOSO CPAT | SprintWeave | Initial dev | Future RHOSO customers | `<placeholder>` |
| NRHO (adapted) | SprintWeave | NAM customer | `<future>` | `<count>` |

### CPAT Reusability Breakdown

> Use an **Expand macro** titled "CPAT Reusability — How much can be reused across customers and products?"

**Same Product, New Customer (~85-95% reuse → 1-2 weeks delivery):**

> When delivering CPAT to another customer on the same product (RHOSO), most of the tool is reused. The CIQ workbook values change, and some customers may need configuration variants not yet covered by existing templates.

| Component | Reuse % | What Changes |
|-----------|---------|--------------|
| Flask Backend API (18 routes) | 100% | Nothing — product-agnostic |
| React Frontend UI (11 components) | 100% | Nothing — product-agnostic |
| Container Packaging | 100% | Nothing — product-agnostic |
| CIQ Parser & Workbook Generator | 100% | Nothing — schema-driven |
| CIQ Schema & Validation | 95% | May need new parameters if customer has unsupported config (e.g., new storage driver, custom network plugin) |
| Ansible Playbooks (18 tasks) | 90% | Core tasks reused; may need new conditional blocks for customer-specific deployment paths |
| Jinja2 Templates (15) | 85% | Existing templates cover connected, disconnected, CPU pinning, BMH modes; may need new templates for edge cases (e.g., custom Cinder driver, non-standard network topology) |
| Defaults (~100) | 90% | Base defaults shared; new defaults if schema extends |
| Blueprinting Engine | 90% | Gap analysis framework reused; new knowledge if customer has unique architecture |
| **Overall** | **~85-95%** | **CIQ values always change; templates/playbooks may need minor extensions for deployment variants** |

**What's already parameterized in CPAT (no new code needed):**

| Customer Variation | Handled By | New Code? |
|---|---|---|
| Connected vs Disconnected | `rhoso_is_disconnected` CIQ flag → conditional templates (IDMS, ITMS, CatalogSource) | No |
| Storage backend (LVM, NFS, Ceph) | CIQ RHOSO Storage + Cinder Backend tables → template parameters | No |
| CPU pinning | `rhoso_cpu_dedicated_set` CIQ flag → Nova ConfigMap template | No |
| Pre-provisioned vs Unprovisioned (BMC) | CIQ deployment mode → BMH + NMState templates | No |
| Service selection (Horizon, Barbican) | CIQ RHOSO Services table → enable flags | No |
| Network topology (bonded, single, DPDK) | CIQ EDPM Network Config table → EDPM template | No |
| Compute scale (3 compact vs 10+ dedicated) | CIQ Data Plane Nodes table → NodeSet template | No |

**What might need new work (~5-15%):**

| Customer Variation | Why New Work | Effort |
|---|---|---|
| Unsupported storage driver (e.g., Pure Storage) | New Cinder backend template + CIQ parameters | ~1-2 days |
| Custom network plugin (non-OVN) | New network templates + playbook conditionals | ~2-3 days |
| Non-standard OS (custom RHEL image) | New EDPM config + validation rules | ~1 day |
| Multi-site / edge deployment | New topology templates + orchestration | ~3-5 days |
| Customer-specific compliance/hardening | New security tasks + validation | ~2-3 days |

**New Product (~60% reuse → ~2 weeks delivery):**

> When adapting CPAT to a new product (e.g., RHOSO → OCP or AAP), the platform layer is reusable but product-specific components need new work.

| Component | Reuse % | Reusable Part | New Work Needed |
|-----------|---------|--------------|-----------------|
| Flask Backend API | 90% | Routes, streaming, auth | Product-specific endpoints |
| React Frontend UI | 85% | Dashboard, cluster mgmt, logs | Product-specific forms |
| Container Packaging | 95% | Dockerfile, entrypoint, Nginx | Minor config |
| CIQ Parser Framework | 80% | Parsing engine, validation framework | New schema mapping |
| CIQ Workbook Generator | 70% | Excel generation engine | New sheets/columns |
| Blueprinting Engine | 70% | Gap analysis framework | New product knowledge |
| Ansible Playbooks | 30% | Common patterns (prereqs, validation) | New deployment tasks |
| CIQ Schema | 20% | Schema type framework | New product parameters |
| Defaults | 15% | Default structure | New product defaults |
| Jinja2 Templates | 10% | Template patterns | New CRs/manifests |
| **Overall** | **~60%** | | |

**Reuse by target product:**

| Adaptation | Reuse % | Reason |
|-----------|---------|--------|
| RHOSO → NRHO | ~75% | Similar OpenStack base, same CR types |
| RHOSO → OCP | ~55% | Different deployment model, new operators |
| RHOSO → AAP | ~50% | Entirely different platform, new automation patterns |

**Architecture enabling reuse:**

```
+---------------------------------------------------+
|  PLATFORM LAYER (~90% reusable across products)   |
|  Flask API | React UI | Container | CIQ Parser    |
+---------------------------------------------------+
|  PRODUCT LAYER (~20% reusable across products)    |
|  CIQ Schema | Playbooks | Templates | Defaults    |
+---------------------------------------------------+
|  CUSTOMER LAYER (0% reuse — unique per customer)  |
|  CIQ Workbook values: IPs, VLANs, hostnames       |
+---------------------------------------------------+
```

### Reusability KPIs

> Use a **Panel macro** (Purple):

```
Blueprints in library: <count>
Products: NCS, CBIS, NRHO, RHOSO
Customers served: <count>
Clusters automated: 265+
Markets: NAM, EUR
Same-product reuse: ~85-95%
Cross-product reuse: ~60%
```

### Legacy Projects (Delivered)

> Use an **Expand macro** titled "Legacy Projects — NDAT, CDAT, NCS Audit Tool".
>
> Inside the expand, use a **3-column layout** with **Panel macros**.

**Column 1 — NDAT** (Green panel)

Panel title: **NDAT — NCS Deployment Automation Tool**

|              |                                |
| ------------ | ------------------------------ |
| **Platform** | Nokia Container Services (NCS) |
| **Status**   | Delivered                      |

**Customers & Clusters:**

| Customer | Clusters | Activity |
| --- | --- | --- |
| T-Mobile USD | 30 | NCS 25.7 Upgrade |
| T-Mobile Mobility | 145 | NCS 26.7 Deployment |
| T-Mobile Signaling | 12 | NCS 25.7 Upgrade |
| T-Mobile NPC | 30 | NCS 25.7 Upgrade |
| Bouygues Telecom | 5 | NCS 25.7 Upgrade |
| AT&T | 6 | NCS 22.12 MP3 Upgrade |
| **Total** | **228 clusters** | **6 customers** |

**Capabilities:** Prechecks, Deployment & Upgrade, Post-deployment/upgrade (Day 0 / Day 1)

**Impact Metrics:**

| Metric | Value |
| --- | --- |
| Manual effort reduction | **60–70%** |
| Upgrade cycle speedup | **40–50% faster** |
| Human error reduction | **~80%** |
| Operational efficiency | **2x improvement** |
| Total time saved | **80.3 hours** (3.5 days) |
| Average speedup | **19% faster** across all active PODs |

**Column 2 — CDAT** (Blue panel)

Panel title: **CDAT — CBIS Deployment Automation Tool + Red Hat AAP**

|                |                                                  |
| -------------- | ------------------------------------------------ |
| **Platform**   | Cloud Band Infrastructure Software (CBIS)        |
| **Automation** | CDAT + Red Hat Ansible Automation Platform (AAP) |
| **Status**     | Delivered                                        |

**Customers & Clusters:**

| Customer | Clusters | Activity |
| --- | --- | --- |
| T-Mobile SDL | 25 | CBIS 25 Upgrade |
| OneWeb | 3 | CBIS 24 Deployment |
| SFR France | 3 | CBIS 24 Deployment |
| Bouygues Telecom | 6 | CBIS 24 Deployment |
| **Total** | **37 clusters** | **4 customers** |

**Capabilities:** Prechecks, Deployment & Upgrade, Post-deployment/upgrade (Day 0 / Day 1), Customer-specific configurations, Blueprint generation & validation

**Column 3 — NCS Audit Tool** (Yellow panel)

Panel title: **NCS Audit Tool**

|              |                                |
| ------------ | ------------------------------ |
| **Platform** | Nokia Container Services (NCS) |
| **Status**   | Delivered                      |

**Customers:** T-Mobile USD — Production cluster audits

**Capabilities:** Deployment configuration audit, Kubernetes audit, Hardware audit, Software packages/versions audit. Audits against blueprinting inputs. Full audit in **less than 20 minutes** for **120 nodes**.

### Embedded Excel Workbook

> Use an **Expand macro** titled "SprintWeave RHOSO Agent Epics Workbook".

1. Attach `SprintWeave RHOSO Agent Epics.xlsx` to this page (three-dot menu → Attachments → drag and drop)
2. In the editor, type `/office` → select **Office Excel** macro
3. Select the attached file → renders inline with all sheets viewable
4. Width: 100%, Height: 600px

---

# GOOGLE SHEETS IFRAMES — Data Sources & Charts

> **One Google Sheet powers Sections 3, 4, and 5.** The Excel file `SprintWeave RHOSO Agent Epics.xlsx` is uploaded to Google Sheets. Charts are created inside Google Sheets and embedded into Confluence as iframes. Cell ranges are also embedded as iframes for live data tables. **Single source of truth — edit in Google Sheets, Confluence updates automatically.**

### How Google Sheets iframe Embedding Works

**For Charts:**
1. Create the chart in Google Sheets (Insert → Chart → configure)
2. Click the chart → three-dot menu → **"Publish chart"** → select **"Interactive"** or **"Image"** → Copy the embed URL
3. In Confluence editor, type `/iframe` → paste the chart publish URL
4. Set width: 100%, height: 400px (adjust as needed)

**For Data Tables (cell ranges):**
1. In Google Sheets, go to **File → Share → Publish to web**
2. Select the specific **sheet** or **cell range** (e.g., `Statistical Data!A1:G12`)
3. Choose **"Web page"** format → Copy the publish URL
4. In Confluence editor, type `/iframe` → paste the URL
5. Set width: 100%, height: 300px (adjust as needed)

**For inline editing view:**
1. Use the direct Google Sheets URL with `/edit` or `/gviz` for embedded cell inputs
2. In Confluence, type `/iframe` → paste the Google Sheets edit URL
3. Authorized users can edit values directly from Confluence

> **Tip:** Published Google Sheets auto-refresh every 5 minutes. For instant updates, re-publish after editing.

---

## Table 1 — Project Delivery Savings

> **Powers:** Section 4 (per-cluster savings, charts) + Section 1 (executive deployment impact)
>
> **One row per project/customer** — tracks per-cluster effort savings from automation.
>
> **What this saving denotes:** *Per-cluster deployment effort reduced by 50% (10 MWD to 5 MWD) using CDAT/NDAT automation across 265+ NCS and CBIS clusters — this is the ongoing operational savings from existing automation tools.*
>
> **Savings Highlight:** *Automation saved 1,325 MWD (265 MWW) across 265 clusters for 10 customer projects.*

### Table 1 Data

> Source: Google Sheets → Statistical Data sheet → "Project Delivery Savings" section. Embedded via `/iframe`.

| Project | Customer | Product | Release | Clusters | WITHOUT (MWD) | WITH (MWD) | Savings (MWD) | Savings % | Total Savings (MWW) |
|---------|----------|---------|---------|----------|---------------|------------|--------------|-----------|-------------------|
| USD | T-Mobile | NCS | 25.7 | 30 | 10 | 5 | 5 | 50% | 30 |
| Mobility | T-Mobile | NCS | 26.7 | 145 | 10 | 5 | 5 | 50% | 145 |
| Signaling | T-Mobile | NCS | 25.7 | 12 | 10 | 5 | 5 | 50% | 12 |
| NPC | T-Mobile | NCS | 25.7 | 30 | 10 | 5 | 5 | 50% | 30 |
| — | Bouygues Telecom | NCS | 25.7 | 5 | 10 | 5 | 5 | 50% | 5 |
| — | AT&T | NCS | 22.12 MP3 | 6 | 10 | 5 | 5 | 50% | 6 |
| SDL | T-Mobile | CBIS | 25 | 25 | 10 | 5 | 5 | 50% | 25 |
| — | OneWeb | CBIS | 24 | 3 | 10 | 5 | 5 | 50% | 3 |
| — | SFR France | CBIS | 24 | 3 | 10 | 5 | 5 | 50% | 3 |
| — | Bouygues Telecom | CBIS | 24 | 6 | 10 | 5 | 5 | 50% | 6 |

### Table 1 Charts (2 Google Sheets charts)

Create these charts in Google Sheets from the "Statistical Data" sheet → "Project Delivery Savings" section:

| Chart | Type | Config | Used In |
|-------|------|--------|---------|
| Savings by Project | Bar | X: Project, Y: Total Savings (MWW) | Section 4 (left) |
| Savings by Product | Pie | Category: Product, Value: Total Savings (MWW) | Section 4 (right) |

**How to create & embed:**
1. In Google Sheets → select Table 1 data range → **Insert → Chart** → Bar → X: Project, Y: Total Project Savings (MWD)
2. Create a second chart → Pie → Category: Product, Value: Total Project Savings (MWD)
3. Publish each chart: chart three-dot menu → **"Publish chart"** → copy embed URL
4. In Confluence → `/iframe` → paste each chart URL (one per column in a 2-column layout)

**Table 1 data iframe:**
1. In Google Sheets → **File → Share → Publish to web** → select "Statistical Data" sheet, range covering Project Delivery Savings rows
2. In Confluence → `/iframe` → paste the published URL → wrap in **Expand macro** titled "Detailed Project Data"

---

## Table 2 — CPAT Development Effort — Manual vs SprintWeave

> **Powers:** Section 3 (dev effort comparison chart + detail table) + Section 1 (executive dev savings)
>
> **Baseline:** Manually developing CPAT | **Comparison:** SprintWeave-generated CPAT
>
> **What this saving denotes:** *Engineering effort to build the 10 CPAT components (CIQ, playbooks, templates, API, UI, container) — comparing manual hand-coding vs SprintWeave agent-generated code.*
>
> **Savings Highlight:** *SprintWeave agents reduced CPAT development effort from 25 MWD (5 weeks) to 9 MWD, saving 64% of engineering effort across 10 components.*

### Table 2 Data

> Source: Google Sheets → Statistical Data sheet → "CPAT Development Efforts" section. Embedded via `/iframe`.

| CPAT Component | Agent | Manual (MWD) | SprintWeave (MWD) | Effort Saved (MWD) | Effort Saved % | What SprintWeave Does |
|----------------|-------|-------------|-------------------|--------------------|----------------|----------------------|
| CIQ Schema | RDA Agent | 4 | 1.5 | 2.5 | 63% | Auto-generates 152+ params, 40+ types, regex patterns from RHOSO docs |
| CIQ Workbook | RDA Agent | 2 | 1 | 1 | 50% | Generates Excel workbooks from schema with validation |
| CIQ Parser | RDA Agent | 2 | 1 | 1 | 50% | Generates parser with header mapping and normalization |
| Blueprinting | RDA Agent | 3 | 1 | 2 | 67% | Builds gap analysis, project-specific CIQ generation |
| Playbooks | RDE Agent | 4 | 1 | 3 | 75% | Generates 18 task files from CIQ schema |
| Templates | RDE Agent | 2 | 0.5 | 1.5 | 75% | Generates 15 templates for all deployment phases |
| Defaults | RDE Agent | 2 | 0.5 | 1.5 | 75% | Generates ~100 defaults from CIQ parameter types |
| Flask API | RDE Agent | 3 | 1 | 2 | 67% | Generates 18 routes with streaming, deployment mgmt |
| React UI | RDE Agent | 2 | 1 | 1 | 50% | Generates 11 components with Vite build |
| Container | RDE Agent | 1 | 0.5 | 0.5 | 50% | Generates Dockerfile, entrypoint, bringup script |
| **Total** | | **25 (5 wks)** | **9 (1.8 wks)** | **16 (3.2 wks)** | **64%** | |

### Table 2 Chart (1 Google Sheets chart)

| Chart | Type | Config | Used In |
|-------|------|--------|---------|
| Dev Effort Comparison | Bar (grouped) | X: CPAT Component, Data series: Manual (MWD) + SprintWeave (MWD) | Section 3 |

**How to create & embed:**
1. In Google Sheets → select CPAT Development Efforts data range → **Insert → Chart** → Bar (grouped)
2. Configure: X-axis = CPAT Component, Data series = Manual (MWD) and SprintWeave (MWD) → grouped bars (Manual = red, SprintWeave = green)
3. Publish chart: three-dot menu → **"Publish chart"** → copy embed URL
4. In Confluence → `/iframe` → paste the chart URL

**Table 2 data iframe:**
1. Publish the CPAT Development Efforts cell range from Google Sheets
2. In Confluence → `/iframe` → paste the published URL → visible in Section 3 as the Component Effort Table

---

## Table 3 — Customer Delivery Lead Time — Manual vs SprintWeave

> **Powers:** Section 5 (delivery readiness chart + detail table) + Section 1 (executive delivery speed)
>
> **Key question:** How fast can we deliver CPAT from requirement to customer?
>
> **What this saving denotes:** *End-to-end calendar time from receiving a customer requirement to delivering a ready CPAT package — comparing manual build-and-deliver vs SprintWeave-accelerated delivery.*
>
> **Savings Highlight:** *SprintWeave-powered CPAT delivers customer packages in 1 week vs 4 weeks manually, saving 3 weeks per customer delivery.*

### Table 3 Data

> Source: Google Sheets → Statistical Data sheet → "Customer Readiness" section. Embedded via `/iframe`.

| Customer / Project | Product | Release | Lead Time (Wks) | Manual Estimate (Wks) | Lead Time Saved (Wks) |
|--------------------|---------|---------|-----------------|----------------------|-----------------------|
| RHOSO — Initial CPAT | RHOSO | 18.0 | 1 | 4 | 3 |
| NRHO — NAM Customer | NRHO | — | `<fill>` | `<fill>` | `<fill>` |
| `<Future RHOSO Customer>` | RHOSO | | | | |
| `<Future OCP Customer>` | OCP | | | | |
| `<Future AAP Customer>` | AAP | | | | |

### Table 3 Chart (1 Google Sheets chart)

| Chart | Type | Config | Used In |
|-------|------|--------|---------|
| Lead Time Comparison | Bar (grouped) | X: Customer/Project, Data series: Manual Estimate (Wks) + Lead Time (Wks) | Section 5 |

**How to create & embed:**
1. In Google Sheets → select Customer Readiness data range → **Insert → Chart** → Bar (grouped)
2. Configure: X-axis = Customer/Project, Data series = Manual Estimate (Wks) and Lead Time (Wks) → grouped bars
3. Publish chart: three-dot menu → **"Publish chart"** → copy embed URL
4. In Confluence → `/iframe` → paste the chart URL

**Table 3 data iframe:**
1. Publish the Customer Readiness cell range from Google Sheets
2. In Confluence → `/iframe` → paste the published URL → visible in Section 5 as the Customer Delivery Table

---

# HOW TO BUILD THIS DASHBOARD

## Step-by-Step Construction Order

### Step 1: Prepare the Data (Google Sheets)

**File:** `SprintWeave RHOSO Agent Epics.xlsx` → upload to **Google Sheets**

**Google Sheets has the formulas AND the charts.** The workflow is:

```
Excel (local master)  →  Upload to Google Sheets  →  Create charts in Google Sheets
                                                      └── Publish charts & cell ranges
                                                      └── Embed as /iframe in Confluence
```

| Sheet | What It Contains | Embeds |
|-------|-----------------|--------|
| `Statistical Data` — Project Delivery Savings | 10 project rows with savings formulas | Section 4: data iframe + 2 chart iframes |
| `Statistical Data` — CPAT Development Efforts | 10 components with effort formulas | Section 3: data iframe + 1 chart iframe |
| `Statistical Data` — Customer Readiness | Customer delivery rows with lead time | Section 5: data iframe + 1 chart iframe |

**Action:** Upload Excel to Google Sheets. Create charts (4 total). Publish charts and cell ranges. Embed in Confluence via `/iframe`.

### Step 2: Create Charts in Google Sheets & Publish

| Order | Chart | Source Range | Type | Publish |
|-------|-------|-------------|------|---------|
| 2a | Savings by Project | Project Delivery Savings | Bar | Publish → copy embed URL |
| 2b | Savings by Product | Project Delivery Savings | Pie | Publish → copy embed URL |
| 2c | Dev Effort Comparison | CPAT Development Efforts | Bar (grouped) | Publish → copy embed URL |
| 2d | Lead Time Comparison | Customer Readiness | Bar (grouped) | Publish → copy embed URL |

> Also publish cell ranges for each data section: **File → Share → Publish to web** → select range → "Web page" → copy URL.

### Step 3: Build the Dashboard Page

Create a single page titled **"GTS Innovation & Automation Dashboard"** and build Sections 0–6 in order:

| Section | What to Build | Data Source |
|---------|--------------|-------------|
| 0 — Welcome & Baseline | Static text + `/info` macro + image | None |
| 1 — Executive Summary | 4-column `/panel` layout + product table | JIRA macros + Google Sheets totals |
| 2 — Development Progress | 3-column panels + JIRA charts + Expand macros | JIRA macros only |
| 3 — CPAT Dev Savings | 3-column KPI panels + `/iframe` chart + `/iframe` data table + static table | Google Sheets iframes |
| 4 — Deployment Savings | 3-column KPI panels + `/iframe` bar & pie charts + `/iframe` data table (in Expand) | Google Sheets iframes |
| 5 — Delivery Readiness | 2-column KPI panels + `/iframe` chart + `/iframe` data table | Google Sheets iframes |
| 6 — Blueprint Reuse & Legacy | Static tables + Expand legacy panels + Expand Excel | Static + attachment |

### Step 4: Embed iframes in Confluence

For each section that needs charts or data tables:

1. In Confluence editor → type `/iframe`
2. Paste the published Google Sheets URL (chart or cell range)
3. Set width: `100%`, height: `400px` (charts) or `300px` (tables)
4. Arrange in column layouts as described in each section

### Step 5: Create CPAT Child Page (Optional)

Create a **child page** titled "CPAT — Cloud Platform Automation Tool" with the detailed CPAT content (architecture, components, deployment tasks, CIQ tables). See the **CPAT Detailed Reference** section below.

## Data Flow

```
SprintWeave RHOSO Agent Epics.xlsx  (LOCAL MASTER)
  │
  └──[upload]──→ Google Sheets  (CALCULATION + CHART LAYER)
                  │
                  ├── Statistical Data: Project Delivery Savings
                  │     ├──[publish chart]──→ /iframe in Confluence Section 4: Bar chart
                  │     ├──[publish chart]──→ /iframe in Confluence Section 4: Pie chart
                  │     ├──[publish range]──→ /iframe in Confluence Section 4: detail table
                  │     └── Section 1: executive deployment impact (read totals)
                  │
                  ├── Statistical Data: CPAT Development Efforts
                  │     ├──[publish chart]──→ /iframe in Confluence Section 3: Grouped bar chart
                  │     ├──[publish range]──→ /iframe in Confluence Section 3: detail table
                  │     └── Section 1: executive dev savings (read totals)
                  │
                  └── Statistical Data: Customer Readiness
                        ├──[publish chart]──→ /iframe in Confluence Section 5: Grouped bar chart
                        ├──[publish range]──→ /iframe in Confluence Section 5: detail table
                        └── Section 1: executive delivery speed (read totals)

JIRA (TMERAWORK1, 200 tickets, 10 labels)
  └── Section 1: initiative status (count macros)
  └── Section 2: charts, panels, issue tables (JIRA macros)
```

## Where the Baseline Shows Up

| Dashboard Location | What's Compared | Baseline (WITHOUT) | Comparison (WITH) |
|-------------------|----------------|--------------------|--------------------|
| Section 1 — Col 2 | Dev savings summary | Manual total MWD | SprintWeave total MWD |
| Section 1 — Col 4 | Delivery speed | Manual lead time | SprintWeave lead time |
| Section 3 — KPI panels | Dev effort totals | Manual MWD | SprintWeave MWD |
| Section 3 — Bar chart | Per-component effort | Manual bars | SprintWeave bars |
| Section 3 — Static table | All dimensions | Manual column | SprintWeave column |
| Section 5 — KPI panels | Lead time | Manual estimate (weeks) | Actual delivery (weeks) |
| Section 5 — Bar chart | Per-customer lead time | Manual bars | SprintWeave bars |

> **DB1 (Section 4)** does NOT use the SprintWeave baseline. It compares `WITHOUT Automation` vs `WITH Automation` at the cluster deployment level.

---

# JIRA LABELS REFERENCE

All 200 JIRA tickets use **10 unique labels**:

**SprintWeave Labels (4):**

| Label | Tickets | Scope |
| --- | --- | --- |
| `sprintweave-core` | 19 | Core architecture, agent definition framework |
| `sprintweave-domain` | 24 | Domain agent rules, templates, knowledge enhancement |
| `sprintweave-engine` | 19 | Pipeline engine, quality gates, artifact export |
| `sprintweave-tools` | 15 | Canvas dashboard, context management, custom skills |

**RHOSO / CPAT Labels (6):**

| Label | Tickets | Scope |
| --- | --- | --- |
| `rhoso-cpat` | 123 | Cross-cutting grouper — all RHOSO tickets |
| `rhoso-manifests` | 41 | RDE Agent — manifest generation |
| `rhoso-app` | 28 | RDE Agent — Flask backend, React frontend, container |
| `rhoso-ansible` | 24 | RDE Agent — Ansible automation, workflows, defaults |
| `rhoso-schema` | 19 | RDA Agent — CIQ schema, validation, parser |
| `rhoso-ciq` | 11 | RDA Agent — CIQ workbooks, project-specific generation |

**Groupings for JQL:**

| Group | Labels | Use for |
| --- | --- | --- |
| All 200 tickets | `NF_GTS, NF_Library` | Overall charts (shared — all viewers see same data) |
| SprintWeave (77) | `sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain` | SprintWeave panel |
| RDA Agent (30) | `rhoso-schema, rhoso-ciq` | RDA panel |
| RDE Agent (93) | `rhoso-ansible, rhoso-manifests, rhoso-app` | RDE panel |
| CPAT (123) | `rhoso-cpat` | CPAT-specific |

---

# IN-JIRA DASHBOARDS (Optional)

> These are dashboards created **inside JIRA** (not Confluence). Optional — create them if your team prefers JIRA's native dashboard view.

### JIRA Dashboard 1 — SprintWeave Framework

**Name:** `SprintWeave Framework Dashboard`

| Gadget | Type | JQL / Config |
| --- | --- | --- |
| Filter Results | Issue Table | `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain) ORDER BY status ASC, key ASC` |
| Pie Chart — Status | Pie Chart | Statistic: Statuses |
| Pie Chart — Labels | Pie Chart | Statistic: Labels |
| Issue Count — Total | Issue Count | `project = TMERAWORK1 AND labels in (sprintweave-core, sprintweave-engine, sprintweave-tools, sprintweave-domain)` |
| Issue Count — Done | Issue Count | Same + `AND statusCategory = Done` |

### JIRA Dashboard 2 — RDA Agent

**Name:** `RDA Agent — Blueprinting Engine Dashboard`

| Gadget | Type | JQL / Config |
| --- | --- | --- |
| Filter Results | Issue Table | `project = TMERAWORK1 AND labels in (rhoso-schema, rhoso-ciq) ORDER BY status ASC, key ASC` |
| Pie Chart — Status | Pie Chart | Statistic: Statuses |
| Pie Chart — Priority | Pie Chart | Statistic: Priorities |
| Created vs Resolved | Two Dimensional | Period: Weekly, Days: 56 |

### JIRA Dashboard 3 — RDE Agent

**Name:** `RDE Agent — Deployment Automation Dashboard`

| Gadget | Type | JQL / Config |
| --- | --- | --- |
| Filter Results | Issue Table | `project = TMERAWORK1 AND labels in (rhoso-ansible, rhoso-manifests, rhoso-app) ORDER BY status ASC, key ASC` |
| Pie Chart — Status | Pie Chart | Statistic: Statuses |
| Pie Chart — Priority | Pie Chart | Statistic: Priorities |
| Pie Chart — Assignee | Pie Chart | `statusCategory != Done` / Statistic: Assignees |
| Created vs Resolved | Two Dimensional | Period: Weekly, Days: 56 |

**How to create:** JIRA → Dashboards → Create dashboard → Add gadgets → Share with team.

---

# CPAT DETAILED REFERENCE (Child Page)

> Create as a **child page** titled "CPAT — Cloud Platform Automation Tool".

### What is CPAT?

CPAT (Cloud Platform Automation Tool) is an end-to-end web-based automation framework for deploying **Red Hat OpenStack Services on OpenShift (RHOSO)** on an existing RHOCP cluster. It is the combined output of two SprintWeave AI agents — the **RDA Agent** (Blueprinting) and the **RDE Agent** (Deployment Automation).

**Platform:** RHOSO (current) | **Future:** NRHO, OCP, AAP (planning phase)

### Architecture

```
+-------------------------------------------------------------------+
|  Bastion / Jump Host                                              |
|  +-------------------------------------------------------------+ |
|  |  CPAT Container (Podman / Docker)                            | |
|  |  +----------------+  +----------------+  +----------------+  | |
|  |  |  React UI      |  |  Flask API     |  |  Ansible       |  | |
|  |  |  (Nginx :80)   |->|  (Gunicorn     |->|  Playbooks     |  | |
|  |  |  11 components |  |   :5000)       |  |  18 tasks      |  | |
|  |  |                |  |  18 routes     |  |  15 templates   |  | |
|  |  +----------------+  +----------------+  +-------+--------+  | |
|  +--------------------------------------------------|----------+  |
+-----------------------------------------------------|-------------+
                                                      |
                +---------------------------+---------+---------+
                v                           v                   v
       +--------+--------+       +----------+------+   +--------+--------+
       |  OCP API        |       |  OCP Workers    |   |  EDPM Compute   |
       |  (oc commands)  |       |  (3 compact     |   |  (RHEL 9.x)    |
       |  Namespaces,    |       |   nodes)        |   |  SSH access,   |
       |  Operators, CRs |       |  NNCP, MetalLB  |   |  Nova compute  |
       +-----------------+       +-----------------+   +-----------------+
```

### Components

| Component | What It Does | Agent |
| --- | --- | --- |
| **CIQ Schema & Validation** | 13 input tables, 152+ parameters, 40+ type definitions with regex validation | RDA |
| **CIQ Workbook Generator** | Excel-based CIQ workbooks with pre-filled templates | RDA |
| **CIQ Parser** | Parses CIQ workbooks, normalizes headers, validates against schema | RDA |
| **Blueprinting Engine** | Customer requirements → validated, deployment-ready configurations | RDA |
| **Ansible Automation** | 18 task files, 15 Jinja2 templates, ~100 defaults for RHOSO manifests | RDE |
| **Flask Backend API** | 18 routes — CIQ upload, manifest generation, Ansible execution with NDJSON streaming | RDE |
| **React Frontend UI** | 11 components (Vite) — CIQ upload, parameter editing, manifest preview, deployment | RDE |
| **Container Packaging** | Multi-stage Docker build (Node 20 + Python 3.12 + Nginx) with Podman support | RDE |

### Deployment Tasks (12)

| # | Task | What It Does |
| --- | --- | --- |
| 1 | Pre-requisites | Validates CIQ, kubeconfig, pull secret, cluster-admin, StorageClass |
| 2 | Prerequisite Operator Installation | NMState, MetalLB, Cert-Manager via OLM |
| 3 | Disconnected Environment Preparation | CatalogSource, IDMS/ITMS, OperatorHub patch |
| 4 | Persistent Storage Configuration | StorageClass for Galera, OVN, Telemetry |
| 5 | OpenStack Operator Installation | Subscription, InstallPlan, OpenStack init CR |
| 6 | RHOCP Preparation for RHOSO | Namespace, privileged labels, osp-secret |
| 7 | Network Preparation | NNCP, NAD, MetalLB IPAddressPool, NetConfig |
| 8 | Control Plane Deployment | OpenStackControlPlane CR |
| 9 | Control Plane Customization | Horizon, Barbican, additional services |
| 10 | Data Plane Deployment | NodeSet + Deployment CRs, EDPM nodes |
| 11 | Post-Deployment Validation | Services, endpoints, compute availability |
| 12 | Generate Manifests for Review | YAML from CIQ (no oc apply) |

### Manifest Templates (15)

| # | Template | CR Kind | When Generated |
| --- | --- | --- | --- |
| 1 | openstack_nncp | NodeNetworkConfigurationPolicy | Always |
| 2 | openstack_nad | NetworkAttachmentDefinition | Always |
| 3 | openstack_metallb | IPAddressPool + L2Advertisement | Always |
| 4 | openstack_netconfig | NetConfig | Always |
| 5 | openstack_control_plane | OpenStackControlPlane | Always |
| 6 | edpm_network_config_template | EDPM NIC config | Always |
| 7 | openstack_dataplane_nodeset | OpenStackDataPlaneNodeSet | Always |
| 8 | openstack_dataplane_deployment | OpenStackDataPlaneDeployment | Always |
| 9 | openstack_baremetalhosts | BareMetalHost + BMC Secrets | Unprovisioned mode |
| 10 | openstack_nmstate_secrets | NMState provisioning Secrets | Unprovisioned mode |
| 11 | openstack_nova_cpu_pinning_cm | Nova CPU pinning ConfigMap | CPU Dedicated Set |
| 12 | catalog_source | CatalogSource | Disconnected mode |
| 13 | image_digest_mirror_set | ImageDigestMirrorSet | Disconnected mode |
| 14 | image_tag_mirror_set | ImageTagMirrorSet | Disconnected mode |
| 15 | operatorhub_disable_defaults | OperatorHub patch | Disconnected mode |

### CIQ Input Summary (13 tables, 152+ parameters)

| Table | Parameters | Covers |
| --- | --- | --- |
| RHOSO Details | 10 | Cluster name, type, environment, versions, deployment mode, namespaces |
| RHOSO Access | 3 | Kubeconfig path, OCP API URL, pull secret path |
| RHOSO Disconnected | 16 | Mirror registry, CatalogSource, IDMS/ITMS |
| RHOSO Storage | 2 | StorageClass, storage backend |
| RHOSO Control Plane | 27 | CR name, FQDN, VIPs, NICs, OVN, TLS, operator config |
| RHOSO Services | 35 | Service enable flags, replica counts |
| RHOSO PV Sizing | 10 | PVC sizes for Galera, OVN, Telemetry, RabbitMQ |
| RHOSO Cinder Backend | 8 | Volume type, driver, NetApp config, secrets |
| RHOSO Neutron Config | 4 | Physnet MTU, API timeout, OVN fragmentation |
| RHOSO EDPM Network Config | 24 | Bridge, topology, bonding, DPDK, NTP, tuning |
| RHOSO Data Plane | 14 | NodeSet/Deployment names, SSH, secrets, subscription |
| RHOSO Networks | 16 cols/row | Per-network: CIDR, VLAN, gateway, MTU, IP ranges |
| RHOSO Data Plane Nodes | 16 cols/row | Per-node: hostname, IPs, role, BMC, boot mode, NICs |

### Prerequisites (Not Managed by CPAT)

| Prerequisite | Description |
| --- | --- |
| Running RHOCP cluster | OCP 4.14+ with cluster-admin access |
| Bastion with Podman | Linux host with network access to OCP API |
| Kubeconfig | cluster-admin kubeconfig file |
| Pull secret | Red Hat registry pull-secret.json |
| SSH key to compute nodes | Private key for Ansible SSH access |
| Network connectivity | Bastion must reach OCP API and EDPM node IPs |

### Running CPAT

```
./bringup.sh                # Build and start CPAT container
./bringup.sh --build        # Build image only
./bringup.sh --restart      # Stop, rebuild, and start
./bringup.sh --stop         # Stop and remove container
```

Access: [http://localhost](http://localhost)

---

# TIPS

1. **Macro refresh** — JIRA macros fetch live data on each page load; no manual refresh needed.
2. **Tune your statuses** — Check your actual project workflow statuses at JIRA → Project Settings → Board → Columns.
3. **Page load speed** — If the page feels slow, reduce Maximum issues per macro or collapse sections with Expand macros.
4. **Child pages** — Create child pages for detailed reports (e.g., "Q3 Innovation Report").
5. **Notifications** — Team members can Watch the page for email alerts.
6. **Updating data** — When project data changes: update Google Sheets directly (formulas auto-compute, charts auto-update). Published iframes in Confluence refresh automatically within 5 minutes. For instant refresh, re-publish the sheet.
7. **Single-ticket Smart Links** — Paste a JIRA URL (e.g., `https://issues.redhat.com/browse/TMERAWORK1-356`) and Confluence auto-converts it to an inline card with status.
8. **Google Sheets permissions** — Set the Google Sheet to "Anyone with the link can view" so Confluence iframes can render. For edit access, share with specific team members.
9. **iframe sizing** — Adjust iframe width (100%) and height (300–500px) per section for optimal display. Charts typically need 400px height, data tables need 250–350px.

---

# PAGE HIERARCHY

```
GTS Innovation Hub (main space)
+-- GTS Innovation & Automation Dashboard (THIS PAGE — single dashboard)
|   +-- Section 0: Welcome & Baseline
|   +-- Section 1: Executive Summary
|   +-- Section 2: Development Progress
|   +-- Section 3: CPAT Dev Savings
|   +-- Section 4: Deployment Savings
|   +-- Section 5: Delivery Readiness
|   +-- Section 6: Blueprint Reuse & Legacy
|
+-- CPAT — Cloud Platform Automation Tool (child page — detailed reference)
+-- Project Delivery Archives
    +-- <Project entries with artifacts>
```
