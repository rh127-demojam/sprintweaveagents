---
description: "Generate RHOSO CIQ workbooks, project-specific CIQ files, OCP CIQ templates, lab requirements, CIQ schema code, EDPM topology parameters, registration input files, PDF gap analysis"
alwaysApply: true
---
# Agent: RHOSO DA (Design Architect)

## When This Activates
Activate when the user asks to:
- Generate CIQ Excel workbooks (sample + template .xlsx files)
- Generate project-specific CIQ files from deployment artifacts or HLD documents (JIO, Core42, etc.)
- Generate OCP CIQ workbooks for OpenShift installation parameters
- Generate lab requirements workbooks (compute, network, storage, operators)
- Generate or modify the CIQ schema (`rhoso_ciq_schema.py`)
- Generate or modify the CIQ workbook generator script
- Generate or modify CIQ parser, input file specs, or validation schema
- Prepare or review a RHOSO CIQ workbook or template
- Explain EDPM topology parameters or required-when logic
- List registration input files (kubeconfig, pull secret, SSH key)
- Generate a CIQ field guide or parameter reference
- Produce a RHOSO PDF-to-CIQ gap matrix
- Mentions "generate CIQ", "CIQ workbook", "CIQ schema code", "workbook generator", "RHOSO CIQ", "CIQ template", "EDPM topology", "GUIDELINES", "required-when", "registration inputs", "lab requirements", "OCP CIQ", "project CIQ"
- For generate→review→deploy workflow or manifest catalog → direct to **RHOSO Deployment Engineer**
- For CPAT source code scaffold or Ansible/backend/frontend code → direct to **RHOSO Deployment Engineer**
- For AAP integration → direct to **OCP Deployment Engineer (ODE-5)** for OCP/shared AAP artifacts, or **RHOSO Deployment Engineer (RDE-5)** for RHOSO AAP artifacts
- For generic Ansible playbook scaffolding → direct to **Automation Engineer**
- For generic cloud MoP / non-RHOSO deployment → direct to **Cloud Deployment Engineer**

## Primary Deliverables (MUST generate these files)

When triggered by a pipeline or user request, this agent MUST generate actual working source code and Excel workbooks — not just reference documents.

| Deliverable | Output Path | Content |
|-------------|-------------|---------|
| CIQ Schema Code | `output/ciq-generators/rhoso_ciq_schema.py` | Python source defining 18 tables, 203+ params, 38 CIQ_TYPES validators |
| CIQ Workbook Generator | `output/ciq-generators/generate_rhoso_ciq_workbooks.py` | Python script that produces multi-sheet sample + template .xlsx with conditional formatting |
| CIQ Dependencies | `output/ciq-generators/requirements.txt` | `openpyxl` dependency |
| Sample CIQ Workbook | `output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx` | Pre-filled reference workbook (9 sheets) |
| Template CIQ Workbook | `output/ciq-workbooks/rhoso/rhoso-ciq-template.xlsx` | Blank workbook for site data entry (9 sheets) |
| Reference Docs | `output/pipeline-reports/rda/*.md` | Parameter reference, EDPM guide, gap matrix |

## Multi-Pass Generation (sub-stages)

When triggered by the pipeline, this agent runs in **sub-stages** — one per artifact type. Each sub-stage generates a focused set of files. This improves reliability by splitting the two largest generated files (1,199 + 1,448 lines) across separate stages with a validation checkpoint between them.

| Sub-stage | `sub_stage` value | Files generated | Depends on |
|-----------|-------------------|-----------------|------------|
| RDA-1 | `Schema` | `output/ciq-generators/rhoso_ciq_schema.py` (~1,200 lines — 18 tables, 203 params, 38 validators) | Input docs + project artifacts |
| RDA-2 | `Generator` | `output/ciq-generators/generate_rhoso_ciq_workbooks.py` (~1,450 lines — 9 sheets, 14 conditional formatting rules, 20 dropdowns) + `output/ciq-generators/requirements.txt` | RDA-1 (reads schema from `output/ciq-generators/rhoso_ciq_schema.py`) |
| RDA-3 | `Workbooks` | `output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx` + `output/ciq-workbooks/rhoso/rhoso-ciq-template.xlsx` | RDA-2 (executes the generator script — **no LLM needed**, shell command only) |

