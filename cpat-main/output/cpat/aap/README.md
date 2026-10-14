# CPAT — Ansible Automation Platform (AAP) 2.5 Integration

Run CPAT OCP and RHOSO deployments via AAP instead of the CPAT UI.
The same Ansible playbooks, roles, and modules are used — zero code changes.

## Architecture

```
AAP Controller
├── Workflow Templates (full install sequences)
│   ├── CPAT OCP ABI Full Install       (11 steps, connected)
│   ├── CPAT OCP ABI-DC Full Install    (14 steps, disconnected)
│   ├── CPAT RHOSO Full Install         (19 steps)
│   └── CPAT OCP Destroy                (1 step)
│
├── Job Templates (individual tasks)
│   ├── CPAT OCP Install     → ocp_install.yml    (26 tasks via survey)
│   ├── CPAT OCP Validate    → ocp_validate.yml   (CIQ validation)
│   ├── CPAT RHOSO Install   → main.yml --tags rhoso  (19 tasks via survey)
│   └── CPAT RHOSO Register  → main.yml --tags register
│
├── Custom Credential Types
│   ├── CPAT Bastion SSH     (SSH key + user → bastion delegate_to)
│   ├── CPAT BMC Credentials (Redfish API user/password)
│   └── CPAT Pull Secret     (OpenShift pull secret JSON → temp file)
│
└── Execution Environment: CPAT EE
    ├── ansible-core 2.16 + openpyxl
    ├── oc + openshift-install binaries
    └── CPAT custom modules (library/ + module_utils/)
```

## Artifact Ownership

AAP artifacts are split across two agents to maintain separation of concerns:

| Agent | Sub-stage | Files Generated |
|-------|-----------|-----------------|
| **ODE-5** (OCP Deployment Engineer) | AAP | `execution-environment/` (4 files), `exports/credential-types.yml`, `exports/ocp-job-templates.yml`, `exports/ocp-workflow-templates.yml`, `exports/all-objects.yml`, `README.md` |
| **RDE-5** (RHOSO Deployment Engineer) | AAP | `exports/rhoso-job-templates.yml`, `exports/rhoso-workflow-templates.yml` |

## Quick Start

### 1. Build the Execution Environment

Prerequisites: `ansible-builder` installed (`pip install ansible-builder`).

```bash
cd output/cpat/aap/execution-environment/

# Place OCP binaries in output/cpat/binaries/ before building:
#   - openshift-install (or openshift-install-linux.tar.gz)
#   - oc (or openshift-client-linux.tar.gz)
#   - Optional: mirror-registry-amd64.tar.gz, oc-mirror-rhel9-linux-amd64.tar.gz

ansible-builder build \
  --tag cpat-ee:latest \
  --file execution-environment.yml \
  --container-runtime podman
```

Push to your container registry:

```bash
podman tag cpat-ee:latest registry.example.com/cpat-ee:latest
podman push registry.example.com/cpat-ee:latest
```

### 2. Create AAP Prerequisites

In the AAP UI (or via API), create:

| Object | Details |
|--------|---------|
| **Organization** | `Default` (exists by default) |
| **Execution Environment** | `CPAT EE` — image: `registry.example.com/cpat-ee:latest` |
| **Project** | `CPAT` — SCM Type: Git, URL: `<your CPAT repo URL>`, Branch: `main` |
| **Inventory** | `CPAT Localhost` — add host `localhost` with variable `ansible_connection: local` |

### 3. Import AAP Objects

```bash
# Import all objects at once (credential types + all job/workflow templates)
awx-manage import < exports/all-objects.yml

# Or import individually:
awx-manage import < exports/credential-types.yml
awx-manage import < exports/ocp-job-templates.yml
awx-manage import < exports/ocp-workflow-templates.yml
awx-manage import < exports/rhoso-job-templates.yml
awx-manage import < exports/rhoso-workflow-templates.yml
```

### 4. Create Credentials

After importing credential types, create credential instances:

| Credential | Type | Fields |
|------------|------|--------|
| `Troshka Bastion SSH` | CPAT Bastion SSH | `bastion_ssh_user: cloud-user`, `bastion_ssh_key: <PEM key>` |
| `Troshka BMC` | CPAT BMC Credentials | `bmc_user: admin`, `bmc_password: <password>` |
| `OCP Pull Secret` | CPAT Pull Secret | `pull_secret_content: <JSON from console.redhat.com>` |

Assign these credentials to the `CPAT OCP Install` job template.

### 5. Upload CIQ File

The CIQ Excel workbook must be accessible to the Ansible controller at runtime.
Options:

1. **Project files** — Place the CIQ in the CPAT git repo (e.g. `input/ocp/ciq/site.xlsx`)
   and use a relative path in the survey.

2. **Shared mount** — Mount a shared NFS/volume to the EE and place CIQ files there.
   Use the absolute path in the survey (e.g. `/mnt/ciq/site.xlsx`).

3. **AAP artifacts** — Upload via AAP API and reference the artifact path.

## Usage

### Run a Single Task

1. Go to **Templates** → **CPAT OCP Install** → **Launch**
2. Fill in the survey:
   - **OCP Task**: Select from dropdown (e.g. `bastion_preparation`)
   - **CIQ File Path**: Path to CIQ workbook
   - **Cluster Name**: Must match CIQ `Cluster Name` field
   - **OCP Version**: e.g. `4.20`
