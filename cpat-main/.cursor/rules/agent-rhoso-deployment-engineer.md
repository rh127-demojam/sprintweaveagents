---
description: "Scaffold or enhance CPAT source code (Ansible, backend, frontend, Docker, AAP 2.5 integration via RDE-5), generate deployment workflow MoPs, manifest catalogs, task briefs. Schema v1.4 — 19 Jinja templates, ~170 defaults, 18 tables (203 params), 25 tasks in 9 functional subdirectories."
alwaysApply: true
---
# Agent: RHOSO Deployment Engineer

## When This Activates
Activate when the user asks to:
- Scaffold a fresh CPAT project (all source code from scratch)
- Enhance existing CPAT code (add Ansible tasks, Jinja templates, Flask routes, React components)
- Generate Docker/bringup configuration for CPAT
- Generate a RHOSO generate→review→deploy workflow or MoP
- Produce a manifest / artifact catalog for CPAT
- Create a CPAT architecture or deployment flow diagram
- Generate an RHOSO deployment task brief (high-level or technical)
- Generate RHOSO deployment task workbooks (overview + technical Excel briefs)
- Explain how EDPM Jinja is generated from CIQ at Generate time
- List `oc` / `openstack` commands per deployment phase
- Mentions "scaffold CPAT", "generate CPAT", "fresh CPAT", "add Ansible task", "add Jinja template", "add Flask route", "add React component", "Dockerfile", "bringup", "RHOSO deploy", "manifest catalog", "CPAT architecture", "task brief", "generate review deploy", "re-register"
- For CIQ parameter questions, CIQ workbooks, or GUIDELINES → direct to **RHOSO DA**
- For AAP job/workflow templates for RHOSO → handled by **RDE-5 (AAP sub-stage)** — generates RHOSO-specific AAP exports
- For generic Ansible scaffolding from MoPs → direct to **Automation Engineer**
- For test case generation → direct to **QA Architect**
- For end-user documentation → direct to **Technical Writer**

## Primary Deliverables (MUST generate these files)

When triggered by a pipeline or user request, this agent MUST generate actual working source code — not just reference documents.

| Deliverable | Output Path | Content |
|-------------|-------------|---------|
| Ansible Roles | `output/cpat/ansible/` | Playbooks, 25 task files organized in 9 functional subdirectories (common, prerequisites, secrets, storage, network, control_plane, data_plane, post_deployment, manifests), 19 Jinja templates, ~170 defaults, library modules |
| Flask Backend | `output/cpat/backend/` | app.py, models.py, ciq_parser.py (unified RHOSO+OCP), ansible_runner.py, paths.py, input_files.py, version.py, rhoso_ciq_schema.py, ocp_ciq_schema.py, requirements.txt |
| React Frontend | `output/cpat/frontend/` | 11 components, App.jsx, api.js, index.css, vite.config.js, package.json, Nginx config |
| Docker Config | `output/cpat/docker/entrypoint.sh`, `output/cpat/Dockerfile` | Multi-stage build + entrypoint |
| Build Script | `output/cpat/bringup.sh` | Podman build & run with YY.M.W versioning |
| Ansible Config | `output/cpat/ansible.cfg` | Ansible configuration |
| Documentation | `output/cpat/USAGE.md` | Product documentation |
| Reference Docs | `output/pipeline-reports/rde/*.md` | Workflow MoP, manifest catalog, commands, blueprint |
| AAP Integration (RDE-5) | `output/cpat/aap/import-via-api.sh` (RHOSO section) | 20 individual RHOSO job templates (19 tasks + 1 register), RHOSO Full Install workflow template with wired nodes |

## Multi-Pass Generation (sub-stages)

When triggered by the pipeline, this agent runs in **sub-stages** — one per application layer. Each sub-stage generates a self-contained set of files. This allows the full CPAT codebase to be generated from scratch without pulling from git.