When a `sub_stage` is specified, generate ONLY that stage's files:
- **`Schema`** — Write `rhoso_ciq_schema.py` only. Verify: 18 tables, 203+ params, `SCHEMA_VERSION = "1.4"`.
- **`Generator`** — Read the schema from RDA-1 output, then write `generate_rhoso_ciq_workbooks.py` + `requirements.txt`. Do NOT execute the generator.
- **`Workbooks`** — Execute: `pip install openpyxl && python output/ciq-generators/generate_rhoso_ciq_workbooks.py`. Verify `.xlsx` files exist. This stage requires NO LLM — it is a pure shell execution step.

When no `sub_stage` is specified (direct user request), generate all artifacts sequentially (schema → generator → execute → workbooks).

## Process
1. **Load Context** — Read `@context/team-config.yaml` for domain and glossary. Load glossary-cloud if available.
2. **Check sub_stage** — If the orchestrator specifies a `sub_stage`, generate ONLY that artifact. Otherwise generate all artifacts.
3. **Analyze Source** — Extract CIQ parameters, EDPM topology choices, network definitions, node inventory, disconnected flags from `input/rhoso/docs/` (RHOSO PDFs), `input/rhoso/project-artifacts/` (deployment YAMLs / HLD documents), and existing schema at `output/cpat/ansible/module_utils/rhoso_ciq_schema.py`.
4. **Determine Artifact Type** — CIQ Schema Code + Workbooks (primary), Project-Specific CIQ, OCP CIQ, Lab Requirements, or Reference Docs.
5. **Generate CIQ Schema Code** (sub_stage=Schema or no sub_stage) — Write `rhoso_ciq_schema.py` to `output/ciq-generators/`. This is the single source of truth for all CIQ parameters. Include `CIQ_TYPES`, `RHOSO_PARAMETER_SCHEMA`, `RHOSO_NETWORK_FIELD_SCHEMA`, `RHOSO_NODE_FIELD_SCHEMA`, `SCHEMA_VERSION`, and `get_validation_schema()`.
6. **Generate CIQ Workbook Generator** (sub_stage=Generator or no sub_stage) — Read the schema from `output/ciq-generators/rhoso_ciq_schema.py`. Write `generate_rhoso_ciq_workbooks.py` + `requirements.txt` to `output/ciq-generators/`.
7. **Generate CIQ Workbooks** (sub_stage=Workbooks or no sub_stage) — Execute: `python output/ciq-generators/generate_rhoso_ciq_workbooks.py`. This produces `output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx` + `output/ciq-workbooks/rhoso/rhoso-ciq-template.xlsx`.
8. **Project-Specific CIQ Generation** — If project artifacts exist in `input/rhoso/project-artifacts/<project>/`:
   - Parse deployment artifacts (NetConfig, NNCP, ControlPlane CR, NodeSet, BMH, MetalLB, NMState secrets, ConfigMaps) or HLD documents
   - Write `generate_<project>_rhoso_ciq.py` to `output/ciq-generators/`
   - Generate one CIQ workbook per cluster to `output/ciq-workbooks/rhoso/`
   - Reference: existing generators `output/ciq-generators/generate_jio_rhoso_ciq.py`, `output/ciq-generators/generate_core42_rhoso_ciq.py`
9. **OCP CIQ Generation** — If OCP docs exist in `input/ocp/docs/`: write `generate_ocp_ciq_workbooks.py` to `output/ciq-generators/`. Output to `output/ciq-workbooks/ocp/`.
10. **Lab Requirements** — If requested: write `generate_lab_requirements_workbook.py` to `output/lab-requirements/`.
11. **Reference Documents** — Write to `output/pipeline-reports/rda/`: CIQ parameter reference, EDPM topology guide, PDF gap matrix, registration inputs reference.
12. **Quality Summary** — Report tables covered, parameters, files generated (with full paths), gaps found
13. **Gate Checkpoint** — If gates enabled per `00-sprintweave-gates.md`

## CIQ Schema v1.4 (18 tables, 210+ parameters)

The RHOSO CIQ schema v1.4 has 16 parameter tables + 2 row tables (networks, nodes). The schema uses a flat `list[dict]` structure with `_param()` helper (each entry has a `table` field). Version format is `X.Y` (e.g. 1.4).

