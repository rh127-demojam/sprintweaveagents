# SprintWeave — CPAT RHOSO Automation Framework

AI-driven framework that uses **SprintWeave** agents to design, generate,
and maintain the **CPAT** (Cloud Platform Automation Tool) for automated
RHOSO deployments.

For CPAT application usage, deployment workflow, and how to run the tool,
see **[output/cpat/README.md](output/cpat/README.md)**.

---

## About CPAT

**CPAT (Cloud Platform Automation Tool)** is an end-to-end automation framework for deploying Red Hat OpenStack Services on OpenShift (RHOSO) at scale across global telco environments. It is powered by two SprintWeave AI agents — the **RHOSO Design Architect (RDA) Agent** and the **RHOSO Deployment Engineer (RDE) Agent** — which together produce all CPAT components.

### Components

| Component | What It Does |
|-----------|-------------|
| **CIQ Schema & Validation** | Defines 13 input tables with 152+ deployment parameters and 40+ type definitions with regex validation. Validates customer inputs before any deployment begins. |
| **CIQ Workbook Generator** | Generates Excel-based Customer Input Questionnaire (CIQ) workbooks from the schema — pre-filled templates for customers to provide deployment parameters. |
| **CIQ Parser** | Parses completed CIQ workbooks back into structured data, normalizing headers and validating all inputs against the schema. |
| **Blueprinting Engine** | Captures customer requirements and transforms them into validated, deployment-ready configurations — covering schema validation, gap analysis, and project-specific CIQ generation from existing deployments. |
| **Ansible Automation** | 18 task files, 15 Jinja2 manifest templates, and ~100 default variables that generate RHOSO manifests (control plane, data plane, network infrastructure, disconnected environments) from CIQ inputs. |
| **Flask Backend API** | REST API with 18 routes providing CIQ upload/parsing, manifest generation, Ansible playbook execution with streaming NDJSON progress, and deployment management. |
| **React Frontend UI** | 11-component web interface built with Vite — provides CIQ upload, parameter editing, manifest preview, deployment execution, and real-time log streaming. |
| **Container Packaging** | Multi-stage Docker build (Node 20 + Python 3.12 + Nginx) with Podman-compatible `bringup.sh` script for single-command build and run. |

### Architecture

CPAT runs as a containerized web application on a bastion host with network
access to the OCP cluster API and SSH access to compute nodes.