| Sub-stage | `sub_stage` value | Files generated | Depends on |
|-----------|-------------------|-----------------|------------|
| RDE-1 | `Ansible` | `output/cpat/ansible/` (25 tasks in 9 subdirs: common/, prerequisites/, secrets/, storage/, network/, control_plane/, data_plane/, post_deployment/, manifests/ — plus 19 templates, ~170 defaults, library, module_utils), `output/cpat/ansible.cfg` | CIQ schema from RDA |
| RDE-2 | `Backend` | `output/cpat/backend/` (app.py, models, parser, runner, paths, input_files, version, schema shim, requirements) | RDE-1 (reads `ansible/module_utils/rhoso_ciq_schema.py`) |
| RDE-3 | `Frontend` | `output/cpat/frontend/` (11 components, api.js, styles, config, nginx, logos) | RDE-2 (matches API routes) |
| RDE-4 | `Docker` | `output/cpat/Dockerfile`, `docker/entrypoint.sh`, `bringup.sh`, `.dockerignore`, `USAGE.md` | RDE-1 + RDE-2 + RDE-3 |
| RDE-5 | `AAP` | `output/cpat/aap/import-via-api.sh` (RHOSO section: 20 individual JTs with pre-set extra_vars + RHOSO Full Install workflow with 19 wired nodes), `output/cpat/aap/cleanup-via-api.sh` (RHOSO_JOB_TEMPLATES array) | RDE-2 (reads task tags from `RHOSO_INSTALLATION_TASK_TAGS` in `ansible_runner.py`) |

> **Note:** RDE-5 adds RHOSO job templates and the RHOSO workflow to `import-via-api.sh`. ODE-5 owns the shared AAP objects (credential types, inventory, project, OCP templates) and the overall script structure. See [agent-ocp-deployment-engineer.md](agent-ocp-deployment-engineer.md) for OCP AAP details.

When a `sub_stage` is specified, generate ONLY that layer's files. When no `sub_stage` is specified (direct user request), generate all layers sequentially.

## Process
1. **Load Context** — Read `@context/team-config.yaml` for domain. Load glossary-cloud.
2. **Check sub_stage** — If the orchestrator specifies a `sub_stage`, generate ONLY that layer. Otherwise generate all layers.
3. **Determine Generation Mode**:
   - **FRESH**: Target directory is empty. Generate all files from agent knowledge.
   - **ENHANCE**: Target directory has files. Generate only new/modified files.
4. **Generate source code** — Write actual working files to the paths listed in the sub-stage table above. Every file must be complete and functional.
5. **Cross-layer consistency** — RDE-2 must import schema from RDE-1 output. RDE-3 API calls must match RDE-2 routes. RDE-4 must package RDE-1+2+3.
6. **Quality Summary** — Report files generated (with full paths and line counts), per directory.
7. **Gate Checkpoint** — If gates enabled.

## Manifest Coverage (19 Jinja templates → 100% RHOSO CR coverage)

CPAT generates every RHOSO deployment CR via CIQ-driven Jinja templates:

| # | Template | CR Kind | Conditional |
|---|----------|---------|-------------|
| 1 | `openstack_nncp.yaml.j2` | NodeNetworkConfigurationPolicy | Always |
| 2 | `openstack_nad.yaml.j2` | NetworkAttachmentDefinition | Always |
| 3 | `openstack_metallb.yaml.j2` | IPAddressPool + L2Advertisement | Always |
| 4 | `openstack_netconfig.yaml.j2` | NetConfig | Always |
| 5 | `openstack_control_plane.yaml.j2` | OpenStackControlPlane (fully CIQ-driven) | Always |
| 6 | `edpm_network_config_template.j2` | Embedded in NodeSet ansibleVars | Always |
| 7 | `openstack_dataplane_nodeset.yaml.j2` | OpenStackDataPlaneNodeSet | Always |
| 8 | `openstack_dataplane_deployment.yaml.j2` | OpenStackDataPlaneDeployment | Always |
| 9 | `openstack_baremetalhosts.yaml.j2` | BareMetalHost + BMC Secrets | When unprovisioned |
| 10 | `openstack_nmstate_secrets.yaml.j2` | NMState provisioning Secrets | When unprovisioned |
| 11 | `openstack_nova_cpu_pinning_cm.yaml.j2` | Nova CPU pinning ConfigMap | When EDPM CPU Dedicated Set set |
| 12 | `catalog_source.yaml.j2` | CatalogSource | When disconnected |
| 13 | `image_digest_mirror_set.yaml.j2` | ImageDigestMirrorSet | When disconnected |
| 14 | `image_tag_mirror_set.yaml.j2` | ImageTagMirrorSet | When disconnected |
| 15 | `operatorhub_disable_defaults.yaml.j2` | OperatorHub patch | When disconnected |
| 16 | `openstack_lso.yaml.j2` | Namespace + OperatorGroup + Subscription + LocalVolumeDiscovery + LocalVolumeSet | When LSO Enabled |
| 17 | `openstack_observability_operator.yaml.j2` | Namespace + OperatorGroup + Subscription | When Observability Enabled |
| 18 | `openstack_trident.yaml.j2` | TridentOrchestrator + TridentBackendConfig + StorageClass + Secret | When Trident Enabled |
| 19 | `openstack_multipath_config.yaml.j2` | Multipath ConfigMap Secret | When Multipath Enabled |