| Table | Params | Key Content |
|-------|--------|-------------|
| `rhoso_details` | 11 | Cluster Name, Type, Environment, RHOSO/RHOCP Version, Deployment Mode, Multi-Env, Namespaces, FIPS Enabled, Description |
| `rhoso_access` | 3 | Kubeconfig Path, RHOCP API URL, Pull Secret Path |
| `rhoso_disconnected` | 16 | Mirror Registry URL/CA/Pull Secret, IDMS/ITMS/ICSP Names, Disable Default CatalogSources, CatalogSource Name/NS/Image, Operator Source/NS, Mirrored Registry Path, DP Container Registry, DP YUM Mirror, Satellite |
| `rhoso_storage` | 2 | Storage Class, Storage Backend |
| `rhoso_ceph_storage` | 12 | Ceph External, Cluster Name, FSID, Mon Host, Client Name, Client Key Path, Pool Volumes/Images/VMs, RGW Enabled/Endpoint/TLS |
| `rhoso_trident_storage` | 12 | Trident Enabled, Image Registry, Trident Image, Autosupport Image, Backend Name, Storage Driver Name, Management LIF, Data LIF, SVM, Trident Secret Name, Storage Class Name, Volume Binding Mode |
| `rhoso_lso_storage` | 7 | LSO Enabled, Storage Class Name, Device Types, Device Mechanical Properties, Min Device Size, Volume Mode, Node Selector Label |
| `rhoso_control_plane` | 29 | CR Name, FQDN, Public VIP, OSP Secret, Mgmt/InternalAPI Network Names, MetalLB NS, NAD CNI Version, InternalAPI/Cell1-RabbitMQ/RabbitMQ/Glance/Cinder/Neutron/Nova/Placement VIPs, Datacentre NIC, Public Interface, Worker NNCP Interface, OVN Gateway Placement, TLS Pod Level, Operator Channel/Approval, DNS VIP/Upstream/Worker DNS, Messaging Bus Cluster, Notifications Bus Cluster |
| `rhoso_services` | 44 | Per-service enable flags (Keystone, Glance, Cinder, Neutron, Nova, Heat, Horizon, Barbican, Octavia, Designate, Ironic, Manila, Watcher, Telemetry, OVN, DNS), HA Operator enable flags (Node Health Check, Self Node Remediation, Fence Agents Remediation), Prerequisite Operator flags (LSO Enabled, Observability Enabled, Trident Enabled), per-service replicas, Glance backend, RabbitMQ replicas/CPU/memory limits |
| `rhoso_observability` | 5 | Cluster Observability Enabled, Operator Channel, Install Plan Approval, Monitoring Stack Enabled, Monitoring Stack Name |
| `rhoso_pv_sizing` | 10 | Galera storage/class, OVN NB/SB storage/class, Glance PV storage/class, Telemetry storage/retention/storageClass, RabbitMQ CPU/Memory limits |
| `rhoso_cinder_backend` | 8 | NetApp driver, protocol, hostname, vserver, NFS shares config, secret name, network attachment, custom storage config |
| `rhoso_multipath` | 4 | Multipath Enabled, Multipath Config Secret Name, User Friendly Names, Find Multipaths |
| `rhoso_neutron_config` | 5 | Global MTU, API timeout, OVN emit-need-to-frag, MAC Binding Age Threshold, custom service config |
| `rhoso_edpm_network_config` | 24 | Physical Bridge, Topology, Nmstate, Update, Bridge Type, NIC1/NIC2, Bond Name, Bonding Options, Use DHCP/DHCPv6, DPDK MTU/RX Queue/OVS Extra, NTP Servers, Registry Secret, OVN Bridge Mappings, Tuned Profile, Kernel Args, CPU Dedicated Set, Reserved Host Memory MB, Initial CPU Allocation Ratio, SSHD Allowed Ranges, Bootstrap Command |
| `rhoso_data_plane` | 14 | NodeSet Name, Deployment Name, Provisioning Mode, SSH User, SSH Key Path, AE Image, SSH/Nova Migration/Subscription/Libvirt Secret Names, Subscription Method, Org ID, Activation Key, RH Username |
| `rhoso_networks` | 16 cols | Network Name, CIDR, VLAN, Gateway, MTU, Purpose, DNS Domain, Subnet Name, Allocation Start/End, Whereabouts Start/End, MetalLB Start/End, NAD Master Interface, NAD Type |
| `rhoso_data_plane_nodes` | 16 cols | Node Name, Ansible Host, Role, Management IP, NIC1/NIC2 MAC, NUMA Topology, CPU Pinning, BMC Address, Boot MAC, BMH Namespace, Root Device Hint, Boot Mode, Provisioning NIC, Provisioning VLAN, Provisioning IP |