```
+-------------------------------------------------------------------+
|  Bastion / Jump Host                                              |
|                                                                   |
|  +-------------------------------------------------------------+ |
|  |  CPAT Container (Podman / Docker)                            | |
|  |                                                              | |
|  |  +----------------+  +----------------+  +----------------+  | |
|  |  |  React UI      |  |  Flask API     |  |  Ansible       |  | |
|  |  |  (Nginx :80)   |->|  (Gunicorn     |->|  Playbooks     |  | |
|  |  |  11 components |  |   :5000)       |  |  18 tasks      |  | |
|  |  |                |  |  18 routes     |  |  15 templates   |  | |
|  |  +----------------+  +----------------+  +-------+--------+  | |
|  +--------------------------------------------------|----------+  |
|                                                     |             |
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

### Communication Flow

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| User browser | CPAT (Nginx :80) | HTTP | Web UI access |
| React UI | Flask API (:5000) | HTTP (proxied) | API calls, log streaming (NDJSON) |
| Flask API | Ansible | subprocess | Triggers playbook runs |
| Ansible | OCP API | HTTPS (oc CLI) | Creates namespaces, operators, CRs, secrets |
| Ansible | EDPM Compute | SSH | Data plane node configuration |

### Deployment Workflow

**Generate → Review → Deploy**

| Step | Action | Description |
|------|--------|-------------|
| 1 | **Upload CIQ** | Upload customer-filled CIQ Excel workbook via web UI |
| 2 | **Validate** | CIQ Parser validates all 152+ parameters against schema with regex patterns |
| 3 | **Generate Manifests** | Ansible renders 15 Jinja2 templates into deployment-ready YAML |
| 4 | **Review** | View or download individual manifests; Download All (ZIP) |
| 5 | **Deploy** | Select deployment tasks to execute; Ansible applies manifests to OCP cluster |
| 6 | **Monitor** | Real-time log streaming via NDJSON shows deployment progress |

### Deployment Tasks (12)

| # | Task | What It Does |
|---|------|--------------|
| 1 | Pre-requisites | Validates CIQ, kubeconfig, pull secret, cluster-admin access, StorageClass |
| 2 | Prerequisite Operator Installation | Installs NMState, MetalLB, Cert-Manager Operators via OLM |
| 3 | Disconnected Environment Preparation | CatalogSource, IDMS/ITMS, OperatorHub patch (disconnected only) |
| 4 | Persistent Storage Configuration | Configures StorageClass for Galera, OVN, Telemetry |
| 5 | OpenStack Operator Installation | Creates Subscription, approves InstallPlan, creates OpenStack init CR |
| 6 | RHOCP Preparation for RHOSO | Creates namespace, privileged labels, osp-secret |
| 7 | Network Preparation | Applies NNCP, NAD, MetalLB IPAddressPool, NetConfig |
| 8 | Control Plane Deployment | Applies OpenStackControlPlane CR, waits for ready |
| 9 | Control Plane Customization | Post-deploy tuning (Horizon, Barbican, additional services) |
| 10 | Data Plane Deployment | Applies NodeSet + Deployment CRs, waits for EDPM nodes ready |
| 11 | Post-Deployment Validation | Verifies all services, endpoints, compute availability |
| 12 | Generate Manifests for Review | Renders YAML from CIQ into artifacts (no oc apply) |

### Manifest Templates (15)

| # | Template | CR Kind | When Generated |
|---|----------|---------|----------------|
| 1 | openstack_nncp | NodeNetworkConfigurationPolicy | Always |
| 2 | openstack_nad | NetworkAttachmentDefinition | Always |
| 3 | openstack_metallb | IPAddressPool + L2Advertisement | Always |
| 4 | openstack_netconfig | NetConfig | Always |
| 5 | openstack_control_plane | OpenStackControlPlane | Always |
| 6 | edpm_network_config_template | EDPM NIC config (os-net-config) | Always |
| 7 | openstack_dataplane_nodeset | OpenStackDataPlaneNodeSet | Always |
| 8 | openstack_dataplane_deployment | OpenStackDataPlaneDeployment | Always |
| 9 | openstack_baremetalhosts | BareMetalHost + BMC Secrets | Unprovisioned mode |
| 10 | openstack_nmstate_secrets | NMState provisioning Secrets | Unprovisioned mode |
| 11 | openstack_nova_cpu_pinning_cm | Nova CPU pinning ConfigMap | When CPU Dedicated Set defined |
| 12 | catalog_source | CatalogSource | Disconnected mode |
| 13 | image_digest_mirror_set | ImageDigestMirrorSet | Disconnected mode |
| 14 | image_tag_mirror_set | ImageTagMirrorSet | Disconnected mode |
| 15 | operatorhub_disable_defaults | OperatorHub patch | Disconnected mode |

### CIQ Input Summary (13 tables, 152+ parameters)

| Table | Params | Covers |
|-------|--------|--------|
| RHOSO Details | 10 | Cluster name, type, environment, versions, deployment mode, namespaces |
| RHOSO Access | 3 | Kubeconfig path, OCP API URL, pull secret path |
| RHOSO Disconnected | 16 | Mirror registry, CatalogSource, IDMS/ITMS (disconnected only) |
| RHOSO Storage | 2 | StorageClass, storage backend |
| RHOSO Control Plane | 27 | CR name, FQDN, VIPs (9 services), NICs, OVN, TLS, operator config |
| RHOSO Services | 35 | 8 service enable flags, replica counts for all services |
| RHOSO PV Sizing | 10 | PVC sizes for Galera, OVN, Telemetry, RabbitMQ resources |
| RHOSO Cinder Backend | 8 | Volume type, driver, NetApp config, secrets |
| RHOSO Neutron Config | 4 | Physnet MTU, API timeout, OVN fragmentation |
| RHOSO EDPM Network Config | 24 | Bridge, topology, bonding, DPDK, NTP, tuning, kernel args |
| RHOSO Data Plane | 14 | NodeSet/Deployment names, SSH, secrets, subscription method |
| RHOSO Networks | 16 cols/row | Per-network: CIDR, VLAN, gateway, MTU, IP ranges, NAD config |
| RHOSO Data Plane Nodes | 16 cols/row | Per-node: hostname, IPs, role, BMC, boot mode, NICs |

### Prerequisites (Not Managed by CPAT)

| Prerequisite | Description |
|--------------|-------------|
| Running RHOCP cluster | OCP 4.14+ with cluster-admin access |
| Bastion with Podman | Linux host with network access to OCP API |
| Kubeconfig | cluster-admin kubeconfig file |
| Pull secret | Red Hat registry pull-secret.json |
| SSH key to compute nodes | Private key for Ansible SSH access |
| Network connectivity | Bastion must reach OCP API and EDPM node IPs |

### Powered By

| Agent | Produces |
|-------|----------|
| **RDA Agent** (Design Architect) | CIQ Schema, CIQ Workbooks, Blueprinting Engine, Gap Analysis |
| **RDE Agent** (Deployment Engineer) | Ansible Automation, Flask Backend, React Frontend, Container Packaging |

**Platform:** RHOSO (current) | **Future:** NRHO, OCP, AAP (planning phase)

---

## Directory Structure

```
cpat/
├── input/                              # Agent inputs (reference docs & project artifacts)
│   ├── rhoso/
│   │   ├── docs/                       # RHOSO PDF documentation
│   │   └── project-artifacts/          # Per-project deployment artifacts
│   │       ├── jio/                    #   JIO cluster manifests
│   │       └── core42/                 #   Core42 HLD documents
│   └── ocp/
│       ├── docs/                       # OCP installation guides (4.17–4.20)
│       └── project-artifacts/
│
├── output/                             # Agent outputs & CPAT application
│   ├── cpat/                           # CPAT application source code (see output/cpat/README.md)
│   │   ├── ansible/                    #   [RDE-1] Playbooks, roles, 15 Jinja templates, ~100 defaults
│   │   │   ├── playbooks/roles/rhoso/tasks/      # 18 task files
│   │   │   ├── playbooks/roles/rhoso/templates/   # 15 Jinja2 templates
│   │   │   ├── playbooks/roles/rhoso/defaults/    # ~100 default variables
│   │   │   ├── library/                           # parse_ciq.py, get_ciq_validation_schema.py
│   │   │   └── module_utils/                      # rhoso_ciq_schema.py, ocp_ciq_schema.py, ciq_parser.py (unified)
│   │   ├── backend/                    #   [RDE-2] Flask API (18 routes, streaming NDJSON)
│   │   ├── frontend/                   #   [RDE-3] React UI (11 components, Vite, Nginx)
│   │   ├── docker/                     #   [RDE-4] Container entrypoint
│   │   ├── Dockerfile                  #   [RDE-4] Multi-stage build
│   │   ├── bringup.sh                  #   [RDE-4] Podman build & run
│   │   └── README.md                   #   CPAT application documentation
│   ├── ciq-generators/                 #   [RDA] Python scripts: rhoso_ciq_schema.py, generators
│   ├── ciq-workbooks/                  #   [RDA] Generated CIQ Excel workbooks
│   │   ├── rhoso/                      #     sample-rhoso.ciq.xlsx, rhoso-ciq-template.xlsx
│   │   └── ocp/                        #     sample-ocp.ciq.xlsx, ocp-ciq-template.xlsx
│   ├── pipeline-reports/               #   Reference docs per stage
│   │   ├── rda/                        #     CIQ param reference, EDPM guide, gap matrix
│   │   └── rde/                        #     Workflow MoP, manifest catalog, blueprint
│   ├── lab-requirements/               #   Lab requirement workbooks
│   └── deployment-tasks/               #   Deployment task Excel briefs
│
├── project-management/                 # JIRA epics, CSV imports, tracking spreadsheets
│
├── agents/                             # Pipeline runners (outside Cursor IDE)
│   ├── rhoai/                          #   RHOAI runner (vLLM on OCP, enterprise)
│   │   ├── run-agents.ps1              #     PowerShell helper (auto-discovers endpoint)
│   │   ├── run-agents.sh               #     Bash helper
│   │   └── requirements.txt            #     openai, pyyaml
│   ├── ollama/                         #   Ollama runner (local GPU, no API key)
│   │   ├── run_pipeline.py             #     Shared pipeline runner (OpenAI-compatible)
│   │   ├── Dockerfile                  #     Self-contained container
│   │   ├── run-agents.ps1              #     PowerShell helper
│   │   ├── run-agents.sh               #     Bash helper
│   │   └── requirements.txt            #     openai, pyyaml
│   ├── cursor/                         #   Cursor SDK runner (cloud, requires API key)
│   │   ├── run_pipeline.py             #     Pipeline runner (cursor-sdk)
│   │   ├── Dockerfile                  #     Container image
│   │   ├── run-agents.ps1              #     PowerShell helper
│   │   ├── run-agents.sh               #     Bash helper
│   │   └── requirements.txt            #     cursor-sdk
│   └── README.md                       #   Runner comparison & quick start
│
├── .cursor/rules/                      # SprintWeave agent definitions
│   ├── agent-orchestrator.md           #   Pipeline coordinator
│   ├── agent-rhoso-da.md               #   RHOSO Design Architect
│   └── agent-rhoso-deployment-engineer.md  # RHOSO Deployment Engineer
│
├── context/                            # Runtime configuration
│   ├── pipelines.yaml                  #   Custom pipeline definitions
│   ├── team-config.yaml                #   Team, gates, quality settings
│   └── glossary-cloud.yaml             #   Domain terminology (100+ terms)
│
├── tools/                              # Built-in pipeline defaults & dashboard
│   ├── pipelines-default.yaml          #   Canonical pipeline definitions
│   └── cpat-dashboard.canvas.tsx       #   Interactive Cursor canvas dashboard
│
└── README.md                           # This file
```

---

## SprintWeave Agents

Three AI agents collaborate to design, generate, and deploy RHOSO automation
artifacts. Agent definitions live under `.cursor/rules/` and activate
automatically based on user prompts.

| Agent | Rule File | Role |
|-------|-----------|------|
| **Orchestrator** | `agent-orchestrator.md` | Pipeline coordinator — sequences agents, enforces gates, reports progress. Never generates artifacts directly. |
| **RHOSO DA** (Design Architect) | `agent-rhoso-da.md` | Analyzes RHOSO documentation and project artifacts to produce CIQ workbooks, schema code, lab requirements, EDPM topology guides, and PDF gap matrices. |
| **RHOSO Deployment Engineer** | `agent-rhoso-deployment-engineer.md` | Scaffolds or enhances CPAT source code (Ansible roles, Flask backend, React frontend, Docker), generates manifest catalogs, workflow MoPs, and deployment task briefs. |

### Agent Input / Output Summary

| Agent | Sub-stage | Reads From | Writes To |
|-------|-----------|------------|-----------|
| RHOSO DA | — | `input/rhoso/docs/`, `input/rhoso/project-artifacts/`, `input/ocp/docs/` | `output/ciq-generators/`, `output/ciq-workbooks/`, `output/lab-requirements/` |
| RHOSO DE | Ansible | CIQ schema from RDA output | `output/cpat/ansible/`, `output/cpat/ansible.cfg` |
| RHOSO DE | Backend | `output/cpat/ansible/module_utils/rhoso_ciq_schema.py` (from Ansible sub-stage) | `output/cpat/backend/` |
| RHOSO DE | Frontend | Backend API routes (from Backend sub-stage) | `output/cpat/frontend/` |
| RHOSO DE | Docker | All prior sub-stages (packages RDE-1+2+3) | `output/cpat/Dockerfile`, `docker/`, `bringup.sh` |
| Orchestrator | — | `context/pipelines.yaml`, `tools/pipelines-default.yaml`, `context/team-config.yaml` | Progress reports and gate checkpoints (no files) |

---

## Pipelines

Pipelines chain agents into ordered stages. Definitions are stored in two
files that the Orchestrator merges at runtime:

| File | Purpose |
|------|---------|
| `tools/pipelines-default.yaml` | Built-in pipeline definitions (canonical) |
| `context/pipelines.yaml` | Team customizations, promoted pipelines, deletions |

### Available Pipelines

| # | Pipeline | Stages | Command |
|---|----------|--------|---------|
| 1 | **RHOSO Delivery** | RDA + RDE-1 + RDE-2 + RDE-3 + RDE-4 (5 stages) | `Run RHOSO delivery pipeline on @cpat` |
| 2 | **RHOSO Design Architect** | RDA (1 stage) | `Run RHOSO DA pipeline on @cpat` |
| 3 | **RHOSO Deployment Engineer** | RDE-1 + RDE-2 + RDE-3 + RDE-4 (4 stages) | `Run RHOSO DE pipeline on @cpat` |

### Multi-Pass Generation

The RDE stage uses **multi-pass sub-stages** to generate the complete CPAT
codebase. Each sub-stage generates one application layer, keeping output
manageable and cross-layer dependencies explicit.

```
Pipeline: RHOSO Delivery — 5 stages

  Step 1/5: RHOSO DA             -> output/ciq-generators/, output/ciq-workbooks/
  Step 2/5: RHOSO DE [Ansible]   -> output/cpat/ansible/ (18 tasks, 15 templates)
  Step 3/5: RHOSO DE [Backend]   -> output/cpat/backend/ (Flask, 18 routes)
  Step 4/5: RHOSO DE [Frontend]  -> output/cpat/frontend/ (React, 11 components)
  Step 5/5: RHOSO DE [Docker]    -> output/cpat/Dockerfile, bringup.sh, USAGE.md
