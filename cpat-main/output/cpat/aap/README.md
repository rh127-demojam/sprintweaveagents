# Ansible Automation Platform (AAP) 2.5 Integration

Run OCP and RHOSO deployments via AAP.
The same Ansible playbooks, roles, and modules are used — zero code changes.

## Architecture

```
AAP Controller
├── Workflow Templates (full install sequences)
│   ├── OCP ABI Full Install            (connected — 15 steps)
│   ├── OCP ABI-DC Full Install         (disconnected — 18 steps)
│   ├── RHOSO Full Install              (19 steps)
│   └── OCP Destroy                     (cleanup — 1 step)
│
├── Job Templates (47 individual tasks)
│   ├── OCP Generate Manifests          → ocp_install.yml
│   ├── OCP Prerequisites              → ocp_install.yml
│   ├── OCP Bastion Preparation         → ocp_install.yml
│   ├── OCP DNS DHCP Validation         → ocp_install.yml
│   ├── OCP NTP Sync                    → ocp_install.yml
│   ├── OCP Mirror Registry Install     → ocp_install.yml
│   ├── OCP OC Mirror Execution         → ocp_install.yml
│   ├── OCP IDMS ITMS Configuration     → ocp_install.yml
│   ├── OCP Generate Install Config     → ocp_install.yml
│   ├── OCP Generate Agent Config       → ocp_install.yml
│   ├── OCP Generate NMState Configs    → ocp_install.yml
│   ├── OCP Generate Ignition Configs   → ocp_install.yml
│   ├── OCP Create Agent ISO            → ocp_install.yml
│   ├── OCP Boot Nodes From ISO         → ocp_install.yml
│   ├── OCP Bootstrap Cluster           → ocp_install.yml
│   ├── OCP Wait Install Complete       → ocp_install.yml
│   ├── OCP Approve CSRs                → ocp_install.yml
│   ├── OCP Configure Authentication    → ocp_install.yml
│   ├── OCP Day-2 Operator Installation → ocp_install.yml
│   ├── OCP MetalLB Configuration       → ocp_install.yml
│   ├── OCP SR-IOV Multus Configuration → ocp_install.yml
│   ├── OCP Cluster Health Check        → ocp_install.yml
│   ├── OCP Node Readiness Check        → ocp_install.yml
│   ├── OCP Full Install                → ocp_install.yml
│   ├── OCP Uninstall Mirror Registry   → ocp_install.yml
│   ├── OCP Destroy Cluster             → ocp_install.yml
│   ├── OCP Validate                    → ocp_validate.yml
│   ├── RHOSO Generate Manifests        → main.yml --tags rhoso
│   ├── RHOSO Pre-requisites            → main.yml --tags rhoso
│   ├── RHOSO Verify Required CRDs      → main.yml --tags rhoso
│   ├── ... (19 RHOSO task templates)
│   └── RHOSO Register                  → main.yml --tags register
│
├── Custom Credential Types
│   ├── Bastion SSH            (SSH key + user → bastion delegate_to)
│   ├── BMC Credentials        (Redfish API user/password)
│   └── Pull Secret            (OpenShift pull secret JSON → temp file)
│
└── Execution Environment (AAP default — no custom EE needed)
```

> **Note:** A custom Execution Environment is not required. OCP binaries
> (`openshift-install`, `oc`, etc.) run on the **bastion** via `delegate_to`,
> not on the AAP controller. The AAP default EE has everything needed.

## Quick Start

### 1. Find Your AAP Controller URL

SSH into the AAP controller host and probe the API:

```bash
ssh rhel@control

# Step 1 — Discover available API services
curl -sk https://localhost/api/

# Expected output (AAP 2.5 Gateway):
# {"description":"AAP gateway REST API","apis":{"gateway":"/api/gateway/","controller":"/api/controller/","eda":"/api/eda/"}}

# Step 2 — Verify the controller API responds
curl -sk https://localhost/api/controller/v2/ping/

# Expected output:
# {"ha":false,"version":"4.6.7","active_node":"control.ansible.workshop",...}

# Step 3 — Test authentication
curl -sk -u admin:'ansible123!' https://localhost/api/controller/v2/me/ | python3 -m json.tool
```