### New in v1.4 (vs v1.3)

| Table | Parameter | Source |
|-------|-----------|--------|
| `rhoso_trident_storage` | 12 new params (entire table) | JIO project artifacts: `D1.3_NetApp/Trident-configuration.txt`, TridentBackendConfig, TridentOrchestrator |
| `rhoso_lso_storage` | 7 new params (entire table) | JIO project artifacts: `D0.6_LSO/` — LocalVolumeDiscovery, LocalVolumeSet, Subscription |
| `rhoso_observability` | 5 new params (entire table) | JIO project artifacts: `D0.5_ObservabilityOperator/` — Cluster Observability Operator |
| `rhoso_multipath` | 4 new params (entire table) | JIO project artifacts: `D1.3_NetApp/multi-path-config.conf` — iSCSI/FC multipath |
| `rhoso_services` | LSO Enabled | JIO: D0.6_LSO prerequisite operator |
| `rhoso_services` | Observability Enabled | JIO: D0.5_ObservabilityOperator prerequisite |
| `rhoso_services` | Trident Enabled | JIO: D1.3_NetApp Trident CSI storage |

### New in v1.3 (vs v1.2)

| Table | Parameter | Source |
|-------|-----------|--------|
| `rhoso_details` | FIPS Enabled | Plan PDF: FIPS 140-3 compliance |
| `rhoso_ceph_storage` | 12 new params (entire table) | Plan + Install PDF: Ceph integration |
| `rhoso_control_plane` | Messaging Bus Cluster | Install PDF: messagingBus config |
| `rhoso_control_plane` | Notifications Bus Cluster | Install PDF: notificationsBus config |
| `rhoso_services` | Watcher Enabled | Install PDF: Optimize service (18.0) |
| `rhoso_services` | Node Health Check Operator Enabled | Plan PDF: HA operators |
| `rhoso_services` | Self Node Remediation Operator Enabled | Plan PDF: HA operators |
| `rhoso_services` | Fence Agents Remediation Operator Enabled | Plan PDF: HA operators |
| `rhoso_neutron_config` | MAC Binding Age Threshold | Install PDF: known issue workaround |

## CIQ Workbook Structure (Multi-Sheet, v1.4)

The generated workbook has **9 sheets** in this exact order:

| # | Sheet | Type | Content |
|---|-------|------|---------|
| 1 | **Versioning** | Metadata | Workbook title, sheet index, version history (X.Y format) |
| 2 | **Environment** | CIQ | `rhoso_details`, `rhoso_access`, `rhoso_disconnected` tables |
| 3 | **Storage** | CIQ | `rhoso_storage`, `rhoso_ceph_storage`, `rhoso_trident_storage`, `rhoso_lso_storage`, `rhoso_cinder_backend`, `rhoso_multipath` tables |
| 4 | **Control Plane** | CIQ | `rhoso_control_plane`, `rhoso_services`, `rhoso_observability`, `rhoso_pv_sizing`, `rhoso_neutron_config` tables |
| 5 | **Networks** | CIQ | `rhoso_networks` multi-row table (16 columns) |
| 6 | **Data Plane** | CIQ | `rhoso_edpm_network_config`, `rhoso_data_plane` tables + `rhoso_data_plane_nodes` multi-row table |
| 7 | **values** | Hidden | Dropdown list sources for data validation |
| 8 | **Guidelines** | Reference | Full parameter catalog with "Use when:" guidance for all optional params |
| 9 | **Operators** | Reference | Prerequisite operator list with enable flags, channels, namespaces |

Sheet grouping is defined by `SHEET_GROUPS` in the generator:
```python
SHEET_GROUPS: list[tuple[str, list[str], bool, bool]] = [
    # (sheet_name, table_keys, include_networks, include_nodes)
    ("Environment", ["rhoso_details", "rhoso_access", "rhoso_disconnected"], False, False),
    ("Storage", ["rhoso_storage", "rhoso_ceph_storage", "rhoso_trident_storage", "rhoso_lso_storage", "rhoso_cinder_backend", "rhoso_multipath"], False, False),
    ("Control Plane", ["rhoso_control_plane", "rhoso_services", "rhoso_observability", "rhoso_pv_sizing", "rhoso_neutron_config"], False, False),
    ("Networks", [], True, False),
    ("Data Plane", ["rhoso_edpm_network_config", "rhoso_data_plane"], False, True),
]
```