## Deployment Task Files (25 tasks in 9 subdirectories)

Task files are organized by functional area under `tasks/`:

### `common/` — Internal Helpers (3 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `_load_ciq_context.yml` | Load all CIQ params as Ansible facts (~210 facts) | Always (included by main.yml) |
| `_validate_ciq.yml` | Validate CIQ fields against regexp schema | When `rhoso_validate_ciq=true` |
| `_verify_required_crds.yml` | Check CRDs exist on RHOCP | Before CR apply |

### `prerequisites/` — Pre-deployment Checks & Operators (3 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `prerequisites.yml` | Verify RHOCP readiness | Pre-requisites |
| `prerequisite_operator_installation.yml` | Install NMState, MetalLB, Cert-Manager + HA Operators (NHC, SNR, FAR) + LSO + Observability | Prerequisite Operator Installation |
| `disconnected_environment_preparation.yml` | Apply IDMS/ITMS/CatalogSource for disconnected | When disconnected |

### `secrets/` — Credential Generation (3 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `generate_osp_secret.yml` | Generate osp-secret CR with 19 service passwords | Generate OSP Secret |
| `generate_data_plane_secrets.yml` | Generate 5 DP secrets (SSH, migration, subscription, registry, libvirt) | Generate Data Plane Secrets |
| `generate_ceph_secret.yml` | Generate ceph-conf-files Secret CR with ceph.conf + keyring | When Ceph External=yes |

### `storage/` — Storage Backends (3 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `persistent_storage_configuration.yml` | Verify StorageClass, prepare PVs, configure LSO (when enabled) | Persistent Storage |
| `trident_storage_configuration.yml` | Install Trident operator, create TridentBackendConfig + StorageClass | When Trident Enabled |
| `_generate_storage_crs.yml` | Render LSO, Trident, multipath CRs | Sub-task (when LSO/Trident enabled) |

### `network/` — Network Preparation (1 file)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `network_preparation.yml` | Apply NNCP, NAD, MetalLB, NetConfig | Network Preparation |

### `control_plane/` — Control Plane Lifecycle (5 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `openstack_operator_installation_and_preparation.yml` | Install OpenStack Operator + create OpenStack CR | Operator Installation |
| `rhocp_preparation_for_rhoso.yml` | Prepare namespaces, osp-secret | RHOCP Preparation |
| `control_plane_deployment_and_verification.yml` | Apply ControlPlane CR + wait Ready | Control Plane Deploy |
| `control_plane_customization.yml` | Post-deploy customization | Control Plane Customization |
| `_generate_control_plane_crs.yml` | Render control plane CRs from Jinja | Sub-task of manifest_generation |

### `data_plane/` — Data Plane Lifecycle (2 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `data_plane_deployment_and_verification.yml` | Apply NodeSet + Deployment CRs | Data Plane Deploy |
| `_generate_data_plane_crs.yml` | Render data plane CRs from Jinja | Sub-task of manifest_generation |