```

### Pipeline Deliverables

Pipeline stages generate **actual working files** — source code, Excel workbooks, and scripts.

**1. RHOSO Delivery** (full end-to-end — 5 stages)

| Stage | Sub-stage | Agent | Generates (files written to disk) |
|-------|-----------|-------|-----------------------------------|
| RDA | — | RHOSO DA | `output/ciq-generators/rhoso_ciq_schema.py` — CIQ schema (13 tables, 152+ params) |
| | | | `output/ciq-generators/generate_rhoso_ciq_workbooks.py` — Generator script |
| | | | `output/ciq-workbooks/rhoso/` — sample + template .xlsx workbooks |
| | | | `output/pipeline-reports/rda/` — Reference docs |
| RDE-1 | Ansible | RHOSO DE | `output/cpat/ansible/playbooks/roles/rhoso/tasks/` — 18 task files |
| | | | `output/cpat/ansible/playbooks/roles/rhoso/templates/` — 15 Jinja2 templates |
| | | | `output/cpat/ansible/playbooks/roles/rhoso/defaults/main.yml` — ~100 defaults |
| | | | `output/cpat/ansible/library/`, `module_utils/` — CIQ parser + schema |
| | | | `output/cpat/ansible.cfg` |
| RDE-2 | Backend | RHOSO DE | `output/cpat/backend/app.py` — Flask API (18 routes, streaming NDJSON) |
| | | | `output/cpat/backend/models.py`, `ciq_parser.py`, `ansible_runner.py` |
| | | | `output/cpat/backend/paths.py`, `input_files.py`, `version.py` |
| | | | `output/cpat/backend/requirements.txt` |
| RDE-3 | Frontend | RHOSO DE | `output/cpat/frontend/src/components/` — 11 React components |
| | | | `output/cpat/frontend/src/App.jsx`, `api.js`, `main.jsx`, `index.css` |
| | | | `output/cpat/frontend/package.json`, `vite.config.js`, `index.html` |
| | | | `output/cpat/frontend/nginx/default.conf` |
| RDE-4 | Docker | RHOSO DE | `output/cpat/Dockerfile` — Multi-stage build (Node 20 + Python 3.12 + Nginx) |
| | | | `output/cpat/docker/entrypoint.sh` — Gunicorn + Nginx startup |
| | | | `output/cpat/bringup.sh` — Podman build & run with YY.M.W versioning |
| | | | `output/cpat/USAGE.md` — Product documentation |

**2. RHOSO Design Architect** (RDA only — 1 stage)

| Stage | Agent | Generates |
|-------|-------|-----------|
| RDA | RHOSO DA | `output/ciq-generators/` — CIQ schema code + all generator scripts |
| | | `output/ciq-workbooks/` — All CIQ Excel workbooks (RHOSO + OCP) |

**3. RHOSO Deployment Engineer** (RDE only — 4 stages)

| Stage | Sub-stage | Agent | Generates |
|-------|-----------|-------|-----------|
| RDE-1 | Ansible | RHOSO DE | `output/cpat/ansible/` — Playbooks, roles, 15 templates, ~100 defaults |
| RDE-2 | Backend | RHOSO DE | `output/cpat/backend/` — Flask API, CIQ parser, Ansible runner |
| RDE-3 | Frontend | RHOSO DE | `output/cpat/frontend/` — React UI, Vite, Nginx |
| RDE-4 | Docker | RHOSO DE | `output/cpat/Dockerfile`, `docker/`, `bringup.sh`, `USAGE.md` |

### How to Trigger a Pipeline

Pipelines are triggered by typing the pipeline command in the Cursor chat, or
by clicking **Launch** on the
[CPAT Dashboard](tools/cpat-dashboard.canvas.tsx) canvas.

```
Run RHOSO delivery pipeline on @cpat
```

The Orchestrator agent activates, resolves the matching pipeline, announces
the execution plan, and runs each stage sequentially.

#### Pipeline Management Commands

| Command | Action |
|---------|--------|
| `Manage pipelines` | List all pipelines with status |
| `Create pipeline` | Guided custom pipeline creation |
| `Edit pipeline [name]` | Modify an existing pipeline |
| `Restore default pipelines` | Reset `context/pipelines.yaml` to defaults |

---

## Gates (Quality Checkpoints)

Gates are configurable pause-approve checkpoints between pipeline stages.
When enabled, the Orchestrator stops after each stage completes, displays a
file inventory with checklist results, and waits for user approval before
proceeding to the next stage.

Gate configuration lives in `context/team-config.yaml`:

```yaml
gates:
  enabled: true
  mode: pause-approve
  apply_to: pipeline          # pipeline | all
  checklist:
    require_source_traceability: true
    require_pii_clean: true
    require_no_unverified: true
    require_min_items: true
  skip_agents: []