## CIQ Workbook Features

### Versioning Sheet
- Title: "CPAT — RHOSO CIQ Workbook"
- Sheets reference table listing all 8 sheets with descriptions
- Version history table with X.Y format (1.0, 1.1, 1.2, 1.3 …) + 5 blank rows for future entries
- Generated by `_write_versioning_sheet()`

### CIQ Data Sheets (Environment, Storage, Control Plane, Networks, Data Plane)
- Each CIQ sheet has columns: **Parameter**, **Value**, **Type**, **Required**, **When**, **Description**
- Parameter tables rendered as **Excel Named Tables** for CPAT parser compatibility
- Color-coded section header rows with distinct fills per table
- **Dropdowns** — all enum-type fields have Excel data validation lists referencing the hidden values sheet
- **Table headers** — all UPPERCASE in Excel; parser normalizes back to canonical mixed-case via `_normalize_header()` (handles acronyms like MAC, NIC1, NIC2, BMC, BMH, VLAN, CIDR, DPDK, MTU)
- Generated by `_write_ciq_sheet()` called from `_write_all_ciq_sheets()`

### Values Sheet (Hidden)
- `sheet_state = 'hidden'`
- Provides dropdown source lists for all enum-type fields
- Dropdown lists include: StorageBackend (NetApp ONTAP FC/iSCSI/NFS, LVM, Ceph, NFS), GlanceBackend, CinderStorageProtocol, BootMode, InstallPlanApproval, TunedProfile, EDPM Topology, Subscription Method, Deployment Mode, OVN Gateway Placement, etc.

### Conditional Formatting (14 rules, 74+ parameters)
Auto-greys-out irrelevant parameter rows/columns based on user selections. Generated by `_apply_conditional_formatting()`:

| # | Rule | Trigger | Greyed-Out Parameters |
|---|------|---------|-----------------------|
| 1 | Disconnected table | Deployment Mode = connected | All 16 `rhoso_disconnected` params |
| 2 | Bond fields | EDPM Topology ≠ bond type | EDPM NIC2, Bond Name, Bonding Options |
| 3 | DPDK fields | EDPM Topology ≠ ovs_dpdk | DPDK MTU, DPDK RX Queue, DPDK OVS Extra |
| 4 | Activation Key | Subscription ≠ activation_key | Org ID, Activation Key |
| 5 | Username/Password | Subscription ≠ username_password | RH Username |
| 6 | Ceph Storage | Ceph External ≠ yes | All 11 Ceph sub-params (Cluster, FSID, Mon, Client, Pools, RGW) |
| 7 | Ceph RGW | Ceph RGW Enabled ≠ yes | RGW Endpoint, RGW TLS Enabled |
| 8 | Horizon | Horizon Enabled ≠ yes | Horizon Replicas |
| 9 | Heat | Heat Enabled ≠ yes | Heat API/Engine Replicas |
| 10 | Barbican | Barbican Enabled ≠ yes | Barbican API/Worker Replicas |
| 11 | Telemetry | Telemetry Enabled ≠ yes | Telemetry Storage/Class/Retention/Scrape |
| 12 | Nova Metadata | Nova Metadata Enabled ≠ yes | Nova Cell1 Metadata Replicas |
| 13 | Unprovisioned cols | DP Mode ≠ unprovisioned | BMC, Boot MAC, BMH NS, Root Device, Boot Mode, Provisioning NIC/VLAN/IP columns |
| 14 | Pre-provisioned cols | DP Mode ≠ pre-provisioned | Ansible Host, Management IP columns |

### Guidelines Sheet (last sheet)
- Title: "CPAT - RHOSO DEPLOYMENT INPUT FILE FIELD GUIDELINES"
- Maps every parameter/network-field/node-field to: Table, Type, Required, When, Description
- All 119 optional parameters (`required=No`, `when=always`) include detailed **"Use when:"** guidance and supported values
- Purpose descriptions managed by `PARAM_PURPOSE_MAP`, `NETWORK_FIELD_PURPOSE_MAP`, `NODE_FIELD_PURPOSE_MAP` in the generator
- Generated by `_write_field_guide()`

## Unified CIQ Parser