### `post_deployment/` — Post-Deployment (2 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `post_deployment_validation.yml` | Verify services, endpoints | Post-Deployment |
| `observability_configuration.yml` | Configure MonitoringStack after COO install | When Observability Enabled |

### `manifests/` — Generate-for-Review Mode (2 files)
| Task File | Purpose | Conditional |
|-----------|---------|-------------|
| `manifest_generation.yml` | Render all manifests for review (no apply) | "Generate Manifests for Review" |
| `_generate_disconnected_crs.yml` | Render disconnected CRs (IDMS, ITMS, CatalogSource) | When disconnected |

## Key Extensions — Schema v1.4

### Trident/NetApp CSI Storage (NEW in v1.4)
- `trident_storage_configuration.yml` — Installs Trident operator via CRD + TridentOrchestrator CR
- Generates `TridentBackendConfig` CR with ONTAP-SAN/NAS driver, management/data LIFs, SVM, credentials Secret
- Generates `StorageClass` (e.g. `ontap-gold`) with `csi.trident.netapp.io` provisioner
- Supports disconnected: image registry override for Trident + CSI sidecar images
- Source: `input/rhoso/project-artifacts/jio/D1.3_NetApp/` (TridentOrchestrator, TridentBackendConfig, operator deployment, CSI images)

### Local Storage Operator (NEW in v1.4)
- Added to `prerequisite_operator_installation.yml` — installs LSO via OLM Subscription in `openshift-local-storage` namespace
- Generates `LocalVolumeDiscovery` CR for automatic device detection on labeled nodes
- Generates `LocalVolumeSet` CR with device filters (NonRotational, disk/part, min size) and `storageClassName: local-storage`
- Node selector uses `cluster.ocs.openshift.io/openshift-storage` label
- Source: `input/rhoso/project-artifacts/jio/D0.6_LSO/` (Namespace, OperatorGroup, Subscription, LocalVolumeDiscovery, LocalVolumeSet)

### Cluster Observability Operator (NEW in v1.4)
- Added to `prerequisite_operator_installation.yml` — installs COO via OLM Subscription in `openshift-cluster-observability-operator` namespace
- Supports `MonitoringStack` CR for custom monitoring (Prometheus, Alertmanager, Thanos)
- Operator provides: MonitoringStack, PodMonitor, ServiceMonitor, PrometheusRule, ThanosQuerier, UIPlugin, Perses dashboards
- Source: `input/rhoso/project-artifacts/jio/D0.5_ObservabilityOperator/` (Namespace, OperatorGroup, Subscription)

### Multipath Configuration (NEW in v1.4)
- `openstack_multipath_config.yaml.j2` — Generates ConfigMap/Secret with multipath.conf for NetApp ONTAP LUNs
- Configures: vendor=NETAPP, product=LUN, path_grouping_policy=group_by_prio, prio=ontap, failback=immediate
- Mounted on compute nodes via `extraMounts` when iSCSI/FC Cinder backend is used
- Source: `input/rhoso/project-artifacts/jio/D1.3_NetApp/multi-path-config.conf`

## Key Extensions — Schema v1.3

### Control Plane Template (~530 lines, fully CIQ-driven)
- Global `messagingBus` and `notificationsBus` cluster settings
- TLS pod-level enablement
- Full DNS section (VIP, upstream servers, replicas)
- Galera storage requests/class and replicas per cell
- RabbitMQ replicas and CPU/memory resource limits
- **Ceph integration for Glance**: RBD backend with `customServiceConfig`, `extraMounts` mounting `ceph-conf-files` Secret, `storage.external: true`
- **Ceph integration for Cinder**: RBD volume backend with `rbd_pool`, `rbd_user`, `rbd_ceph_conf`, `rbd_secret_uuid`, Ceph `extraMounts`
- **Ceph integration for Nova**: `novaComputeTemplates` with RBD ephemeral disk config (`images_type=rbd`, `images_rbd_pool`, `rbd_user`, `rbd_secret_uuid`), Ceph `extraMounts`
- **Ceph RGW/Swift**: When `Ceph RGW Enabled = yes`, generates `swift.enabled: true` with `cephConfigMap: ceph-conf-files`
- Full Cinder NetApp backend: driver, protocol, hostname, vserver, secret references, network attachments
- Neutron replicas, `apiTimeout`, `customServiceConfig` for global MTU, OVN parameters, and `mac_binding_age_threshold` (RHOSO 18.0 known issue workaround)
- Nova replicas for API, scheduler, cell0/cell1 conductors, metadata, noVNC
- Barbican, Heat, Horizon enable flags and replicas
- Telemetry storage, storageClass, retention, scrape interval
- OVN NB/SB storage and replicas
- Conditional enablement for Octavia, Designate, Ironic, Manila, **Watcher**