> **Note:** If running the import script from your **local laptop** (not from the controller),
> use the controller's external hostname/IP instead of `localhost`:
> ```bash
> export AAP_URL=https://control.ansible.workshop
> ```

> **Tip:** The import script's `detect_api_base()` function automatically detects whether your AAP
> uses the Gateway path (`/api/controller/v2/`) or the standalone path (`/api/v2/`), so the
> same `AAP_URL` works for both deployment types.

---

### 2. Import AAP Objects (`import-via-api.sh`)

The import script creates all AAP objects via REST API. It only needs `curl` and `python3` —
run it from any machine that can reach the AAP controller (your laptop, the controller itself, etc.).

```bash
export AAP_URL=https://localhost
export AAP_USER=admin
export AAP_PASS='ansible123!'

# Point to your GitLab repo (private)
export SCM_URL=https://gitlab.com/rh-global-services-auto/cpat.git
export SCM_CREDENTIAL="GitLab SCM"            # credential name to use/create
export SCM_USERNAME="your-gitlab-username"    # creates credential if it doesn't exist
export SCM_PASSWORD="glpat-xxxxxxxxxxxx"      # GitLab PAT with read_repository scope
export SCM_BRANCH=main                        # optional, defaults to main

bash import-via-api.sh
```

| Environment Variable | Required | Default | Description |
|---|---|---|---|
| `AAP_URL` | Yes | — | AAP controller URL (e.g. `https://localhost`) |
| `AAP_USER` | No | `admin` | AAP username |
| `AAP_PASS` | Yes | — | AAP password |
| `SCM_URL` | No | — | Git URL for the Ansible project |
| `SCM_CREDENTIAL` | No | — | Name of Source Control credential to use or create |
| `SCM_USERNAME` | No | — | Git username (used to create `SCM_CREDENTIAL` if it doesn't exist) |
| `SCM_PASSWORD` | No | — | Git personal access token (used to create `SCM_CREDENTIAL` if it doesn't exist) |
| `SCM_BRANCH` | No | `main` | Git branch to sync |
| `PLAYBOOK_PREFIX` | No | `output/cpat` | Path from repo root to the ansible directory |

> **Note:** For **public repos**, omit `SCM_CREDENTIAL`, `SCM_USERNAME`, and `SCM_PASSWORD`.
> The script creates the Source Control credential automatically if `SCM_CREDENTIAL` is set
> but doesn't exist yet — no need to create it manually in the AAP UI.

**What the script creates:**

| Step | API Endpoint | Objects Created |
|:----:|-------------|-----------------|
| 1 | `POST /credential_types/` | 3 custom credential types (Bastion SSH, BMC, Pull Secret) |
| 2 | `POST /inventories/` | Inventory `Automation Localhost` with `localhost` host |
| 3 | `POST /credentials/` | Source Control credential (if `SCM_CREDENTIAL` + `SCM_USERNAME` + `SCM_PASSWORD` set) |
| 4 | `POST /projects/` | Project `Cloud Platform Automation` with GitLab SCM sync |
| 5 | `POST /job_templates/` | 47 job templates (27 OCP + 20 RHOSO) — one per task |
| 6 | `POST /job_templates/{id}/survey_spec/` | Surveys attached to each template |
| 7 | `POST /job_templates/{id}/credentials/` | Attaches credentials to all OCP job templates |
| 8 | `POST /workflow_job_templates/` | 4 workflow templates (ABI, ABI-DC, Destroy, RHOSO) |
| 9 | `POST /workflow_job_templates/{id}/workflow_nodes/` | Workflow nodes wired in sequential on-success chains |

**HTTP response codes:**
- `201` — Created successfully
- `200` — Survey attached / credential linked
- `400` — Object already exists (safe to re-run)
- `401` — Authentication failed (check AAP_USER/AAP_PASS)

> **Note:** The script is idempotent — re-running it skips existing objects (400) and only creates missing ones.

**If SCM sync fails** (e.g. credential not attached on first run), fix the project manually:

```bash
# Attach the credential to the existing project and trigger sync
PROJECT_ID=<project-id-from-script-output>
CRED_ID=<gitlab-scm-credential-id>

curl -sk -X PATCH -u admin:'ansible123!' \
  -H "Content-Type: application/json" \
  "https://localhost/api/controller/v2/projects/${PROJECT_ID}/" \
  -d "{\"credential\": ${CRED_ID}}" -o /dev/null -w "Patch: %{http_code}\n"

curl -sk -X POST -u admin:'ansible123!' \
  "https://localhost/api/controller/v2/projects/${PROJECT_ID}/update/" \
  -o /dev/null -w "Sync triggered: %{http_code}\n"

# Wait and check
sleep 15
curl -sk -u admin:'ansible123!' \
  "https://localhost/api/controller/v2/projects/${PROJECT_ID}/" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Status:', d.get('status'))"
# Expected: Status: successful

# Then re-run: bash import-via-api.sh
```

---

### 3. Cleanup (`cleanup-via-api.sh`)

To remove all resources created by the import script:

```bash
export AAP_URL=https://localhost
export AAP_USER=admin
export AAP_PASS='ansible123!'

# Dry run — preview what will be deleted
bash cleanup-via-api.sh

# Actually delete everything
bash cleanup-via-api.sh --confirm
```

Deletion order (respects dependencies): Workflows → Job Templates → Credential Instances → Credential Types → Project → Inventory.

---

### 4. Create Credential Instances (for running jobs)

After the import, create credential **instances** in AAP UI with actual secrets for your target environment:

| Credential Name | Type | Fields |
|---|---|---|
| `Troshka Bastion SSH` | Bastion SSH | `bastion_ssh_user: cloud-user`, `bastion_ssh_key: <PEM key>` |
| `Troshka BMC` | BMC Credentials | `bmc_user: admin`, `bmc_password: password` |
| `OCP Pull Secret` | Pull Secret | `pull_secret_content: <JSON from console.redhat.com>` |

Then attach these credentials to the OCP job templates (via AAP UI or the script will do it automatically on re-run if the credentials exist).

### 5. Upload CIQ File

The CIQ Excel workbook must be accessible to the Ansible controller at runtime.
Options:

1. **Project files** — Place the CIQ in the git repo (e.g. `input/ocp/ciq/site.xlsx`)
   and use a relative path in the survey.

2. **Shared mount** — Mount a shared NFS/volume to the EE and place CIQ files there.
   Use the absolute path in the survey (e.g. `/mnt/ciq/site.xlsx`).

3. **AAP artifacts** — Upload via AAP API and reference the artifact path.

## Usage

### Run a Single Task

1. Go to **Templates** → **OCP Bastion Preparation** (or any task) → **Launch**
2. Fill in the survey:
   - **CIQ File Path**: Path to CIQ workbook
   - **Cluster Name**: Must match CIQ `Cluster Name` field
   - **OCP Version**: e.g. `4.22`
3. Click **Launch**

Each job template has the task pre-configured via `extra_vars` — no dropdown selection needed.

### Run a Full OCP Install

1. Go to **Templates** → **OCP ABI Full Install** → **Launch**
2. Fill in the workflow survey (CIQ path, cluster name, version)
3. Click **Launch**
4. Monitor progress in the workflow visualizer — each node runs sequentially

### Run a Full RHOSO Install

1. Go to **Templates** → **RHOSO Full Install** → **Launch**
2. Fill in the workflow survey (CIQ path, cluster name, version)
3. Click **Launch**

### Destroy an OCP Cluster

1. Go to **Templates** → **OCP Destroy** → **Launch**
2. Fill in CIQ path, cluster name, version
3. Click **Launch**

## File Structure

```
aap/
├── import-via-api.sh                   # REST API import script (creates all AAP objects)
├── cleanup-via-api.sh                  # REST API cleanup script (removes all AAP objects)
└── README.md                           # This file
```

## Job Templates Reference

### OCP Job Templates (27)

| # | Job Template | Task Tag | Group |
|---|---|---|---|
| 1 | OCP Generate Manifests | `generate_manifests` | Generate |
| 2 | OCP Prerequisites | `prerequisites` | Prerequisites |
| 3 | OCP Bastion Preparation | `bastion_preparation` | Prerequisites |
| 4 | OCP DNS DHCP Validation | `dns_dhcp_validation` | Prerequisites |
| 5 | OCP NTP Sync | `ntp_sync` | Prerequisites |
| 6 | OCP Mirror Registry Install | `mirror_registry` | Mirror |
| 7 | OCP OC Mirror Execution | `oc_mirror` | Mirror |
| 8 | OCP IDMS ITMS Configuration | `idms_itms_config` | Mirror |
| 9 | OCP Generate Install Config | `install_config` | Config |
| 10 | OCP Generate Agent Config | `agent_config` | Config |
| 11 | OCP Generate NMState Configs | `nmstate_configs` | Config |
| 12 | OCP Generate Ignition Configs | `ignition_configs` | Ignition |
| 13 | OCP Create Agent ISO | `agent_iso` | Ignition |
| 14 | OCP Boot Nodes From ISO | `boot_nodes` | Ignition |
| 15 | OCP Bootstrap Cluster | `bootstrap` | Bootstrap |
| 16 | OCP Wait Install Complete | `wait_install` | Bootstrap |
| 17 | OCP Approve CSRs | `approve_csrs` | Cluster Config |
| 18 | OCP Configure Authentication | `auth_config` | Cluster Config |
| 19 | OCP Day-2 Operator Installation | `day2_operators` | Cluster Config |
| 20 | OCP MetalLB Configuration | `metallb_config` | Network |
| 21 | OCP SR-IOV Multus Configuration | `sriov_config` | Network |
| 22 | OCP Cluster Health Check | `health_check` | Validation |
| 23 | OCP Node Readiness Check | `node_readiness` | Validation |
| 24 | OCP Full Install | `full_install` | All-in-one |
| 25 | OCP Uninstall Mirror Registry | `uninstall_mirror_registry` | Cleanup |
| 26 | OCP Destroy Cluster | `destroy_cluster` | Cleanup |
| 27 | OCP Validate | *(separate playbook)* | CIQ |

### RHOSO Job Templates (20)

| # | Job Template | Task Path | Group |
|---|---|---|---|
| 1 | RHOSO Generate Manifests | `manifests/manifest_generation` | Generate |
| 2 | RHOSO Pre-requisites | `prerequisites/prerequisites` | Prerequisites |
| 3 | RHOSO Verify Required CRDs | `common/_verify_required_crds` | Prerequisites |
| 4 | RHOSO Prerequisite Operator Installation | `prerequisites/prerequisite_operator_installation` | Prerequisites |
| 5 | RHOSO Disconnected Environment Preparation | `prerequisites/disconnected_environment_preparation` | Prerequisites |
| 6 | RHOSO Generate OSP Secret | `secrets/generate_osp_secret` | Secrets |
| 7 | RHOSO Generate Data Plane Secrets | `secrets/generate_data_plane_secrets` | Secrets |
| 8 | RHOSO Generate Ceph Secret | `secrets/generate_ceph_secret` | Secrets |
| 9 | RHOSO Persistent Storage Configuration | `storage/persistent_storage_configuration` | Storage |
| 10 | RHOSO Trident Storage Configuration | `storage/trident_storage_configuration` | Storage |
| 11 | RHOSO Generate Storage CRs | `storage/_generate_storage_crs` | Storage |
| 12 | RHOSO OpenStack Operator Installation | `control_plane/openstack_operator_installation_and_preparation` | Control Plane |
| 13 | RHOSO RHOCP Preparation | `control_plane/rhocp_preparation_for_rhoso` | Control Plane |
| 14 | RHOSO Control Plane Deployment | `control_plane/control_plane_deployment_and_verification` | Control Plane |
| 15 | RHOSO Control Plane Customization | `control_plane/control_plane_customization` | Control Plane |
| 16 | RHOSO Network Preparation | `network/network_preparation` | Network |
| 17 | RHOSO Data Plane Deployment | `data_plane/data_plane_deployment_and_verification` | Data Plane |
| 18 | RHOSO Post-Deployment Validation | `post_deployment/post_deployment_validation` | Post-Deploy |
| 19 | RHOSO Observability Configuration | `post_deployment/observability_configuration` | Post-Deploy |
| 20 | RHOSO Register | *(tag: register)* | Register |

## Workflow Templates Reference

| Workflow | Steps | Duration (typical) |
|---|---|---|
| OCP ABI Full Install | 15 steps: Prerequisites → Install Config → Agent Config → NMState → Agent ISO → Boot Nodes → Bootstrap → Wait Install → CSRs → Auth → Day-2 → MetalLB → SR-IOV → Health Check → Node Readiness | 60–90 min |
| OCP ABI-DC Full Install | 18 steps: Prerequisites → Mirror Registry → OC Mirror → IDMS/ITMS → Install Config → Agent Config → NMState → Agent ISO → Boot Nodes → Bootstrap → Wait Install → CSRs → Auth → Day-2 → MetalLB → SR-IOV → Health Check → Node Readiness | 90–150 min |
| RHOSO Full Install | 19 steps: Generate Manifests → Prerequisites → Verify CRDs → Operator Install → Disconnected Prep → OSP Secret → DP Secrets → Ceph Secret → Storage → Trident → Storage CRs → OpenStack Operator → RHOCP Prep → Control Plane → CP Customization → Network → Data Plane → Validation → Observability | 60–120 min |
| OCP Destroy | 1 step: Destroy Cluster | 5–15 min |

## Compatibility Notes

- **ansible.cfg**: The existing `ansible.cfg` sets `library` and `module_utils` paths
  relative to CWD. AAP uses the project root as CWD, so paths resolve correctly.

- **delegate_to**: OCP tasks delegate to bastion via `delegate_to` with SSH vars
  from CIQ-parsed facts. The `Bastion SSH` credential injects the SSH key
  as a temp file and passes the path via extra var.

- **Async tasks**: Long-running tasks (bootstrap, oc-mirror, etc.) use Ansible
  `async/poll: 0` + `async_status`. AAP supports this natively. Set job timeout
  to 14400s (4 hours) for safety.

- **no_log**: Pull-secret tasks use `no_log: true` — respected by AAP.

## Customization

### Adding a new OCP task

1. Create the Ansible task file in `roles/ocp/tasks/<subdir>/`
2. Add a `create_ocp_jt` call in `import-via-api.sh` (Section 3)
3. Add an `attach_ocp_survey` call in `import-via-api.sh` (Section 4)
4. If part of a workflow, add the job template name to the `wire_workflow` call (Section 7)
5. Add the template name to `cleanup-via-api.sh` OCP_JOB_TEMPLATES array
6. Re-run: `bash import-via-api.sh`

### Adding a new RHOSO task

1. Create the Ansible task file in `roles/rhoso/tasks/<subdir>/`
2. Add a `create_rhoso_jt` call in `import-via-api.sh` (Section 3)
3. Add an `attach_rhoso_survey` call in `import-via-api.sh` (Section 4)
4. If part of a workflow, add the job template name to the `wire_workflow` call (Section 7)
5. Add the template name to `cleanup-via-api.sh` RHOSO_JOB_TEMPLATES array
6. Re-run: `bash import-via-api.sh`

### Skipping workflow steps

AAP workflow templates support disabling individual nodes. In the workflow
visualizer, right-click a node and select "Disable" to skip it during the
next run. Useful for resuming after a partial failure.