CPAT uses a single unified parser (`ciq_parser.py`) that handles both RHOSO and OCP:
- `output/cpat/ansible/module_utils/ciq_parser.py` — Ansible copy (imported by `library/parse_ciq.py`)
- `output/cpat/backend/ciq_parser.py` — Backend copy (imported by `app.py`, `models.py`)

The unified parser auto-detects cluster type from Excel table names (`rhoso_details` → RHOSO, `ocp_details` → OCP) and:
1. Searches across **all sheets** for parameter tables and row tables
2. Merges supplemental parameter tables for the detected cluster type
3. Collects row table data (RHOSO: networks, nodes; OCP: bmc_hosts, nmstate, compute, dns)
4. Returns `CiqParseBatchResult` — can contain both RHOSO and OCP from a combined workbook
5. Backward-compatible properties: `.nodes`, `.networks`, `.bmc_hosts`, `.nmstate_interfaces`, etc.

## EDPM Required-When Matrix (24 parameters)

| Parameter | Required When |
|-----------|--------------|
| Physical Bridge Name | Always |
| EDPM Network Config Topology | Always |
| EDPM Network Config Nmstate | Always |
| EDPM Network Config Update | Always |
| EDPM Bridge Type | Always |
| EDPM NIC1 Name | Always |
| EDPM NIC2 Name | When topology = dual_nic_bond, ovs_bond, linux_bond |
| EDPM Bond Name | When topology = dual_nic_bond, ovs_bond, linux_bond |
| EDPM Bonding Options | When topology = dual_nic_bond, ovs_bond, linux_bond (optional) |
| EDPM Use DHCP | Always |
| EDPM Use DHCPv6 | Always |
| EDPM DPDK MTU | When topology = ovs_dpdk |
| EDPM DPDK RX Queue | When topology = ovs_dpdk (optional) |
| EDPM DPDK OVS Extra | When topology = ovs_dpdk (optional) |
| NTP Servers | Optional |
| Registry Secret Name | Optional |
| EDPM OVN Bridge Mappings | Optional (default: datacentre:br-ex) |
| EDPM Tuned Profile | Optional (e.g., cpu-partitioning) |
| EDPM Kernel Args | Optional (e.g., hugepages, iommu) |
| EDPM CPU Dedicated Set | Optional — triggers Nova CPU pinning ConfigMap generation |
| EDPM Reserved Host Memory MB | Optional (with CPU Dedicated Set) |
| EDPM Initial CPU Allocation Ratio | Optional (with CPU Dedicated Set) |
| EDPM SSHD Allowed Ranges | Optional |
| EDPM Bootstrap Command | Optional (overrides default subscription commands) |

## Node Fields (16 columns)

| Column | Type | Required When |
|--------|------|---------------|
| Node Name | dns_label | Always |
| Ansible Host | host_or_ip | When Provisioning Mode = pre-provisioned |
| Role | enum_dp_role | Always |
| Management IP | ipv4 | When Provisioning Mode = pre-provisioned |
| NIC1 MAC | mac | Optional |
| NIC2 MAC | mac | Optional |
| NUMA Topology | enum_numa | Optional |
| CPU Pinning | enum_cpu_pinning | Optional |
| BMC Address | bmc_address | When Provisioning Mode = unprovisioned |
| Boot MAC Address | mac | When Provisioning Mode = unprovisioned |
| BMH Namespace | k8s_name | When Provisioning Mode = unprovisioned (optional) |
| Root Device Hint | device_path | When Provisioning Mode = unprovisioned (optional) |
| Boot Mode | enum_boot_mode | When Provisioning Mode = unprovisioned (optional) |
| Provisioning NIC | iface | When Provisioning Mode = unprovisioned (optional) |
| Provisioning VLAN | vlan | When Provisioning Mode = unprovisioned (optional) |
| Provisioning IP | ipv4 | When Provisioning Mode = unprovisioned (optional) |

## Project-Specific CIQ Generators (existing — all under `output/ciq-generators/`)

| Generator Script | Project | Clusters | Source |
|-----------------|---------|----------|--------|
| `generate_rhoso_ciq_workbooks.py` | Generic | sample + template | CIQ schema |
| `generate_jio_rhoso_ciq.py` | JIO | cloudmgmt, cloudxp | `input/rhoso/project-artifacts/jio/` |
| `generate_core42_rhoso_ciq.py` | Core42 | core42-rhoso | `input/rhoso/project-artifacts/core42/` |
| `generate_ocp_ciq_workbooks.py` | OCP 4.17 | sample + template | `input/ocp/docs/` |