```

### Gate Trigger Points

With the 5-stage RHOSO Delivery pipeline, a gate fires after each stage:

| After Stage | Gate Checkpoint Shows |
|-------------|----------------------|
| RDA | CIQ schema code + workbooks — file inventory |
| RDE-1 (Ansible) | 18 tasks, 15 templates, defaults — file inventory |
| RDE-2 (Backend) | Flask app, parser, runner — file inventory |
| RDE-3 (Frontend) | React components, Vite config — file inventory |
| RDE-4 (Docker) | Dockerfile, bringup.sh, USAGE.md — file inventory |

### Checklist Items

Each gate verifies four quality checks against the stage output:

| Check | What It Validates |
|-------|-------------------|
| `require_source_traceability` | Every output traces back to a source (RHOSO PDF, CIQ schema, or project artifact) |
| `require_pii_clean` | No secrets, passwords, or PII in generated files |
| `require_no_unverified` | No unverified assumptions — all flagged with `[ASSUMPTION:]` tags |
| `require_min_items` | Minimum number of output files generated with non-zero size |

### Gate Behavior

| Setting | Effect |
|---------|--------|
| `enabled: true` | Gates are active for pipelines |
| `enabled: false` | All stages run without pausing |
| `apply_to: pipeline` | Gates apply only during pipeline execution |
| `apply_to: all` | Gates apply to every agent invocation |
| `skip_agents: [agent]` | Skip gates for specific agents |

### Gate Responses

At each checkpoint the user can respond with:

| Response | Action |
|----------|--------|
| `approve` / `next` / `continue` | Proceed to the next stage |
| `approve all` | Disable gates for all remaining stages |
| `skip` | Skip current gate (marked as "skipped") |
| `reject: [reason]` | Re-run the agent with the provided feedback |

### Overriding Gates in Prompts

- Add **"with gates"** or **"with checklist"** to force gates ON
- Add **"no gates"** to force gates OFF

```
Run RHOSO delivery pipeline on @cpat with gates
Run RHOSO DA pipeline on @cpat no gates
```