3. Click **Launch**

### Run a Full OCP Install

1. Go to **Templates** → **CPAT OCP ABI Full Install** → **Launch**
2. Fill in the workflow survey (CIQ path, cluster name, version)
3. Click **Launch**
4. Monitor progress in the workflow visualizer — each node runs sequentially

### Run a Full RHOSO Install

1. Go to **Templates** → **CPAT RHOSO Full Install** → **Launch**
2. Fill in the workflow survey (CIQ path, cluster name, version)
3. Click **Launch**

### Destroy an OCP Cluster

1. Go to **Templates** → **CPAT OCP Destroy** → **Launch**
2. Fill in CIQ path, cluster name, version
3. Click **Launch**

## File Structure

```
aap/
├── execution-environment/                  # ODE-5 owns
│   ├── execution-environment.yml           # ansible-builder v3 EE definition
│   ├── requirements.yml                    # Galaxy collections (none currently)
│   ├── requirements.txt                    # Python: openpyxl==3.1.5
│   └── bindep.txt                          # System: python3-devel, jq, openssh-clients
├── exports/
│   ├── all-objects.yml                     # ODE-5 — unified import (everything merged)
│   ├── credential-types.yml                # ODE-5 — 3 custom credential types
│   ├── ocp-job-templates.yml               # ODE-5 — 2 OCP job templates with surveys
│   ├── ocp-workflow-templates.yml          # ODE-5 — 3 OCP workflow templates
│   ├── rhoso-job-templates.yml             # RDE-5 — 2 RHOSO job templates with surveys
│   └── rhoso-workflow-templates.yml        # RDE-5 — 1 RHOSO workflow template
└── README.md                               # ODE-5 — this file
```

## Job Templates Reference

| Job Template | Playbook | Survey Key | Tasks | Owner |
|---|---|---|---|---|
| CPAT OCP Install | `ocp_install.yml` | `ocp_task` | 26 OCP tasks | ODE-5 |
| CPAT OCP Validate | `ocp_validate.yml` | — | CIQ validation | ODE-5 |
| CPAT RHOSO Install | `main.yml` (tags: rhoso) | `installation_task` | 19 RHOSO tasks | RDE-5 |
| CPAT RHOSO Register | `main.yml` (tags: register) | `registration_target` | Cluster registration | RDE-5 |

## Workflow Templates Reference

| Workflow | Steps | Duration (typical) | Owner |
|---|---|---|---|
| CPAT OCP ABI Full Install | 11 nodes (prerequisites → node_readiness) | 60–90 min | ODE-5 |
| CPAT OCP ABI-DC Full Install | 14 nodes (+ mirror steps) | 90–150 min | ODE-5 |
| CPAT RHOSO Full Install | 19 nodes (manifest_generation → observability) | 60–120 min | RDE-5 |
| CPAT OCP Destroy | 1 node | 5–15 min | ODE-5 |

## Compatibility Notes

- **ansible.cfg**: The existing `ansible.cfg` sets `library` and `module_utils` paths
  relative to CWD. AAP uses the project root as CWD, so paths resolve correctly.

- **delegate_to**: OCP tasks delegate to bastion via `delegate_to` with SSH vars
  from CIQ-parsed facts. The `CPAT Bastion SSH` credential injects the SSH key
  as a temp file and passes the path via extra var.

- **Async tasks**: Long-running tasks (bootstrap, oc-mirror, etc.) use Ansible
  `async/poll: 0` + `async_status`. AAP supports this natively. Set job timeout
  to 14400s (4 hours) for safety.

- **no_log**: Pull-secret tasks use `no_log: true` — respected by both CPAT and AAP.

- **cpat_execution_uuid**: This CPAT-specific variable is absent in AAP runs.
  All tasks handle this gracefully with `default('unknown')` fallback. Logs are
  still written to the bastion and visible in AAP job output.

- **CPAT UI features not available in AAP**: Manifest review panel, command log
  streaming, execution history table. AAP provides its own job log viewer instead.

## Customization

### Adding a new OCP version

1. Update the survey `choices` in `ocp-job-templates.yml` and `ocp-workflow-templates.yml`
2. Rebuild the EE with the new version's `openshift-install` binary

### Adding a new OCP task

1. Create the Ansible task file in `roles/ocp/tasks/<subdir>/`
2. Add the task to `OCP_INSTALLATION_TASK_TAGS` in `ansible_runner.py` (for CPAT UI)
3. Add the task value to the survey `choices` in `exports/ocp-job-templates.yml`
4. If part of a workflow, add a new node in `exports/ocp-workflow-templates.yml`
5. Re-import: `awx-manage import < exports/all-objects.yml`

### Adding a new RHOSO task

1. Create the Ansible task file in `roles/rhoso/tasks/<subdir>/`
2. Add the task to `RHOSO_INSTALLATION_TASK_TAGS` in `ansible_runner.py` (for CPAT UI)
3. Add the task value to the survey `choices` in `exports/rhoso-job-templates.yml`
4. If part of a workflow, add a new node in `exports/rhoso-workflow-templates.yml`
5. Re-import: `awx-manage import < exports/all-objects.yml`

### Skipping workflow steps

AAP workflow templates support disabling individual nodes. In the workflow
visualizer, right-click a node and select "Disable" to skip it during the
next run. Useful for resuming after a partial failure.