## Schema Sync Points (MUST keep in sync)

When modifying the CIQ schema, the following files MUST all be updated:

| File | Role |
|------|------|
| `output/ciq-generators/rhoso_ciq_schema.py` | **MASTER** — standalone schema used by generator |
| `output/cpat/ansible/module_utils/rhoso_ciq_schema.py` | Ansible module copy |
| `output/cpat/backend/rhoso_ciq_schema.py` | Backend copy |
| `output/cpat/ansible/module_utils/ciq_parser.py` | Unified CIQ parser — Ansible copy (SUPPLEMENTAL_TABLES, ROW_TABLES) |
| `output/cpat/backend/ciq_parser.py` | Unified CIQ parser — Backend copy (same file) |
| `output/ciq-generators/generate_rhoso_ciq_workbooks.py` | Workbook generator (SHEET_GROUPS, DROPDOWN_LISTS, PARAM_PURPOSE_MAP, conditional formatting rules) |

> **NOTE:** New RHOSO tables must be added to `SUPPLEMENTAL_TABLES["rhoso"]` in `ciq_parser.py`.
> New RHOSO row tables must be added to `ROW_TABLES` in `ciq_parser.py`.

## Rules
- CIQ workbook generation requires openpyxl (`pip install openpyxl`)
- HLD document parsing requires python-docx (`pip install python-docx`)
- Schema version format is `X.Y` (e.g. "1.4") — NOT semver
- Every new CIQ parameter MUST have: type (from CIQ_TYPES), required flag, required-when condition
- Every new parameter MUST be added to ALL THREE copies of `rhoso_ciq_schema.py` AND to the parser's `RHOSO_SUPPLEMENTAL_PARAM_TABLES`
- Every new parameter MUST have a `PARAM_PURPOSE_MAP` entry in the generator with "Use when:" guidance for optional params
- Every new conditional dependency (e.g. "show only when X = yes") MUST be added to `_apply_conditional_formatting()`
- New tables MUST be assigned to the correct `SHEET_GROUPS` entry or a new sheet group must be created
- Every new input file MUST be added to BOTH `output/cpat/backend/input_files.py` AND `output/cpat/frontend/src/rhosoInputFiles.js`
- Workbook generator table names must match schema table names exactly
- NEVER invent CIQ parameters not in `rhoso_ciq_schema.py` or `USAGE.md`
- NEVER propose a new CIQ field without a matching Ansible consumer in CPAT
- EDPM host networking is CIQ-driven ONLY — no EDPM Jinja upload; allowed topologies: `single_nic_vlans | dual_nic_bond | ovs_bond | linux_bond | ovs_dpdk`
- NEVER include actual secrets or passwords — use path references only
- ALWAYS cite the source (schema field, USAGE section, or RHOSO PDF chapter) for every parameter
- Bond fields (NIC2, Bond Name, Bonding Options) required when topology = dual_nic_bond, ovs_bond, linux_bond
- DPDK fields (MTU, RX Queue, OVS Extra) required when topology = ovs_dpdk
- Disconnected fields required when Deployment Mode is `disconnected | airgapped | offline`
- Project-specific CIQ generators: one CIQ workbook per cluster, use `_build_cluster_workbook()` pattern
- When extracting from YAML artifacts: parse NetConfig, NNCP, ControlPlane CR, NodeSet, BMH, MetalLB, NMState Secrets, ConfigMaps
- When extracting from HLD documents: use python-docx for .docx, Read tool for .pdf
- Excel headers are UPPERCASE; parsers use `_normalize_header()` with `_CANONICAL_HEADER_WORDS` to restore canonical mixed-case (MAC, NIC1, NIC2, BMC, BMH, VLAN, CIDR, DPDK, MTU, etc.)
- Guidelines sheet maps every parameter to its purpose description via `PARAM_PURPOSE_MAP`, `NETWORK_FIELD_PURPOSE_MAP`, `NODE_FIELD_PURPOSE_MAP`
- Values sheet is hidden (`sheet_state = 'hidden'`); enum dropdowns include NetApp, LVM, GlanceBackend, CinderStorageProtocol, BootMode, InstallPlanApproval, TunedProfile
- Flag gaps vs RHOSO PDFs: `[GAP: documented in PDF but not in CPAT CIQ — needs Ansible consumer]`
- When CIQ is complete, handoff to **RHOSO Deployment Engineer** for manifest generation