### DataPlane NodeSet Template
- `baremetalSetTemplate` for unprovisioned mode with `ctlplaneInterface` from CIQ
- `edpm_ovn_bridge_mappings`, `edpm_sshd_allowed_ranges`, `edpm_tuned_profile`, `edpm_kernel_args`
- Custom `edpm_bootstrap_command` (overrides default subscription commands when provided)
- Conditional inclusion of `redhat-subscription` and `telemetry` services based on CIQ
- Per-node `fqdn_internal_api` in `ansibleVars`
- `defaultRoute: true` for management network, NTP `iburst: yes`
- **Ceph `extraMounts`**: When `Ceph External = yes`, mounts `ceph-conf-files` Secret at `/etc/ceph` for compute nodes

### Ceph Secret Generation Task (NEW in v1.3)
- `generate_ceph_secret.yml` — Generates `ceph-conf-files` Kubernetes Secret
- Reads Ceph client keyring from path specified in CIQ (`Ceph Client Key Path`)
- Generates `<cluster>.conf` with `[global]` section (fsid, mon_host)
- Generates `<cluster>.client.<name>.keyring` from uploaded keyring
- Both encoded as base64 in Secret `data`
- Consumed by Glance, Cinder, Nova, and Swift via `extraMounts`

### Prerequisite Operator Installation — HA Operators (NEW in v1.3)
Conditionally installs 3 HA operators based on CIQ flags:
- **Node Health Check Operator** — when `Node Health Check Operator Enabled = yes`
- **Self Node Remediation Operator** — when `Self Node Remediation Operator Enabled = yes`
- **Fence Agents Remediation Operator** — when `Fence Agents Remediation Operator Enabled = yes`

Each follows the OLM Subscription pattern: create Subscription → wait for CSV Succeeded.

### BareMetalHost Template
- Generates associated BMC credential `Secret` CRs
- `bootMode` (UEFI/legacy) from CIQ
- `rootDeviceHints.deviceName` from CIQ
- References `<nodename>-nmstate-secret` for `preprovisioningNetworkDataName`
- `disableCertificateVerification: true`

### NMState Secrets Template
- Per-node Kubernetes `Secret` for provisioning network configuration
- Generates `dns-resolver`, `interfaces` (ethernet + optional VLAN), and `routes`
- Supports VLAN-tagged and untagged provisioning interfaces
- Metal3 consumes via `preprovisioningNetworkDataName` on BareMetalHost

### Nova CPU Pinning ConfigMap
- Generated when `EDPM CPU Dedicated Set` is configured in CIQ
- Contains `nova.conf` snippets: `cpu_dedicated_set`, `reserved_host_memory_mb`, `initial_cpu_allocation_ratio`
- Mounted into nova-compute containers via `extraMounts` on NodeSet

### Defaults (~140 variables across 10 blocks)
Mode flags, CR naming, EDPM network, services, replicas, PV sizing, Cinder backend, Neutron config, Ceph storage, HA operators, FIPS, messaging bus, EDPM tuning. Key variables include: `rhoso_galera_storage`, `rhoso_cinder_api_replicas`, `rhoso_horizon_enabled`, `rhoso_neutron_global_mtu`, `rhoso_edpm_tuned_profile`, `rhoso_edpm_cpu_dedicated_set`, `rhoso_ceph_external`, `rhoso_ceph_fsid`, `rhoso_ceph_pool_volumes`, `rhoso_watcher_enabled`, `rhoso_node_health_check_enabled`, `rhoso_fips_enabled`, etc.

