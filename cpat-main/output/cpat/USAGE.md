# CPAT — Cloud Platform Automation Tool

Complete product documentation for CPAT — RHOSO 18.0 + OCP 4.17–4.20 deployment automation.

- RHOSO CIQ Schema v1.4 — 19 Jinja templates, 24 task files, 18 CIQ tables, ~210 defaults
- OCP CIQ Schema v1.1 — 12 Jinja templates, 27 task files, 18 CIQ tables (14 param + 4 row), 177 fields

**Version:** tag/API `YY.M.W`; UI displays `vYY.M.W`

---

## Table of Contents

- [Product Overview](#product-overview)
- [Quick Start](#quick-start)
- [Registration Workflow](#registration-workflow)
- [Generation Workflow](#generation-workflow)
- [Deployment Workflow](#deployment-workflow)
- [RHOSO Installation Tasks (19)](#rhoso-installation-tasks)
- [OCP Installation Tasks (22)](#ocp-installation-tasks)
- [Input Files Reference](#input-files-reference)
- [CIQ Parameter Reference (18 tables)](#ciq-parameter-reference)
- [OCP CIQ Parameter Reference (18 tables)](#ocp-ciq-parameter-reference)
- [Manifest Catalog (19 templates)](#manifest-catalog)
- [OCP Manifest Catalog (12 templates)](#ocp-manifest-catalog)
- [Cluster Commands by Phase](#cluster-commands-by-phase)
- [Troubleshooting Guide](#troubleshooting-guide)

---

## Product Overview

CPAT (Cloud Platform Automation Tool) automates deployment of:

- **Red Hat OpenStack Services on OpenShift (RHOSO) 18.0** on an existing RHOCP cluster
- **OpenShift Container Platform (OCP) 4.17–4.20** installation on bare metal

It provides a web UI for CIQ-driven manifest generation, review, and deployment.

**Architecture:**

```
React UI → Flask API → Ansible Runner → OpenShift (via kubeconfig / openshift-install)
```

**Supported products:**
- **RHOSO 18.0** on RHOCP 4.16+ — Full deployment automation
- **OCP 4.17–4.20** — ABI, IPI-BM, UPI-BM, ABI-DC, SNO installation methods

**What CPAT automates:**

- CIQ (Customer Installation Questionnaire) parsing — 18 parameter tables, 203 parameters
- Manifest generation — 19 Jinja templates producing all RHOSO deployment CRs
- Operator installation — NMState, MetalLB, Cert-Manager, HA operators, LSO, Observability
- Secret generation — osp-secret (19 service passwords), data plane secrets, Ceph secret
- Storage configuration — PVC validation, LSO local volumes, Trident NetApp CSI
- Network preparation — NNCP, NAD, MetalLB, NetConfig
- Control plane deployment — OpenStackControlPlane CR (fully CIQ-driven, ~555 lines)
- Data plane deployment — NodeSet, Deployment, BareMetalHost (provisioned/unprovisioned)
- Observability — Cluster Observability Operator + MonitoringStack
- Post-deployment validation — CLI smoke tests

---

## Quick Start

### Container deployment (recommended)

```bash
# Build and start CPAT (Podman)
./bringup.sh build
./bringup.sh start

# Access the UI
open http://localhost:8080
# Login: admin / admin
```

### Container management

```bash
./bringup.sh build     # Build the container image (downloads OCP binaries)
./bringup.sh start     # Start container (build if image missing)
./bringup.sh stop      # Stop and remove container
./bringup.sh restart   # Stop, rebuild, and start
./bringup.sh logs      # Tail container logs
./bringup.sh shell     # Open shell inside running container
./bringup.sh export    # Save image as .tar for transfer to disconnected bastion
```

### OCP binaries in container

The Dockerfile automatically downloads OCP binaries (`openshift-install`, `oc`,
`kubectl`, `oc-mirror`) from `mirror.openshift.com` during the build.
Default version is **4.20**; override with:

```bash
podman build --build-arg OCP_VERSION=4.19 -t cpat:25.10.1 .
```

Alternatively, place pre-downloaded binaries in `binaries/` before building.

### Disconnected deployment workflow

```bash
# On connected machine:
./bringup.sh build          # Build image (downloads OCP 4.20 binaries)
./bringup.sh export         # Creates cpat-25.10.1.tar

# Transfer to bastion:
scp -P 2222 cpat-25.10.1.tar pull-secret.json cloud-user@<bastion>:~/

# On bastion:
podman load -i cpat-25.10.1.tar
./bringup.sh start
```

### Local development

```bash
# Backend
cd backend && pip install -r requirements.txt
CPAT_DATA_DIR=../data python app.py

# Frontend
cd frontend && npm install && npm run dev
```

### Version scheme

CPAT uses `YY.M.W` (year.month.week-of-month):
- Image tags: `cpat:25.9.4`
- UI display: `v25.9.4`
- Override: `CPAT_VERSION=25.9.4 ./bringup.sh build`

---

## Registration Workflow

Registration parses a CIQ `.xlsx` workbook and creates a RHOSO environment in CPAT.

### Steps

1. **Navigate** to Register Cluster in the CPAT UI
2. **Upload** a CIQ workbook (`.xlsx`) with a `rhoso_details` table containing `Type = RHOSO`
3. **Upload input files** (optional at registration; can be added later via Dashboard → Input Files):
   - Kubeconfig (cluster-admin)
   - Pull secret (registry auth)
   - SSH private key (data plane Ansible access)
   - Ceph keyring (when Ceph External = yes)
   - NetApp config (when Trident Enabled = yes)
   - Multipath config (when Multipath Enabled = yes)
4. **Click Register** — CPAT parses CIQ parameters, networks, and nodes; creates inventory
5. **Verify** — Cluster appears in the sidebar

### CIQ requirements

- Must contain a `rhoso_details` table with `Type = RHOSO`
- Supplemental tables (`rhoso_access`, `rhoso_storage`, etc.) on any sheet are merged
- Network rows (`rhoso_networks`) collected from all sheets
- Node rows (`rhoso_data_plane_nodes`) collected from all sheets

### Manual registration

```bash
ansible-playbook ansible/playbooks/main.yml --tags register \
  -e '{"ciq_file_path":"path/to/ciq.xlsx","cluster_description":"","registration_target":"rhoso"}'
```

---

## Generation Workflow

Generate manifests for review before applying to the cluster.

### Steps

1. **Select cluster** in the CPAT sidebar
2. **Click "Generate Manifests for Review"** — renders all CRs from CIQ into artifacts
3. **Review** — open Artifacts Panel to view, download, or ZIP-download all manifests
4. **Edit** — modify any YAML if needed (download, edit, re-upload is supported)

### What gets generated

All 19 templates are rendered based on CIQ parameters. Conditional templates
(disconnected, LSO, Trident, observability, multipath, BMH, NMState secrets,
CPU pinning) are only generated when their CIQ conditions are met.

Output directory: `<CPAT_DATA_DIR>/artifacts/<cluster>/`

### Flags

| Flag | Value | Effect |
|------|-------|--------|
| `rhoso_apply_manifests` | `false` | No `oc apply` — templates only |
| `rhoso_skip_generation` | `false` | Run Jinja rendering |

---

## Deployment Workflow

Deploy reviewed manifests to the RHOCP cluster.

### Steps

1. **Ensure** Generate + Review are complete
2. **Select deployment tasks** — choose from 18 deployment tasks (all except Generate)
3. **Choose execution mode:**
   - **Deploy** (default) — applies reviewed artifacts (`rhoso_skip_generation=true`)
   - **Full / re-render** — regenerates then applies (`rhoso_skip_generation=false`)
4. **Click Install** — tasks execute sequentially with live SSE log streaming
5. **Validate** — Post-Deployment Validation runs CLI smoke tests

### Flags

| Flag | Deploy (default) | Full / re-render |
|------|------------------|------------------|
| `rhoso_apply_manifests` | `true` | `true` |
| `rhoso_skip_generation` | `true` | `false` |

### Recommended task order

1. Pre-requisites
2. Prerequisite Operator Installation
3. Generate OSP Secret
4. Generate Data Plane Secrets
5. Generate Ceph Secret (when Ceph External = yes)
6. Disconnected Environment Preparation (when disconnected)
7. Persistent Storage Configuration
8. Trident Storage Configuration (when Trident Enabled = yes)
9. Generate Storage CRs (when LSO/Trident/Multipath enabled)
10. OpenStack Operator Installation and Preparation
11. RHOCP Preparation for RHOSO
12. Network Preparation
13. Control Plane Deployment and Verification
14. Control Plane Customization
15. Data Plane Deployment and Verification
16. Post-Deployment Validation
17. Observability Configuration (when Observability Enabled = yes)

---

## RHOSO Installation Tasks

CPAT provides **19 installation tasks** (1 generate + 18 deploy) mapped to
Ansible task files via `backend/ansible_runner.py` (`RHOSO_INSTALLATION_TASK_TAGS`).

### Task summary

| # | UI Task | Ansible File | Conditional |
|---|---------|--------------|-------------|
| 0 | Generate Manifests for Review | `manifest_generation.yml` | Always |
| 1 | Pre-requisites | `prerequisites.yml` | Always |
| 2 | Verify Required CRDs | `_verify_required_crds.yml` | Always |
| 3 | Prerequisite Operator Installation | `prerequisite_operator_installation.yml` | Always |
| 4 | Disconnected Environment Preparation | `disconnected_environment_preparation.yml` | When disconnected |
| 5 | Generate OSP Secret | `generate_osp_secret.yml` | Always |
| 6 | Generate Data Plane Secrets | `generate_data_plane_secrets.yml` | Always |
| 7 | Generate Ceph Secret | `generate_ceph_secret.yml` | When Ceph External = yes |
| 8 | Persistent Storage Configuration | `persistent_storage_configuration.yml` | Always |
| 9 | Trident Storage Configuration | `trident_storage_configuration.yml` | When Trident Enabled = yes |
| 10 | Generate Storage CRs | `_generate_storage_crs.yml` | When LSO/Trident/Multipath |
| 11 | OpenStack Operator Installation and Preparation | `openstack_operator_installation_and_preparation.yml` | Always |
| 12 | RHOCP Preparation for RHOSO | `rhocp_preparation_for_rhoso.yml` | Always |
| 13 | Network Preparation | `network_preparation.yml` | Always |
| 14 | Control Plane Deployment and Verification | `control_plane_deployment_and_verification.yml` | Always |
| 15 | Control Plane Customization | `control_plane_customization.yml` | Always |
| 16 | Data Plane Deployment and Verification | `data_plane_deployment_and_verification.yml` | Always |
| 17 | Post-Deployment Validation | `post_deployment_validation.yml` | Always |
| 18 | Observability Configuration | `observability_configuration.yml` | When Observability Enabled = yes |

### Shared context (every task)

Before any task runs, `roles/rhoso/tasks/main.yml` includes `_load_ciq_context.yml`:

1. Confirms RHOSO environment in dynamic inventory
2. Loads CIQ parameters (~210 facts), `rhoso_networks`, `rhoso_data_plane_nodes`
3. Resolves deployment mode, namespaces, network names, EDPM flags, registries
4. Creates manifest directory under `<CPAT_DATA_DIR>/artifacts/<cluster>/`
5. Detects kubeconfig (`rhoso_can_apply` / `rhoso_can_query` gates)
6. Validates every CIQ field against the Python schema (`_validate_ciq.yml`)

---

### 0. Generate Manifests for Review (`manifest_generation.yml`)

Renders all reviewable CRs into `<CPAT_DATA_DIR>/artifacts/<cluster>/`.
Does **not** apply to the cluster. Does **not** require a reachable kubeconfig.

| Step | What it does |
|------|-------------|
| Assert generate-only | Fails if `rhoso_apply_manifests=true`. |
| Disconnected templates | When disconnected: includes `_generate_disconnected_crs.yml` (IDMS, ITMS, CatalogSource, OperatorHub disable). |
| Ceph secret | When Ceph External = yes: includes `generate_ceph_secret.yml`. |
| Network + control-plane CRs | Includes `_generate_control_plane_crs.yml` (NNCP, NAD, MetalLB, NetConfig, OpenStackControlPlane). |
| Data-plane CRs | Includes `_generate_data_plane_crs.yml` (EDPM Jinja, BMH, NodeSet, Deployment). |
| Storage CRs | When LSO/Trident/Multipath enabled: includes `_generate_storage_crs.yml` (LSO, Trident, Multipath). |
| List files | Summary of rendered files for UI review. |

### 1. Pre-requisites (`prerequisites.yml`)

Pre-flight checks before any deployment work.

| Step | What it does |
|------|-------------|
| Document required inputs | Logs required CIQ inputs. |
| Assert core CIQ parameters | Fails if kubeconfig, storage class, namespaces, pull secret, networks, or mgmt/internal-API names are empty. |
| Kubeconfig / pull secret files | `stat` on paths; assert files exist. |
| `oc whoami` | Confirms cluster-admin access. |
| Cluster API reachable | Verifies RHOCP API responds. |
| StorageClass exists | `oc get storageclass` for CIQ Storage Class. |
| Disconnected inputs | When disconnected, asserts mirror registry / catalog fields present. |
| Summary | Pass/fail summary. |

### 2. Verify Required CRDs (`_verify_required_crds.yml`)

Checks that all required CRDs exist on the RHOCP cluster before applying CRs.
Verifies control plane, data plane, prerequisites, and unprovisioned CRDs.

### 3. Prerequisite Operator Installation (`prerequisite_operator_installation.yml`)

Installs required RHOCP operators via OLM Subscriptions. Each operator follows:
Namespace → OperatorGroup → Subscription → Approve InstallPlan → Wait CSV Succeeded.

| Operator | Namespace | Conditional |
|----------|-----------|-------------|
| NMState | `openshift-nmstate` | Always |
| MetalLB | `metallb-system` | Always |
| Cert-Manager | `cert-manager-operator` | Always |
| Node Health Check | `openshift-operators` | When NHC Enabled = yes |
| Self Node Remediation | `openshift-operators` | When SNR Enabled = yes |
| Fence Agents Remediation | `openshift-operators` | When FAR Enabled = yes |
| Local Storage Operator | `openshift-local-storage` | When LSO Enabled = yes |
| Cluster Observability Operator | `openshift-cluster-observability-operator` | When Observability Enabled = yes |

### 4. Disconnected Environment Preparation (`disconnected_environment_preparation.yml`)

Reference: *Deploying RHOSO in a disconnected environment*.

- **Connected mode:** logs skip and exits.
- **Disconnected mode:**

| Step | What it does |
|------|-------------|
| Validate CIQ | Requires Mirror Registry URL, pull secret, CatalogSource image/name. |
| Generate (or assert reviewed) | Renders or verifies disconnected CRs. |
| Mirror CA | ConfigMap + patches `image.config.openshift.io/cluster`. |
| Merge pull secret | Merges mirror auths into `openshift-config/pull-secret`. |
| Apply mirrors | IDMS, ITMS, OperatorHub disable, CatalogSource. |
| Wait CatalogSource READY | Polls until mirrored CatalogSource is ready. |

### 5. Generate OSP Secret (`generate_osp_secret.yml`)

Generates the `osp-secret` Opaque Secret CR with 19 service passwords
(Admin, Galera root/password, RabbitMQ, Glance, Cinder, Neutron, Nova, Heat,
Barbican, Octavia, Designate, Ironic, Manila, Watcher, Placement, Aodh, Swift,
and Fernet key).

### 6. Generate Data Plane Secrets (`generate_data_plane_secrets.yml`)

Generates 5 data plane secrets:
- Ansible SSH private key secret
- Nova migration SSH key secret
- Subscription manager secret
- Registry pull secret (optional)
- Libvirt secret

### 7. Generate Ceph Secret (`generate_ceph_secret.yml`)

When `Ceph External = yes`, generates `ceph-conf-files` Kubernetes Secret:
- `<cluster>.conf` with `[global]` section (fsid, mon_host)
- `<cluster>.client.<name>.keyring` from uploaded keyring
- Both base64-encoded in Secret `data`
- Consumed by Glance, Cinder, Nova, Swift via `extraMounts`

### 8. Persistent Storage Configuration (`persistent_storage_configuration.yml`)

| Step | What it does |
|------|-------------|
| Require Storage Class | Asserts CIQ `Storage Class` is set. |
| Verify StorageClass | `oc get storageclass` for that name. |
| Default annotation | Checks default StorageClass marking. |
| List PVCs | Lists existing PVCs in openstack namespace. |
| LSO (v1.4) | When LSO Enabled: applies `LocalVolumeDiscovery` + `LocalVolumeSet` CRs. |
| Summary | Notes backend guidance and next steps. |

### 9. Trident Storage Configuration (`trident_storage_configuration.yml`) — NEW v1.4

Installs NetApp Trident CSI storage operator and configures backend + StorageClass.
Runs only when `Trident Enabled = yes` in CIQ.

| Step | What it does |
|------|-------------|
| Validate parameters | Asserts driver, management LIF, and SVM are set. |
| Generate manifests | Renders `openstack_trident.yaml` from template. |
| Create namespace | `oc apply` Trident namespace. |
| Apply manifests | Applies TridentOrchestrator + TridentBackendConfig + StorageClass + Secret. |
| Wait Installed | Polls TridentOrchestrator until status = Installed (600s timeout). |
| Verify StorageClass | `oc get storageclass` for Trident class. |

### 10. Generate Storage CRs (`_generate_storage_crs.yml`) — NEW v1.4

Sub-task that renders storage-related templates when storage features are enabled:
- LSO manifests: Namespace + OperatorGroup + Subscription + LocalVolumeDiscovery + LocalVolumeSet
- Trident manifests: TridentOrchestrator + TridentBackendConfig + StorageClass + Secret
- Multipath manifests: ConfigMap/Secret with multipath.conf

### 11. OpenStack Operator Installation and Preparation (`openstack_operator_installation_and_preparation.yml`)

| Step | What it does |
|------|-------------|
| Disconnected guards | Asserts CatalogSource / Operator Source. |
| Create operators namespace | Applies `openstack-operators` namespace. |
| Create OperatorGroup | Applies OperatorGroup. |
| Create Subscription | Subscribes with Manual/Automatic approval. |
| Approve InstallPlan | Approves pending InstallPlan. |
| Create OpenStack init CR | Applies `OpenStack` initialization CR. |
| Verify CSV | Waits for CSV Succeeded. |

### 12. RHOCP Preparation for RHOSO (`rhocp_preparation_for_rhoso.yml`)

| Step | What it does |
|------|-------------|
| Create OpenStack namespace | Applies namespace with privileged pod-security labels. |
| Verify privileged labels | Asserts `pod-security.kubernetes.io/enforce=privileged`. |
| Generate osp-secret | Creates Opaque Secret with service passwords. |
| Verify Secret | Confirms osp-secret exists. |

### 13. Network Preparation (`network_preparation.yml`)

| Step | What it does |
|------|-------------|
| Verify network CRDs | NMState, NAD, MetalLB, NetConfig CRDs. |
| Generate (or assert reviewed) | Renders or verifies network CRs. |
| Apply network CRs | NNCP, NAD, MetalLB IPAddressPool + L2Advertisement, NetConfig. |
| OVN IP forwarding | Enables global IP forwarding when needed. |
| Verify resources | Lists applied network resources. |

### 14. Control Plane Deployment and Verification (`control_plane_deployment_and_verification.yml`)

| Step | What it does |
|------|-------------|
| Verify CRDs | Control plane CRDs exist. |
| Generate (or assert reviewed) | Renders or verifies CRs. |
| Prerequisites | Storage Class, NetworkPolicies, Operator CSV, NetConfig, osp-secret. |
| Apply supporting CRs | NNCP / NAD / MetalLB / NetConfig if not applied. |
| Apply OpenStackControlPlane | `oc apply` of control plane CR. |
| Wait Setup complete | Waits for Ready conditions. |
| Verify | Lists pods; asserts openstackclient pod exists. |

### 15. Control Plane Customization (`control_plane_customization.yml`)

| Step | What it does |
|------|-------------|
| Require existing CR | Asserts OpenStackControlPlane exists. |
| Export current CR | Dumps live CR for review. |
| Patch guidance | Writes guidance file (cells, topologies, volumes, etc.). |
| Optional re-apply | Waits for Ready if CR re-applied. |

### 16. Data Plane Deployment and Verification (`data_plane_deployment_and_verification.yml`)

| Step | What it does |
|------|-------------|
| Verify CRDs | NodeSet / Deployment / BMH CRDs. |
| Generate (or assert reviewed) | Renders or verifies CRs. |
| Prerequisites | SSH key, subscription inputs, control plane Ready. |
| Secrets | Creates 5 DP secrets (SSH, migration, subscription, registry, libvirt). |
| NodeSet | Validates provisioning mode; applies BMH (unprovisioned); applies NodeSet; waits SetupReady. |
| Deployment | Removes failed prior Deployments; applies Deployment; waits Ready. |

### 17. Post-Deployment Validation (`post_deployment_validation.yml`)

| Step | What it does |
|------|-------------|
| ControlPlane Ready | Asserts control plane Ready condition. |
| NodeSet Ready | Asserts NodeSet Ready. |
| Deployment Ready | Asserts Deployment Ready. |
| Failing / pending pods | Lists unhealthy pods. |
| OpenStack CLI smoke | Runs basic `openstack` commands via openstackclient pod. |
| Summary report | Overall health summary. |

### 18. Observability Configuration (`observability_configuration.yml`) — NEW v1.4

Configures Cluster Observability Operator after installation. Runs only when
`Observability Enabled = yes` in CIQ.

| Step | What it does |
|------|-------------|
| Verify CSV | Waits for Cluster Observability Operator CSV Succeeded. |
| Create MonitoringStack | Applies MonitoringStack CR (Prometheus, Alertmanager, retention). |
| Wait Ready | Polls MonitoringStack Available condition (600s timeout). |
| List resources | Shows MonitoringStack and Prometheus pods. |

---

## OCP Installation Tasks

CPAT provides **22 OCP installation tasks** (1 generate + 21 deploy) mapped to
Ansible task files via `backend/ansible_runner.py` (`OCP_INSTALLATION_TASK_TAGS`).

### Supported installation methods

| Method | Description |
|--------|-------------|
| ABI | Agent-based Installer — boots nodes from agent ISO |
| IPI-BM | Installer-Provisioned Infrastructure — Bare Metal with BMC |
| UPI-BM | User-Provisioned Infrastructure — Bare Metal with ignition |
| ABI-DC | Agent-based Installer — Disconnected with mirror registry |
| SNO | Single Node OpenShift — single-node ABI |

### OCP task summary

| # | UI Task | Ansible Task Tag | Conditional |
|---|---------|-----------------|-------------|
| 0 | OCP Generate Manifests | `generate_manifests` | Always |
| 1 | OCP Bastion Preparation | `bastion_preparation` | Always |
| 2 | OCP DNS DHCP Validation | `dns_dhcp_validation` | Always |
| 3 | OCP NTP Sync | `ntp_sync` | Always |
| 4 | OCP Mirror Registry Install | `mirror_registry` | When disconnected |
| 5 | OCP OC Mirror Execution | `oc_mirror` | When disconnected |
| 6 | OCP IDMS ITMS Configuration | `idms_itms_config` | When disconnected |
| 7 | OCP Generate Install Config | `install_config` | Always |
| 8 | OCP Generate Agent Config | `agent_config` | When ABI/ABI-DC |
| 9 | OCP Generate NMState Configs | `nmstate_configs` | When NMState interfaces defined |
| 10 | OCP Generate Ignition Configs | `ignition_configs` | When UPI |
| 11 | OCP Create Agent ISO | `agent_iso` | When ABI/ABI-DC |
| 12 | OCP Bootstrap Cluster | `bootstrap` | Always |
| 13 | OCP Wait Install Complete | `wait_install` | Always |
| 14 | OCP Approve CSRs | `approve_csrs` | Always |
| 15 | OCP Configure Authentication | `auth_config` | Always |
| 16 | OCP Day-2 Operator Installation | `day2_operators` | Always |
| 17 | OCP MetalLB Configuration | `metallb_config` | When MetalLB enabled |
| 18 | OCP SR-IOV Multus Configuration | `sriov_config` | When SR-IOV/Multus enabled |
| 19 | OCP Cluster Health Check | `health_check` | Always |
| 20 | OCP Node Readiness Check | `node_readiness` | Always |
| 21 | OCP Full Install | `full_install` | All steps sequentially |

### OCP shared context

Before any OCP task runs, `roles/ocp/tasks/main.yml` includes `common/_load_ciq_context.yml`:

1. Loads CIQ parameters from inventory
2. Resolves install method flags (`ocp_is_abi`, `ocp_is_ipi`, `ocp_is_upi`, `ocp_is_sno`)
3. Resolves disconnected flag (`ocp_is_disconnected`)
4. Creates install/manifest directories
5. Validates CIQ fields per install method (`common/_validate_ciq.yml`)

### OCP Ansible role directory structure

```
roles/ocp/
├── defaults/main.yml          ~170 default variables
├── meta/main.yml              Galaxy metadata
├── vars/main.yml              Internal variables (paths, derived flags)
├── tasks/
│   ├── main.yml               Entry point: CIQ load + task routing
│   ├── common/                _load_ciq_context, _validate_ciq, _verify_prerequisites
│   ├── prerequisites/         bastion_preparation, dns_dhcp_validation, ntp_sync
│   ├── mirror/                mirror_registry_install, oc_mirror_execution, idms_itms_configuration
│   ├── install_config/        generate_install_config, generate_agent_config, generate_nmstate_configs
│   ├── ignition/              generate_ignition_configs, create_agent_iso
│   ├── bootstrap/             bootstrap_cluster, wait_bootstrap_complete
│   ├── cluster_config/        approve_csrs, configure_authentication, day2_operator_installation
│   ├── network/               metallb_configuration, sriov_multus_configuration
│   ├── validation/            cluster_health_check, node_readiness_check
│   └── manifests/             manifest_generation, _generate_disconnected_crs
└── templates/                 12 Jinja2 templates
```

### Manual OCP installation (single task)

```bash
ansible-playbook ansible/playbooks/ocp_install.yml \
  -e '{"ocp_cluster_name":"lab-ocp","ocp_version":"4.19","ocp_task":"install_config"}'
```

Valid `ocp_task` values: `full_install`, `generate_manifests`, `bastion_preparation`,
`dns_dhcp_validation`, `ntp_sync`, `mirror_registry`, `oc_mirror`, `idms_itms_config`,
`install_config`, `agent_config`, `nmstate_configs`, `ignition_configs`, `agent_iso`,
`bootstrap`, `wait_install`, `approve_csrs`, `auth_config`, `day2_operators`,
`metallb_config`, `sriov_config`, `health_check`, `node_readiness`.

---

## OCP CIQ Parameter Reference

CPAT parses **18 OCP CIQ tables** with **~175 parameters** from the OCP CIQ workbook.

### OCP CIQ tables

| # | Table Name | Parameters | Description |
|---|------------|-----------|-------------|
| 1 | `ocp_details` | ~22 | Cluster identity, version, install method |
| 2 | `ocp_networking` | ~12 | Network CIDRs, network type, IP families |
| 3 | `ocp_platform_baremetal` | ~12 | IPI bare metal VIPs, provisioning network |
| 4 | `ocp_agent_config` | ~12 | ABI rendezvous IP, NTP, agent counts |
| 5 | `ocp_disconnected` | ~14 | Mirror registry, IDMS, CatalogSource |
| 6 | `ocp_mirror_registry` | ~10 | Quay mirror-registry settings |
| 7 | `ocp_bastion` | ~10 | Bastion host details |
| 8 | `ocp_load_balancer` | ~8 | HAProxy / LB config (platform=none) |
| 9 | `ocp_certificates` | ~7 | API/Ingress certificates |
| 10 | `ocp_storage` | ~8 | Default storage class, NFS, LSO, ODF |
| 11 | `ocp_day2_operators` | ~12 | Day-2 operator toggles |
| 12 | `ocp_ingress` | ~6 | Ingress controller settings |
| 13 | `ocp_proxy` | ~5 | HTTP/HTTPS proxy config |
| 14 | `ocp_bmc_hosts` | 14 cols | BMC host definitions (row table) |
| 15 | `ocp_nmstate_interfaces` | 12 cols | NMState interface configs (row table) |
| 16 | `ocp_compute_nodes` | 14 cols | Compute node details (row table) |
| 17 | `ocp_dns_records` | 8 cols | DNS record definitions (row table) |

---

## OCP Manifest Catalog

CPAT generates **12 OCP manifest templates** covering all OCP installation methods.

| # | Template | Generates | Conditional |
|---|----------|-----------|-------------|
| 1 | `ocp_install_config.yaml.j2` | `install-config.yaml` (IPI/UPI/ABI) | Always |
| 2 | `ocp_sno_install_config.yaml.j2` | `install-config.yaml` (SNO) | When SNO |
| 3 | `ocp_agent_config.yaml.j2` | `agent-config.yaml` | When ABI/ABI-DC |
| 4 | `ocp_nmstate_config.yaml.j2` | Per-host NMState YAML | When NMState interfaces |
| 5 | `ocp_platform_baremetal.yaml.j2` | Bare metal platform snippet | When IPI/ABI |
| 6 | `ocp_image_content_source.yaml.j2` | ImageDigestMirrorSet CR | When disconnected |
| 7 | `ocp_catalog_source.yaml.j2` | CatalogSource CR | When disconnected |
| 8 | `ocp_chrony_config.j2` | chrony.conf | Always |
| 9 | `ocp_haproxy_config.j2` | HAProxy LB config | When platform=none |
| 10 | `ocp_dns_records.j2` | BIND zone file | When DNS records |
| 11 | `ocp_day2_operator_sub.yaml.j2` | Operator Subscription CRs | When day-2 operators |
| 12 | `ocp_mirror_imageset.yaml.j2` | oc-mirror ImageSetConfiguration | When disconnected |

---

## OCP Input Files Reference

| Field | CIQ Parameter | Stored As | Required |
|-------|--------------|-----------|----------|
| `ocp_pull_secret` | Pull Secret Path | `pull-secret.json` | Yes |
| `ocp_ssh_public_key` | SSH Public Key Path | `ssh-public-key` | Yes |
| `ocp_mirror_pull_secret` | Mirror Pull Secret Path | `mirror-pull-secret.json` | When disconnected |
| `ocp_mirror_ca` | Mirror Registry CA Path | `mirror-ca.crt` | When disconnected |

---

## Input Files Reference

Files uploaded via the CPAT UI (Register or Dashboard → Input Files). Each maps
to a CIQ parameter that references a filesystem path.

| Field | CIQ Parameter | Stored As | Required |
|-------|--------------|-----------|----------|
| `kubeconfig` | Kubeconfig Path | `kubeconfig` | Recommended |
| `pull_secret` | Pull Secret Path | `pull-secret.json` | Recommended |
| `mirror_pull_secret` | Mirror Pull Secret Path | `mirror-pull-secret.json` | When disconnected |
| `mirror_ca` | Mirror Registry CA Path | `mirror-ca.crt` | When disconnected + CA |
| `dataplane_ssh_key` | Data Plane SSH Private Key Path | `dataplane-ssh-key` | Recommended |
| `netapp_config` | Trident Secret Name | `netapp-config.json` | When Trident Enabled = yes |
| `multipath_config` | Multipath Config Secret Name | `multipath-config.conf` | When Multipath Enabled = yes |
| `ceph_keyring` | Ceph Client Key Path | `ceph-keyring` | When Ceph External = yes |

Uploaded files are stored under `<CPAT_DATA_DIR>/secrets/<cluster-id>/` with `0600`
permissions. Path CIQ parameters are automatically overridden to point to stored
locations during Ansible execution.

---

## CIQ Parameter Reference

CPAT parses **18 CIQ tables** with **203 parameters** from the RHOSO CIQ workbook.
Tables are identified by bold uppercase merged-cell headers in the Excel sheet.

### 1. RHOSO Details

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Cluster Name` | `rhoso-cloud-01` | Unique RHOSO environment name for registration and inventory. |
| `Type` | `RHOSO` | Must be RHOSO (identifies this CIQ as a RHOSO registration). |
| `Environment` | `lab` | Deployment lifecycle label (`lab`, `test`, `staging`, `prod`, `development`). |
| `RHOSO Version` | `18.0` | Red Hat OpenStack Services on OpenShift product version. |
| `RHOCP Version` | `4.16` | Underlying Red Hat OpenShift Container Platform version. |
| `Deployment Mode` | `connected` | `connected` \| `disconnected` \| `airgapped` \| `offline`. |
| `Multi Environment on Single RHOCP` | `no` | Multiple RHOSO envs on one RHOCP (unique namespaces). |
| `OpenStack Namespace` | `openstack` | Namespace for OpenStack control-plane services. |
| `OpenStack Operators Namespace` | `openstack-operators` | Namespace for the OpenStack Operator. |
| `Description` | *(notes)* | Free-text notes. |

### 2. RHOSO Access

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Kubeconfig Path` | `/opt/cpat/kubeconfigs/rhocp.kubeconfig` | Absolute path to RHOCP cluster-admin kubeconfig. |
| `RHOCP API URL` | `https://api.ocp.example.com:6443` | Optional RHOCP API endpoint URL. |
| `Pull Secret Path` | `/opt/cpat/secrets/pull-secret.json` | Absolute path to registry pull-secret JSON. |

### 3. RHOSO Disconnected

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Mirror Registry URL` | `mirror.example.com:8443` | Disconnected mirror registry host[:port]. |
| `Mirror Registry CA Path` | `/opt/cpat/certs/mirror-ca.crt` | CA certificate for mirror registry. |
| `Mirror Pull Secret Path` | `/opt/cpat/secrets/mirror-pull-secret.json` | Mirror auth secret (falls back to Pull Secret Path). |
| `ImageDigestMirrorSet Name` | `rhoso-idms` | ImageDigestMirrorSet CR name. |
| `ImageTagMirrorSet Name` | `rhoso-itms` | ImageTagMirrorSet CR name. |
| `ImageContentSourcePolicy Name` | *(optional)* | Legacy ICSP name (prefer IDMS/ITMS). |
| `Disable Default CatalogSources` | `no` | Disable default OperatorHub sources. |
| `CatalogSource Name` | `redhat-operators` | Mirrored CatalogSource CR name. |
| `CatalogSource Namespace` | `openshift-marketplace` | CatalogSource namespace. |
| `CatalogSource Image` | `mirror…/redhat-operator-index:v4.16` | Mirrored operator-index image. |
| `Operator Source` | `redhat-operators` | OLM Subscription `spec.source`. |
| `Operator Source Namespace` | `openshift-marketplace` | OLM Subscription `sourceNamespace`. |
| `Mirrored Registry OpenStack Path` | `rh-osbs/rhosp18` | Mirror path for RHOSO images. |
| `Data Plane Container Registry` | `mirror…/rh-osbs/rhosp18` | Optional EDPM container registry override. |
| `Data Plane YUM Mirror URL` | `https://satellite…/pulp/content` | Optional YUM/DNF mirror. |
| `Satellite Capsule URL` | `https://satellite.example.com` | Optional Satellite Capsule URL. |

### 4. RHOSO Storage

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Storage Class` | `ocs-storagecluster-ceph-rbd` | RHOCP StorageClass for PVCs. |
| `Storage Backend` | `Red Hat OpenShift Data Foundation` | Storage solution (ODF, NFS, Ceph, LSO, External). |

### 5. RHOSO Ceph Storage

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Ceph External` | `yes` | Enable external Ceph integration. |
| `Ceph Cluster Name` | `ceph` | Ceph cluster name. |
| `Ceph FSID` | `a1b2c3d4-…` | Ceph cluster FSID. |
| `Ceph Mon Host` | `10.0.0.10,10.0.0.11,10.0.0.12` | Ceph monitor host addresses. |
| `Ceph Client Name` | `openstack` | Ceph client name. |
| `Ceph Client Key Path` | `/opt/cpat/secrets/ceph-keyring` | Path to Ceph client keyring file. |
| `Ceph Pool Volumes` | `volumes` | RBD pool for Cinder volumes. |
| `Ceph Pool Images` | `images` | RBD pool for Glance images. |
| `Ceph Pool VMs` | `vms` | RBD pool for Nova ephemeral disks. |
| `Ceph RGW Enabled` | `no` | Enable Swift via Ceph RADOS Gateway. |
| `Ceph RGW Endpoint` | `http://10.0.0.50:8080` | Ceph RGW endpoint URL. |
| `Ceph RGW TLS Enabled` | `no` | Enable TLS for RGW endpoint. |

### 6. RHOSO Control Plane

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Control Plane CR Name` | `openstack-control-plane` | OpenStackControlPlane CR name. |
| `Control Plane FQDN` | `openstack.apps.ocp.example.com` | Public FQDN for control plane API. |
| `Public VIP` | `10.20.30.40` | Public VIP for control plane endpoint. |
| `OSP Secret Name` | `osp-secret` | Secret holding service passwords. |
| `Management Network Name` | `ctlplane` | Control-plane network name. |
| `Internal API Network Name` | `internalapi` | Internal API network / MetalLB pool name. |
| `MetalLB Namespace` | `metallb-system` | Namespace for MetalLB. |
| `NAD CNI Version` | `0.3.1` | CNI version in NAD configs. |
| `Internal API VIP` | `172.17.0.80` | VIP on Internal API network. |
| `Cell1 RabbitMQ VIP` | `172.17.0.86` | VIP for Nova cell1 RabbitMQ. |
| `RabbitMQ VIP` | `172.17.0.85` | VIP for RabbitMQ. |
| `Glance Internal VIP` | `172.17.0.80` | Glance VIP on Internal API. |
| `Cinder Internal VIP` | `172.17.0.80` | Cinder VIP on Internal API. |
| `Neutron Internal VIP` | `172.17.0.80` | Neutron VIP on Internal API. |
| `Nova Internal VIP` | `172.17.0.80` | Nova VIP on Internal API. |
| `Placement Internal VIP` | `172.17.0.80` | Placement VIP on Internal API. |
| `Datacentre NIC` | `ospbr` | Datacentre / provider NIC name. |
| `Public Interface` | `eth0` | Public interface name. |
| `Worker NNCP Interface` | `enp6s0` | Worker NIC for NNCP. |
| `OVN Gateway Placement` | `control-plane` | `control-plane` \| `data-plane` \| `networker`. |
| `TLS Pod Level Enabled` | `no` | Enable TLS at pod level. |
| `Operator Channel` | `stable-v1.0` | OLM Subscription channel. |
| `DNS VIP` | `172.17.0.82` | VIP for DNS service. |
| `DNS Upstream Servers` | `8.8.8.8,8.8.4.4` | Upstream DNS servers. |
| `Worker DNS Servers` | `172.30.0.10` | DNS servers for worker nodes. |
| `Messaging Bus Cluster` | `rabbitmq` | Global messageBus cluster name. |
| `Notifications Bus Cluster` | `rabbitmq` | Global notificationsBus cluster name. |
| `FIPS Enabled` | `no` | Enable FIPS compliance mode. |

### 7. RHOSO EDPM Network Config

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Physical Bridge Name` | `br-ex` | OVS bridge name on data plane nodes. |
| `EDPM Network Config Topology` | `dual_nic_bond` | `single_nic_vlans` \| `dual_nic_bond` \| `ovs_bond` \| `linux_bond` \| `ovs_dpdk`. |
| `EDPM Network Config Nmstate` | `yes` | Use nmstate provider for os-net-config. |
| `EDPM Network Config Update` | `no` | Allow network_config updates on existing nodes. |
| `EDPM Bridge Type` | `ovs_bridge` | `ovs_bridge` \| `ovs_user_bridge`. |
| `EDPM NIC1 Name` | `nic1` | First NIC alias. |
| `EDPM NIC2 Name` | `nic2` | Second NIC alias (bonded topologies). |
| `EDPM Bond Name` | `bond0` | Bond device name (bonded topologies). |
| `EDPM Bonding Options` | `mode=802.3ad lacp_rate=fast …` | Linux bonding_options string. |
| `EDPM Use DHCP` | `no` | DHCP on ctlplane/bond. |
| `EDPM Use DHCPv6` | `no` | DHCPv6 on ctlplane/bond. |
| `EDPM DPDK MTU` | `9000` | MTU for DPDK interfaces. |
| `EDPM DPDK RX Queue` | `1` | RX queue count for DPDK ports. |
| `EDPM DPDK OVS Extra` | `set port bond0 bond_mode=balance-slb` | Extra OVS args for DPDK bonds. |
| `NTP Servers` | `clock.redhat.com,…` | Comma-separated NTP servers. |
| `Registry Secret Name` | *(optional)* | Secret for private registry on nodes. |

### 8. RHOSO Data Plane

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Data Plane NodeSet Name` | `openstack-data-plane` | OpenStackDataPlaneNodeSet CR name. |
| `Data Plane Deployment Name` | `data-plane-deploy` | OpenStackDataPlaneDeployment CR name. |
| `Data Plane Provisioning Mode` | `pre-provisioned` | `pre-provisioned` \| `unprovisioned`. |
| `Data Plane SSH User` | `cloud-admin` | SSH user for EDPM Ansible. |
| `Data Plane SSH Private Key Path` | `/opt/cpat/keys/…` | Path to SSH private key. |
| `Data Plane Ansible EE Image` | *(optional)* | Override Ansible EE image. |
| `Ansible SSH Secret Name` | `dataplane-ansible-ssh-private-key-secret` | Ansible SSH Secret name. |
| `Nova Migration Secret Name` | `nova-migration-ssh-key` | Nova migration Secret name. |
| `Subscription Secret Name` | `subscription-manager` | Subscription manager Secret name. |
| `Libvirt Secret Name` | `libvirt-secret` | Libvirt Secret name. |
| `Subscription Method` | `activation_key` | `activation_key` \| `username_password`. |
| `Red Hat Organization ID` | `12345678` | Org ID for activation_key method. |
| `Red Hat Activation Key` | `rhoso-dataplane` | Activation key. |
| `Red Hat Username` | *(optional)* | Username for username_password method. |

### 9. RHOSO Services

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Horizon Enabled` | `no` | Enable Horizon dashboard. |
| `Heat Enabled` | `yes` | Enable Heat orchestration. |
| `Telemetry Enabled` | `no` | Enable Ceilometer/Prometheus telemetry. |
| `Barbican Enabled` | `no` | Enable Barbican key manager. |
| `Octavia Enabled` | `no` | Enable Octavia load balancer. |
| `Designate Enabled` | `no` | Enable Designate DNS. |
| `Ironic Enabled` | `no` | Enable Ironic bare metal provisioning. |
| `Manila Enabled` | `no` | Enable Manila shared file systems. |
| `Watcher Enabled` | `no` | Enable Watcher resource optimization. |
| `Glance Backend` | `PVC` | Glance storage: `PVC`, `Cinder`, or `S3`. |
| `Glance Replicas` | `1` | Glance API replicas. |
| `Nova API Replicas` | `1` | Nova API replicas. |
| `Nova Scheduler Replicas` | `1` | Nova scheduler replicas. |
| `Nova Conductor Cell0 Replicas` | `1` | Cell0 conductor replicas. |
| `Nova Conductor Cell1 Replicas` | `1` | Cell1 conductor replicas. |
| `Nova Metadata Enabled` | `yes` | Enable Nova metadata service. |
| `Nova Cell1 Metadata Replicas` | `1` | Cell1 metadata replicas. |
| `Nova Cell1 noVNC Replicas` | `1` | Cell1 noVNC proxy replicas. |
| `Neutron Replicas` | `1` | Neutron API replicas. |
| `Keystone Replicas` | `1` | Keystone API replicas. |
| `Cinder API Replicas` | `1` | Cinder API replicas. |
| `Cinder Scheduler Replicas` | `1` | Cinder scheduler replicas. |
| `Barbican API Replicas` | `1` | Barbican API replicas. |
| `Barbican Worker Replicas` | `1` | Barbican worker replicas. |
| `Placement Replicas` | `1` | Placement API replicas. |
| `Horizon Replicas` | `1` | Horizon replicas. |
| `Heat API Replicas` | `1` | Heat API replicas. |
| `Heat Engine Replicas` | `1` | Heat engine replicas. |
| `Memcached Replicas` | `1` | Memcached replicas. |
| `Galera Replicas` | `1` | Galera (MariaDB) replicas. |
| `Galera Cell1 Replicas` | `1` | Galera cell1 replicas. |
| `RabbitMQ Replicas` | `3` | RabbitMQ replicas. |
| `RabbitMQ Cell1 Replicas` | `3` | RabbitMQ cell1 replicas. |
| `DNS Replicas` | `1` | Designate DNS replicas. |
| `OVN NB Replicas` | `3` | OVN Northbound DB replicas. |
| `OVN SB Replicas` | `3` | OVN Southbound DB replicas. |

### 10. RHOSO PV Sizing

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Galera Storage Request` | `5G` | PVC size for Galera database. |
| `Galera Cell1 Storage Request` | `5G` | PVC size for cell1 Galera. |
| `OVN NB Storage Request` | `10G` | PVC size for OVN Northbound DB. |
| `OVN SB Storage Request` | `10G` | PVC size for OVN Southbound DB. |
| `Telemetry Storage Request` | `20G` | PVC size for telemetry data. |
| `Telemetry Storage Class` | *(optional)* | StorageClass override for telemetry. |
| `Telemetry Retention` | `24h` | Data retention period. |
| `Telemetry Scrape Interval` | `30s` | Prometheus scrape interval. |
| `RabbitMQ CPU Limit` | `500m` | CPU limit for RabbitMQ pods. |
| `RabbitMQ Memory Limit` | `1Gi` | Memory limit for RabbitMQ pods. |

### 11. RHOSO Cinder Backend

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Cinder Default Volume Type` | `netapp` | Default volume type. |
| `Cinder Volume Backend Name` | `netapp-backend` | Backend name in cinder.conf. |
| `Cinder Volume Driver` | `cinder.volume.drivers.netapp…` | Python driver class. |
| `Cinder Storage Protocol` | `iSCSI` | `FC`, `iSCSI`, or `NFS`. |
| `Cinder NetApp Server Hostname` | `10.0.0.100` | NetApp management IP. |
| `Cinder NetApp Vserver` | `svm01` | NetApp SVM name. |
| `Cinder Volume Secret Name` | `cinder-netapp-secret` | K8s Secret for backend credentials. |
| `Cinder Volume Network Attachments` | `storage` | NADs for storage network access. |

### 12. RHOSO Neutron Config

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Neutron Global Physnet MTU` | `1500` | Global physical network MTU. |
| `Neutron Physical Network MTUs` | `datacentre:1500,tenant:1400` | Per-physnet MTU overrides. |
| `Neutron API Timeout` | `60` | API request timeout in seconds. |
| `OVN Emit Need To Frag` | `yes` | Enable OVN "fragmentation needed" ICMP. |
| `MAC Binding Age Threshold` | `0` | OVN MAC binding age threshold (RHOSO 18.0 workaround). |

### 13. RHOSO HA Operators

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Node Health Check Operator Enabled` | `no` | Enable Node Health Check Operator. |
| `Self Node Remediation Operator Enabled` | `no` | Enable Self Node Remediation Operator. |
| `Fence Agents Remediation Operator Enabled` | `no` | Enable Fence Agents Remediation Operator. |

### 14. RHOSO Trident Storage — NEW v1.4

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Trident Enabled` | `no` | Enable NetApp Trident CSI storage. |
| `Trident Image Registry` | `mirror.example.com:5000/trident` | Trident image registry (disconnected). |
| `Trident Image` | `trident:24.06.0` | Trident operator image. |
| `Trident Autosupport Image` | `trident-autosupport:24.06.0` | Trident autosupport image. |
| `Trident Backend Name` | `ontap-backend` | TridentBackendConfig name. |
| `Trident Storage Driver Name` | `ontap-san` | ONTAP driver: `ontap-san` \| `ontap-nas`. |
| `Trident Management LIF` | `10.0.0.100` | ONTAP management LIF IP. |
| `Trident Data LIF` | `10.0.0.101` | ONTAP data LIF IP. |
| `Trident SVM` | `svm-trident` | ONTAP Storage Virtual Machine. |
| `Trident Secret Name` | `backend-ontap-secret` | K8s Secret for ONTAP credentials. |
| `Trident Storage Class Name` | `ontap-gold` | StorageClass name for Trident. |
| `Trident Volume Binding Mode` | `Immediate` | StorageClass volumeBindingMode. |

### 15. RHOSO LSO Storage — NEW v1.4

| Parameter | Example | Description |
|-----------|---------|-------------|
| `LSO Enabled` | `no` | Enable Local Storage Operator. |
| `LSO Storage Class Name` | `local-storage` | StorageClass name for local volumes. |
| `LSO Device Types` | `disk` | Comma-separated device types (disk, part). |
| `LSO Device Mechanical Properties` | `NonRotational` | Device type filter (NonRotational, Rotational). |
| `LSO Min Device Size` | `100Gi` | Minimum device size for LocalVolumeSet. |
| `LSO Volume Mode` | `Block` | Volume mode: `Block` \| `Filesystem`. |
| `LSO Node Selector Label` | `cluster.ocs.openshift.io/openshift-storage` | Node selector label for LSO. |

### 16. RHOSO Observability — NEW v1.4

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Observability Enabled` | `no` | Enable Cluster Observability Operator. |
| `Observability Operator Channel` | `stable` | OLM Subscription channel. |
| `Observability Install Plan Approval` | `Automatic` | InstallPlan approval strategy. |
| `Observability Monitoring Stack Enabled` | `no` | Create MonitoringStack CR after operator install. |
| `Observability Monitoring Stack Name` | `rhoso-monitoring` | MonitoringStack CR name. |

### 17. RHOSO Multipath — NEW v1.4

| Parameter | Example | Description |
|-----------|---------|-------------|
| `Multipath Enabled` | `no` | Enable multipath configuration. |
| `Multipath Config Secret Name` | `multipath-config` | Secret/ConfigMap name for multipath.conf. |
| `Multipath User Friendly Names` | `yes` | Use user-friendly device names. |
| `Multipath Find Multipaths` | `yes` | Auto-detect multipath devices. |

### 18. RHOSO Networks (row table)

Feeds NetConfig, NAD, MetalLB pools, and NNCP. Include RHOSO networks as needed.

| Column | Description |
|--------|-------------|
| `Network Name` | Logical network name (e.g. `ctlplane`, `internalapi`, `storage`). |
| `CIDR` | IPv4 CIDR for the subnet. |
| `VLAN` | Optional VLAN ID (1–4094). |
| `Gateway` | Optional default gateway IP. |
| `MTU` | Maximum transmission unit. |
| `Purpose` | Network purpose: Control plane, Internal API, Storage, etc. |
| `DNS Domain` | DNS domain for NetConfig. |
| `Subnet Name` | Subnet name inside NetConfig. |
| `Allocation Start` / `Allocation End` | NetConfig allocationRanges. |
| `Whereabouts Start` / `Whereabouts End` | NAD Whereabouts IPAM ranges. |
| `MetalLB Start` / `MetalLB End` | MetalLB VIP pool ranges. |
| `NAD Master Interface` | Parent interface/bridge for NAD. |
| `NAD Type` | `macvlan` \| `bridge` \| `ipvlan`. |

### RHOSO Data Plane Nodes (row table)

| Column | Description |
|--------|-------------|
| `Node Name` | Unique data plane node name. |
| `Ansible Host` | SSH IP or hostname. |
| `Role` | `compute` \| `networker` \| `compute-networker`. |
| `Management IP` | IP on management/ctlplane network. |
| `NIC1 MAC` / `NIC2 MAC` | MACs for EDPM NIC mappings. |
| `NUMA Topology` | NUMA hint. |
| `CPU Pinning` | `enabled` \| `disabled`. |
| `BMC Address` | BMC/Redfish URI (unprovisioned). |
| `Boot MAC Address` | Boot NIC MAC (unprovisioned). |
| `BMH Namespace` | Namespace for BareMetalHost CRs. |
| `FQDN Internal API` | Per-node internal API FQDN. |

---

## Manifest Catalog

CPAT generates **19 manifest templates** covering 100% of RHOSO deployment CRs.
Conditional templates are only rendered when their CIQ conditions are met.

| # | Template | CR Kind | Applied Phase | Conditional |
|---|----------|---------|--------------|-------------|
| 1 | `openstack_nncp.yaml.j2` | NodeNetworkConfigurationPolicy | Network Preparation | Always |
| 2 | `openstack_nad.yaml.j2` | NetworkAttachmentDefinition | Network Preparation | Always |
| 3 | `openstack_metallb.yaml.j2` | IPAddressPool + L2Advertisement | Network Preparation | Always |
| 4 | `openstack_netconfig.yaml.j2` | NetConfig | Network Preparation | Always |
| 5 | `openstack_control_plane.yaml.j2` | OpenStackControlPlane (~555 lines, fully CIQ-driven) | Control Plane Deploy | Always |
| 6 | `edpm_network_config_template.j2` | Embedded in NodeSet ansibleVars | Data Plane Deploy | Always |
| 7 | `openstack_dataplane_nodeset.yaml.j2` | OpenStackDataPlaneNodeSet | Data Plane Deploy | Always |
| 8 | `openstack_dataplane_deployment.yaml.j2` | OpenStackDataPlaneDeployment | Data Plane Deploy | Always |
| 9 | `openstack_baremetalhosts.yaml.j2` | BareMetalHost + BMC Secrets | Data Plane Deploy | When unprovisioned |
| 10 | `openstack_nmstate_secrets.yaml.j2` | NMState provisioning Secrets | Data Plane Deploy | When unprovisioned |
| 11 | `openstack_nova_cpu_pinning_cm.yaml.j2` | Nova CPU pinning ConfigMap | Data Plane Deploy | When CPU pinning set |
| 12 | `catalog_source.yaml.j2` | CatalogSource | Disconnected Prep | When disconnected |
| 13 | `image_digest_mirror_set.yaml.j2` | ImageDigestMirrorSet | Disconnected Prep | When disconnected |
| 14 | `image_tag_mirror_set.yaml.j2` | ImageTagMirrorSet | Disconnected Prep | When disconnected |
| 15 | `operatorhub_disable_defaults.yaml.j2` | OperatorHub patch | Disconnected Prep | When disconnected |
| 16 | `openstack_lso.yaml.j2` | Namespace + OperatorGroup + Subscription + LocalVolumeDiscovery + LocalVolumeSet | Storage Config | When LSO Enabled |
| 17 | `openstack_observability_operator.yaml.j2` | Namespace + OperatorGroup + Subscription | Operator Install | When Observability Enabled |
| 18 | `openstack_trident.yaml.j2` | TridentOrchestrator + TridentBackendConfig + StorageClass + Secret | Storage Config | When Trident Enabled |
| 19 | `openstack_multipath_config.yaml.j2` | Multipath ConfigMap/Secret | Storage Config | When Multipath Enabled |

### Required CRDs vs generated CRs

| Area | CRD (must exist on cluster) | CR generated by CPAT |
|------|----------------------------|----------------------|
| Operator init | `openstacks.operator.openstack.org` | `OpenStack` |
| Control plane | `openstackcontrolplanes.core.openstack.org` | `OpenStackControlPlane` |
| Networks | `netconfigs.network.openstack.org` | `NetConfig` |
| Networks | `network-attachment-definitions.k8s.cni.cncf.io` | `NetworkAttachmentDefinition` |
| Networks | `nodenetworkconfigurationpolicies.nmstate.io` | `NodeNetworkConfigurationPolicy` |
| Networks | `ipaddresspools.metallb.io` / `l2advertisements.metallb.io` | `IPAddressPool` / `L2Advertisement` |
| Data plane | `openstackdataplanenodesets.dataplane.openstack.org` | `OpenStackDataPlaneNodeSet` |
| Data plane | `openstackdataplanedeployments.dataplane.openstack.org` | `OpenStackDataPlaneDeployment` |
| Data plane | `openstackdataplaneservices.dataplane.openstack.org` | (created by Operator) |
| Unprovisioned | `baremetalhosts.metal3.io` | `BareMetalHost` |

---

## Cluster Commands by Phase

### Pre-check

| Command | Purpose |
|---------|---------|
| `oc get nodes` | Verify RHOCP cluster access |
| `oc get crd \| grep openstack` | Verify OpenStack Operator CRDs |
| `oc whoami` | Confirm cluster-admin access |

### Network Preparation

| Command | Purpose |
|---------|---------|
| `oc get nncp` | Verify NNCP applied |
| `oc get net-attach-def -n openstack` | Verify NADs created |
| `oc get ipaddresspool -n metallb-system` | Verify MetalLB pools |
| `oc get l2advertisement -n metallb-system` | Verify L2 advertisements |
| `oc get netconfig -n openstack` | Verify NetConfig |

### Operator Installation

| Command | Purpose |
|---------|---------|
| `oc get csv -n openshift-nmstate` | NMState Operator CSV status |
| `oc get csv -n metallb-system` | MetalLB Operator CSV status |
| `oc get csv -n cert-manager-operator` | Cert-Manager CSV status |
| `oc get csv -n openshift-local-storage` | LSO Operator CSV status |
| `oc get csv -n openshift-cluster-observability-operator` | Observability CSV status |
| `oc get tridentorchestrator -n trident` | Trident Operator status |

### Control Plane

| Command | Purpose |
|---------|---------|
| `oc get openstackcontrolplane -n openstack` | Check control plane status |
| `oc get pods -n openstack` | Verify service pods running |
| `oc get secret osp-secret -n openstack` | Verify osp-secret exists |
| `oc get openstackclient -n openstack` | Verify openstackclient pod |

### Data Plane

| Command | Purpose |
|---------|---------|
| `oc get openstackdataplanenodeset -n openstack` | Check NodeSet status |
| `oc get openstackdataplanedeployment -n openstack` | Check deployment status |
| `oc get baremetalhost -n openstack` | Check BMH status (unprovisioned) |
| `oc get secret -n openstack \| grep dataplane` | Verify data plane secrets |

### Storage

| Command | Purpose |
|---------|---------|
| `oc get storageclass` | List available StorageClasses |
| `oc get pvc -n openstack` | List PVCs in openstack namespace |
| `oc get localvolumediscovery -n openshift-local-storage` | Verify LSO discovery |
| `oc get localvolumeset -n openshift-local-storage` | Verify LSO volume set |
| `oc get tridentbackendconfig -n trident` | Verify Trident backend |

### Observability

| Command | Purpose |
|---------|---------|
| `oc get monitoringstack -n openshift-cluster-observability-operator` | Verify MonitoringStack |
| `oc get pods -n openshift-cluster-observability-operator -l app.kubernetes.io/name=prometheus` | Check Prometheus pods |

### Post-Deployment Validation

| Command | Purpose |
|---------|---------|
| `openstack endpoint list` | Verify service endpoints |
| `openstack network list` | Verify Neutron networks |
| `openstack compute service list` | Verify Nova compute services |
| `openstack volume service list` | Verify Cinder services |
| `openstack image list` | Verify Glance images |
| `openstack flavor list` | List available flavors |

---

## Troubleshooting Guide

### Container issues

| Symptom | Resolution |
|---------|-----------|
| UI shows outdated version | Hard-refresh browser (Ctrl+Shift+R). Check sidebar version matches expected. |
| Container fails to start | Check `podman logs cpat`. Verify port 8080 is free. |
| Ansible not found | Ensure `ansible-core` is installed in the image. Rebuild with `./bringup.sh build`. |
| Permission denied on secrets | Files under `/cpat-data/secrets/` should be `0600`. Check volume mount permissions. |
| MSYS path mangling on Windows | `bringup.sh` sets `MSYS2_ARG_CONV_EXCL='*'`. Entrypoint forces `CPAT_DATA_DIR=/cpat-data`. |

### Registration issues

| Symptom | Resolution |
|---------|-----------|
| "No rhoso_details table found" | Ensure CIQ workbook has a `rhoso_details` table with `Type = RHOSO`. |
| Header normalization errors | CIQ headers are auto-normalized (UPPERCASE → mixed-case). Check for typos. |
| Duplicate cluster name | Each RHOSO environment must have a unique `Cluster Name`. |

### Generation issues

| Symptom | Resolution |
|---------|-----------|
| "rhoso_apply_manifests must be false" | Use the "Generate Manifests for Review" button (not a deploy task). |
| Empty NNCP worker list | Generate doesn't require kubeconfig — worker names are best-effort. Review/edit before Deploy. |
| Missing disconnected CRs | Set `Deployment Mode = disconnected` in CIQ and provide mirror registry details. |
| Missing storage CRs | Set `LSO Enabled`, `Trident Enabled`, or `Multipath Enabled` to `yes` in CIQ. |

### Deployment issues

| Symptom | Resolution |
|---------|-----------|
| "Kubeconfig not found" | Upload kubeconfig via Dashboard → Input Files or set `Kubeconfig Path` in CIQ. |
| CSV timeout | Increase wait time or check OLM Subscription status manually. Verify CatalogSource for disconnected. |
| ControlPlane not Ready | Check `oc get openstackcontrolplane -n openstack -o yaml` for conditions. Verify osp-secret, StorageClass, network CRs. |
| NodeSet SetupReady failed | Check SSH key secret, subscription credentials, network connectivity to compute nodes. |
| Deployment failed | Remove failed Deployment CRs (`oc delete openstackdataplanedeployment <name> -n openstack`) and retry. Check AnsibleEE job logs. |
| Trident Orchestrator not Installed | Verify `oc get tridentorchestrator -n trident -o yaml`. Check image registry settings for disconnected. |
| MonitoringStack not Available | Verify Observability Operator CSV Succeeded. Check namespace and operator logs. |

### CIQ validation issues

| Symptom | Resolution |
|---------|-----------|
| "Validation failed for N fields" | All validation failures are reported in one message. Fix the listed CIQ parameters and re-register. |
| Boolean coercion errors | CIQ `yes`/`no` values are handled; templates use `\| string` before `\| length`. |
| Missing required fields | Core fields (Cluster Name, Type, Storage Class, namespaces) are mandatory. |

### Data directory layout

| Path | Content |
|------|---------|
| `<CPAT_DATA_DIR>/cpat.db` | SQLite database (clusters, executions) |
| `<CPAT_DATA_DIR>/uploads/` | Registered CIQ workbooks |
| `<CPAT_DATA_DIR>/secrets/<cluster-id>/` | Uploaded kubeconfig, pull secrets, SSH keys |
| `<CPAT_DATA_DIR>/logs/registrations/` | Registration execution logs |
| `<CPAT_DATA_DIR>/logs/installations/` | RHOSO task execution logs |
| `<CPAT_DATA_DIR>/artifacts/<cluster>/` | Generated OpenStack CR manifests |

Local dev: `<repo>/data/` — Container: `/cpat-data`

---

## CIQ Workbook Reference

CIQ workbooks live under `CIQTemplates/`:

| File | Purpose |
|------|---------|
| `sample-rhoso.ciq.xlsx` | Filled example — reference while editing |
| `rhoso-ciq-template.xlsx` | Empty workbook — fill with site values |
| `generate_rhoso_ciq_workbooks.py` | Regenerates sample + empty CIQ files |

```bash
pip install -r CIQTemplates/requirements.txt
python CIQTemplates/generate_rhoso_ciq_workbooks.py
```

### Workbook sheets

- **field_guide** — catalog of every parameter with descriptions
- **RHOSO** — split parameter tables + `rhoso_networks` + `rhoso_data_plane_nodes`
- **values** — dropdown lists (Name Manager names for data validation)

### Disconnected mode

Set `Deployment Mode = disconnected` (or `airgapped` / `offline`) in RHOSO Details
and complete the RHOSO Disconnected table. Run Disconnected Environment Preparation
before Operator Installation.

---

## Ansible Registration and Installation

### Manual registration

```bash
ansible-playbook ansible/playbooks/main.yml --tags register \
  -e '{"ciq_file_path":"CIQTemplates/sample-rhoso.ciq.xlsx","cluster_description":"","registration_target":"rhoso"}'
```

### Manual installation (single task)

```bash
ansible-playbook ansible/playbooks/main.yml --tags rhoso \
  -e '{"ciq_file_path":"CIQTemplates/sample-rhoso.ciq.xlsx","cluster_name":"rhoso-cloud-01","rhoso_version":"RHOSO 18.0","installation_task":"prerequisites"}'
```

Valid `installation_task` values: `manifest_generation`, `prerequisites`,
`_verify_required_crds`, `prerequisite_operator_installation`,
`disconnected_environment_preparation`, `generate_osp_secret`,
`generate_data_plane_secrets`, `generate_ceph_secret`,
`persistent_storage_configuration`, `trident_storage_configuration`,
`_generate_storage_crs`,
`openstack_operator_installation_and_preparation`,
`rhocp_preparation_for_rhoso`, `network_preparation`,
`control_plane_deployment_and_verification`,
`control_plane_customization`,
`data_plane_deployment_and_verification`,
`post_deployment_validation`,
`observability_configuration`.

---

## API Reference

### Core endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/auth/login` | Authentication |
| `POST` | `/api/auth/logout` | Logout |
| `GET` | `/api/auth/me` | Current user |
| `GET` | `/api/dashboard` | Dashboard summary (RHOSO + OCP counts) |
| `GET` | `/api/clusters` | List all registered clusters (`?type=rhoso\|ocp`) |
| `GET` | `/api/clusters/<id>` | Get cluster details |
| `DELETE` | `/api/clusters/<id>` | Delete cluster |
| `GET` | `/api/clusters/<id>/artifacts` | List generated manifests |
| `GET` | `/api/clusters/<id>/artifacts/<file>` | View/download single manifest |
| `GET` | `/api/clusters/<id>/artifacts/download-all` | Download all manifests as ZIP |
| `GET/POST` | `/api/clusters/<id>/input-files` | Manage input file uploads |
| `GET` | `/api/version` | Get CPAT version + supported types |

### RHOSO endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/clusters/register` | Register RHOSO cluster (CIQ upload, NDJSON stream) |
| `POST` | `/api/rhoso-installations/run` | Start RHOSO installation (NDJSON stream) |
| `GET` | `/api/rhoso-installations` | List RHOSO executions |
| `GET` | `/api/rhoso-installations/<id>` | Get execution status |
| `GET` | `/api/rhoso-installations/<id>/log` | Get/download execution log |

### OCP endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/ocp/clusters/register` | Register OCP cluster (CIQ upload) |
| `GET` | `/api/ocp-installations/tasks` | List available OCP task names |
| `POST` | `/api/ocp-installations/run` | Start OCP installation (NDJSON stream) |
| `GET` | `/api/ocp-installations` | List OCP executions |
| `GET` | `/api/ocp-installations/<id>` | Get OCP execution status |
| `GET` | `/api/ocp-installations/<id>/log` | Get/download OCP execution log |

---

*CPAT v25.10.1 — RHOSO CIQ Schema v1.4 + OCP CIQ Schema v1.1 — RHOSO 18.0 + OCP 4.17–4.20*