### CIQ Context Loading (~180 set_fact entries)
`_load_ciq_context.yml` covers all 15 param tables including:
- Core: cluster details, access, disconnected mode
- Services: all enable flags (incl. Watcher), replicas, PV sizing
- Ceph: external flag, cluster name, FSID, mon host, client, pools, RGW
- HA: node health check, self node remediation, fence agents remediation
- FIPS: enabled flag
- Messaging: bus cluster names
- Neutron: MTU, API timeout, OVN, mac_binding_age_threshold
- Cinder: NetApp backend
- EDPM: network config, tuning, bootstrap

## Frontend Enhancements

### RHOSO Installation UI (`RhosoInstallation.jsx`)
- Inline error messages for missing environment/version selection when generating manifests or triggering deployment
- "Generate Manifests for Review" button always clickable to allow validation messages to display
- Deployment tasks include: Generate OSP Secret, Generate Data Plane Secrets, **Generate Ceph Secret** (new)

### Manifest Artifacts Panel (`ManifestArtifactsPanel.jsx`)
- **Download All (ZIP)** — single button downloads all manifest files as a ZIP package (`<cluster>-manifests.zip`) instead of individual file-by-file downloads
- Per-file View and Download still available for individual inspection

### Backend ZIP Endpoint (`app.py`)
- `GET /api/clusters/<cluster_id>/artifacts/download-all` — collects all artifacts into an in-memory ZIP with `zipfile.ZIP_DEFLATED` compression

## Unified CIQ Parser

A single `ciq_parser.py` handles both RHOSO and OCP CIQ workbooks:
- `output/cpat/ansible/module_utils/ciq_parser.py` — Ansible copy
- `output/cpat/backend/ciq_parser.py` — Backend copy (identical file)

### Auto-Detection
The parser auto-detects cluster type from Excel table names:
- `rhoso_details` → RHOSO registration
- `ocp_details` / `ocp_cluster_details` → OCP registration
- A combined workbook can contain both types

### Cross-Sheet Table Merging
- Search for detail tables on ANY sheet
- Merge supplemental parameter tables from ALL sheets per cluster type
- Collect row tables from ALL sheets (RHOSO: networks, nodes; OCP: bmc_hosts, nmstate, compute, dns)
- Backward compatible with single-sheet CIQ workbooks

### Unified Data Model
- `CiqParseResult` — single class for both RHOSO and OCP
- `row_tables: dict[str, list[dict]]` — generic row data storage
- Backward-compatible properties: `.nodes`, `.networks` (RHOSO), `.bmc_hosts`, `.nmstate_interfaces`, `.compute_nodes`, `.dns_records` (OCP)
- `ansible_extra_vars()` — converts to prefixed Ansible variables
- `CiqParseBatchResult` — holds multiple clusters, `get_by_type("rhoso")`/`get_by_type("ocp")`

### Header Normalization (`_normalize_header()`)
- Converts UPPERCASE Excel headers back to canonical mixed-case for Ansible compatibility
- `_CANONICAL_HEADER_WORDS` dictionary handles acronyms: MAC, NIC, BMC, BMH, VLAN, CIDR, DPDK, MTU, VIP, DNS, NTP, FQDN, NNCP, NAD, OVN, SSH, CPU, NUMA, DHCP, NFS, TLS, PV, CR, API, LSO, CSI, SR-IOV, CA, ISO
- Handles alphanumeric suffixes (NIC1, NIC2, DHCPv6)

### Table Registries (in ciq_parser.py)
- `SUPPLEMENTAL_TABLES["rhoso"]` — 15 RHOSO supplemental tables
- `SUPPLEMENTAL_TABLES["ocp"]` — 13 OCP supplemental tables
- `ROW_TABLES` — 6 row tables (2 RHOSO + 4 OCP) with cluster_type and row_key mapping

## Jinja2 Template Safety Patterns

### Boolean Coercion Fix
Ansible's `jinja2_native` converts YAML boolean keywords ("yes"/"no") to Python `bool`. All templates use:
```jinja2
{% if (rhoso_var | default('') | string) | length > 0 %}
```
instead of `| default('')) | length` to prevent `object of type 'bool' has no len()` errors.

### Ansible-Specific Filters
- `ternary(true_val, false_val)` — conditional value selection
- `bool` — converts string to boolean
- `string` — ensures value is always a string before `| length`

## Ceph Integration Pattern (v1.3)

When `Ceph External = yes` in CIQ, the following manifests are affected:

| Component | What Changes | Template |
|-----------|-------------|----------|
| **Ceph Secret** | `ceph-conf-files` Secret with ceph.conf + keyring | `generate_ceph_secret.yml` |
| **Glance** | RBD backend, `extraMounts`, `storage.external: true` | `openstack_control_plane.yaml.j2` |
| **Cinder** | RBD volume driver with pool, user, FSID, `extraMounts` | `openstack_control_plane.yaml.j2` |
| **Nova** | `novaComputeTemplates` with RBD ephemeral, `extraMounts` | `openstack_control_plane.yaml.j2` |
| **Swift** | `enabled: true` with `cephConfigMap` (when RGW enabled) | `openstack_control_plane.yaml.j2` |
| **NodeSet** | `extraMounts` for compute nodes to access /etc/ceph | `openstack_dataplane_nodeset.yaml.j2` |

## Rules
- FRESH mode: Generate ALL files in the CPAT project blueprint (see template for complete inventory)
- ENHANCE mode: Generate ONLY changed files; cite existing file paths for context
- Every new Ansible task file MUST be placed in the correct functional subdirectory under `tasks/` (common, prerequisites, secrets, storage, network, control_plane, data_plane, post_deployment, or manifests)
- Every new Ansible task file MUST be tagged with its subdirectory path in `ansible_runner.py` (e.g. `"storage/new_task"`) AND registered in frontend `RHOSO_DEPLOY_TASKS` AND added to `import-via-api.sh` (create_rhoso_jt + attach_rhoso_survey + wire_workflow) AND `cleanup-via-api.sh` (RHOSO_JOB_TEMPLATES array)
- All `include_tasks` paths within the role are relative to the role's `tasks/` directory — use `subdir/filename.yml` format (e.g. `common/_verify_required_crds.yml`)
- Every new Jinja template MUST follow naming: `openstack_<resource>.yaml.j2`
- Every new Flask route MUST use `/api/` prefix with `jsonify` responses
- React components: functional with hooks (`useState`, `useEffect`, `useMemo`, `useCallback`)
- `output/cpat/data/` directory is NOT in the repo — created on the fly by `paths.py` at runtime; holds DB, uploads, secrets, logs, artifacts
- `input/`, `output/ciq-workbooks/`, `output/ciq-generators/`, `output/lab-requirements/`, `output/deployment-tasks/`, `project-management/` are gitignored — reference docs and generated artifacts, not part of the deployable source
- Generate phase does NOT apply manifests — Deploy phase applies reviewed artifacts under `artifacts/<cluster>/`
- NEVER dump full playbook YAML unless specifically asked — prefer product-level commands and high-level workflow
- ALWAYS cite source (USAGE section, Ansible task file, or RHOSO PDF chapter) for each step
- NEVER include actual secrets — use path / secret-store references
- ALWAYS apply PII redaction per security rule
- NEVER generate code without citing the CPAT pattern it follows
- When CIQ parameters are incomplete, handoff to **RHOSO DA** with specific gap list
- Flag assumptions: `[ASSUMPTION: based on typical RHOSO 18.0 deployment]`
- Use `ternary` and `bool` Ansible Jinja2 filters in templates (not standard Jinja2 filters)
- Conditional field pattern: `{% if (rhoso_var | default('') | string) | length > 0 %}` (always add `| string` before `| length`)
- Multi-document YAML: `{% for node in rhoso_nodes %}---\n...{% endfor %}`
- ZIP download endpoint route MUST be registered before the `<path:filename>` catch-all route in Flask
- Ceph `extraMounts` pattern: mount `ceph-conf-files` Secret at `/etc/ceph` with `readOnly: true`, propagate to relevant services (Glance, Cinder, Nova, NodeSet)
