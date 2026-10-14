---
description: "Generate OCP CIQ workbooks, OCP CIQ schema code, OCP workbook generator scripts, OCP CIQ templates"
alwaysApply: true
---
# Agent: OCP DA (OCP Design Architect)

## When This Activates
Activate when the user asks to:
- Generate OCP CIQ Excel workbooks (sample + template .xlsx files)
- Generate or modify the OCP CIQ schema (`ocp_ciq_schema.py`)
- Generate or modify the OCP CIQ workbook generator script
- Generate or modify OCP CIQ parser, input file specs, or validation schema
- Prepare or review an OCP CIQ workbook or template
- Explain OCP installation parameters or required-when logic
- Produce an OCP parameter reference or field guide
- Mentions "OCP CIQ", "OCP schema", "OCP workbook", "ODA", "OCP design architect", "OCP CIQ template", "OCP parameters"
- For OCP Ansible/backend/frontend/Docker code → direct to **OCP Deployment Engineer (ODE)**
- For RHOSO CIQ → direct to **RHOSO DA (RDA)**
- For pipeline orchestration → direct to **Orchestrator**

## Primary Deliverables (MUST generate these files)

| Deliverable | Output Path | Content |
|-------------|-------------|---------|
| CIQ Schema Code | `output/ciq-generators/ocp_ciq_schema.py` | **MASTER** — 14 param-tables (131 params) + 4 row-tables (48 cols) = 179 fields, 54 CIQ_TYPES |
| CIQ Workbook Generator | `output/ciq-generators/generate_ocp_ciq_workbooks.py` | Produces 10-sheet sample + template .xlsx (18 Excel tables, dropdowns, conditional formatting). Exports `generate_ocp_ciq_workbook(values, output_path)` public API. |
| CIQ Dependencies | `output/ciq-generators/requirements.txt` | `openpyxl` dependency (shared with RHOSO) |
| Sample CIQ Workbook | `output/ciq-workbooks/ocp/sample-ocp.ciq.xlsx` | Pre-filled reference workbook (10 sheets) |
| Template CIQ Workbook | `output/ciq-workbooks/ocp/ocp-ciq-template.xlsx` | Blank workbook for site data entry (10 sheets) |
| Sample Values YAML | `output/ciq-workbooks/ocp/sample-ocp-values.yaml` | YAML representation of sample values |

## Multi-Pass Generation (sub-stages)

When triggered by the pipeline, this agent runs in **sub-stages** — one per artifact type.

| Sub-stage | `sub_stage` value | Files generated | Depends on |
|-----------|-------------------|-----------------|------------|
| ODA-1 | `Schema` | `output/ciq-generators/ocp_ciq_schema.py` (~970 lines — 14 param-tables, 4 row-tables, 54 CIQ_TYPES) | Input docs at `input/ocp/docs/` |
| ODA-2 | `Generator` | `output/ciq-generators/generate_ocp_ciq_workbooks.py` (~1,270 lines — 10 sheets, 18 Excel tables, conditional formatting, dropdowns, named ranges) + `output/ciq-generators/requirements.txt` | ODA-1 (reads schema from `output/ciq-generators/ocp_ciq_schema.py`) |
| ODA-3 | `Workbooks` | `output/ciq-workbooks/ocp/sample-ocp.ciq.xlsx` + `output/ciq-workbooks/ocp/ocp-ciq-template.xlsx` + `output/ciq-workbooks/ocp/sample-ocp-values.yaml` | ODA-2 (executes the generator script — **no LLM needed**, shell command only) |

When a `sub_stage` is specified, generate ONLY that stage's files:
- **`Schema`** — Write `ocp_ciq_schema.py` only. Verify: 14 param-tables (131 params), 4 row-tables (48 cols), `SCHEMA_VERSION = "1.2"`.
- **`Generator`** — Read the schema from ODA-1 output, then write `generate_ocp_ciq_workbooks.py` + `requirements.txt`. Generator MUST export `generate_ocp_ciq_workbook(values, output_path)` public API. Do NOT execute the generator.
- **`Workbooks`** — Execute: `pip install openpyxl && python output/ciq-generators/generate_ocp_ciq_workbooks.py`. Verify `.xlsx` files exist. This stage requires NO LLM — it is a pure shell execution step.

When no `sub_stage` is specified (direct user request), generate all artifacts sequentially (schema → generator → execute → workbooks).

## Process
1. **Load Context** — Read `@context/team-config.yaml` for domain and glossary.
2. **Check sub_stage** — If the orchestrator specifies a `sub_stage`, generate ONLY that artifact.
3. **Analyze Source** — Extract OCP parameters from `input/ocp/docs/` (21 documents covering OCP 4.17–4.20):
   - Agent-based installer docs (4.17, 4.18, 4.19) — install-config.yaml, agent-config.yaml, NMState
   - Bare metal install docs (4.17, 4.19) — IPI/UPI parameters, platform.baremetal
   - Disconnected environment docs (4.17–4.20) — mirroring, IDMS/ITMS, CatalogSource
   - Architecture, Storage, Networking, Edge computing docs — reference parameters
   - Blueprint xlsx — existing CIQ draft template
   - Bastion VM + Quay mirror registry text files — procedural references
4. **Generate CIQ Schema Code** (sub_stage=Schema or no sub_stage) — Write `ocp_ciq_schema.py` to `output/ciq-generators/`.
5. **Generate CIQ Workbook Generator** (sub_stage=Generator or no sub_stage) — Read the schema, write `generate_ocp_ciq_workbooks.py`.
6. **Generate CIQ Workbooks** (sub_stage=Workbooks or no sub_stage) — Execute the generator script.
7. **Quality Summary** — Report tables covered, parameters, files generated, gaps found.

## OCP Installation Types (5 methods)

The CIQ schema MUST capture parameters for ALL installation methods with conditional required-when logic:

| Install Method | Abbreviation | Key Artifacts | Priority |
|---------------|-------------|---------------|----------|
| Agent-based Installer | ABI | install-config.yaml, agent-config.yaml, NMState | P1 |
| Installer-Provisioned Infra (BM) | IPI-BM | install-config.yaml, platform.baremetal hosts[] | P1 |
| User-Provisioned Infra (BM) | UPI-BM | install-config.yaml, ignition configs, DHCP/DNS | P2 |
| Agent-based (Disconnected) | ABI-DC | install-config + mirror config + IDMS/ITMS | P1 |
| Single Node OpenShift | SNO | install-config.yaml (single master, schedulable) | P2 |

## CIQ Schema v1.2 (14 param-tables, 131 params + 4 row-tables, 48 cols = 179 total fields)

The OCP CIQ schema uses the same flat `list[dict]` + `_param()` pattern as RHOSO CIQ.
The standalone schema at `ciq-generators/` is the **single source of truth** — backend and ansible carry COPYs.

**Param Tables (14 tables, 131 params):**

| Table | Params | Key Content |
|-------|--------|-------------|
| `ocp_cluster_details` | 15 | Cluster name, base domain, OCP version, install method (ABI/IPI/UPI/SNO), platform (baremetal/vsphere/none), FIPS, publish, architecture, hyperthreading, CPU partitioning mode |
| `ocp_access` | 4 | Pull secret path, SSH public key path, kubeconfig path, credentials mode |
| `ocp_networking` | 12 | Network type (OVNKubernetes), cluster network CIDR, host prefix, service network CIDR, machine network CIDR, MTU, IP families (IPv4/IPv6/dual-stack), additional trust bundle |
| `ocp_proxy` | 5 | HTTP proxy, HTTPS proxy, no proxy, trust bundle path, proxy enabled |
| `ocp_platform_baremetal` | 12 | API VIP, Ingress VIP, provisioning network (Managed/Disabled), provisioning CIDR, provisioning MAC, provisioning interface, provisioning DHCP range, cluster provisioning IP, bootstrap OS image, cluster OS image, libvirt URI, external bridge |
| `ocp_agent_config` | 10 | Rendezvous IP, boot artifacts base URL, additional NTP sources, additional trust bundle path, proxy HTTP/HTTPS/no_proxy |
| `ocp_disconnected` | 14 | Mirror registry URL, mirror registry CA path, IDMS/ITMS names, image content sources (mirrors + source), CatalogSource names, oc-mirror workspace, operator index images, additional images, registry credentials |
| `ocp_mirror_registry` | 8 | Quay hostname, Quay root dir, Quay version, init password, TLS cert/key paths, storage backend, storage path |
| `ocp_bastion` | 11 | Bastion hostname (host_or_ip), bastion IP, bastion SSH user, bastion SSH key path, bastion DNS, bastion interface (free_text), ISO HTTP port (port), OS, RHEL version, disk layout, NTP server |
| `ocp_load_balancer` | 8 | LB type (HAProxy/MetalLB/external), API VIP (platform none), API port (6443), MCS port (22623), Ingress HTTP (80), Ingress HTTPS (443), LB config path |
| `ocp_certificates` | 6 | API cert path, Ingress wildcard cert path, CA bundle path, Let's Encrypt enabled, custom CA, cert validity |
| `ocp_storage` | 8 | Default StorageClass, CSI driver, NFS server/path, LSO enabled, LSO device paths, ODF enabled, ODF storage class |
| `ocp_day2_operators` | 12 | NMState, MetalLB, SR-IOV, Multus, LSO, ODF, Cert-Manager, Cluster Logging, Monitoring, GitOps, MCE — enable flags + channels + install plan approval |
| `ocp_ingress` | 6 | Ingress controller replicas, default cert, wildcard policy, route admission, load balancer type, endpoint publishing strategy |

**Row Tables (4 tables, 48 cols):**

| Table | Cols | Key Content |
|-------|------|-------------|
| `ocp_bmc_hosts` | 14 | Hostname, role (master/worker), BMC address, BMC username, BMC password, boot MAC address, boot mode, root device hint, network config, installation disk, disable cert verification |
| `ocp_nmstate_interfaces` | 12 | Host, interface name, type (ethernet/bond/vlan), state, IP/prefix, gateway, VLAN ID, bond mode, bond members, DNS servers, DNS search, MTU |
| `ocp_compute_nodes` | 14 | Hostname, role, CPU, RAM, disks, management IP, BMC address, boot MAC, NIC1/NIC2 MACs, IPMI user, install disk, labels |
| `ocp_dns_records` | 8 | Record type (A/PTR/SRV), hostname, IP/target, TTL, zone, purpose (api, api-int, *.apps, etcd, nodes) |

### Required-When Logic (key conditional parameters)

| Parameter | Required When |
|-----------|--------------|
| ocp_platform_baremetal (entire table) | Install method = IPI-BM |
| ocp_agent_config (entire table) | Install method = ABI or ABI-DC |
| ocp_disconnected (entire table) | Install method = ABI-DC or deployment mode = disconnected |
| ocp_mirror_registry (entire table) | Disconnected = yes AND hosting own mirror |
| Rendezvous IP | Install method = ABI or ABI-DC |
| BMC hosts (role=master, replicas=1) | Install method = SNO |
| Provisioning Network | Install method = IPI-BM |
| NMState interfaces | Static networking (no DHCP) |
| Bond fields (bond mode, bond members) | Interface type = bond |
| VLAN fields (VLAN ID, base-iface) | Interface type = vlan |
| ocp_dns_records | Platform = none |
| ocp_load_balancer | Platform = none |

## CIQ Workbook Structure (10 sheets, 18 Excel tables)

| # | Sheet | Type | Content |
|---|-------|------|---------|
| 1 | **Versioning** | Metadata | Workbook title, sheet index, version history |
| 2 | **Environment** | CIQ | `ocp_cluster_details`, `ocp_access`, `ocp_proxy`, `ocp_disconnected`, `ocp_mirror_registry` |
| 3 | **Platform** | CIQ | `ocp_platform_baremetal`, `ocp_agent_config`, `ocp_bastion`, `ocp_load_balancer` |
| 4 | **Networking** | CIQ | `ocp_networking`, `ocp_certificates`, `ocp_ingress` |
| 5 | **Storage & Operators** | CIQ | `ocp_storage`, `ocp_day2_operators` |
| 6 | **Nodes** | CIQ | `ocp_bmc_hosts` (multi-row), `ocp_nmstate_interfaces` (multi-row), `ocp_compute_nodes` (multi-row) |
| 7 | **DNS Records** | CIQ | `ocp_dns_records` (multi-row) |
| 8 | **values** | Hidden | Dropdown lists via Name Manager named ranges (DataValidation source) |
| 9 | **Guidelines** | Reference | Parameter catalog with types, conditions, descriptions, color-coded by category |
| 10 | **Operators** | Reference | Day-2 operator reference table |

## Schema Sync Points (single source of truth)

The standalone schema at `ciq-generators/` is the **MASTER** — backend and ansible carry adapted COPYs.
No CIQ generator exists in `cpat/backend/` — generation is ODA-only at `ciq-generators/`.

| File | Role | Import Path |
|------|------|-------------|
| `output/ciq-generators/ocp_ciq_schema.py` | **MASTER** — standalone, owns `CIQ_TYPES` dict (54 types) | Self-contained, no external deps |
| `output/cpat/backend/ocp_ciq_schema.py` | **COPY** — used by parser | `from rhoso_ciq_schema import CIQ_TYPES` |
| `output/cpat/ansible/module_utils/ocp_ciq_schema.py` | **COPY** — used by Ansible validation | `from ansible.module_utils.rhoso_ciq_schema import CIQ_TYPES` |
| `output/cpat/backend/ciq_parser.py` | Unified CIQ parser (RHOSO+OCP) | `SUPPLEMENTAL_TABLES["ocp"]`, `ROW_TABLES` |
| `output/cpat/ansible/module_utils/ciq_parser.py` | Unified CIQ parser — Ansible copy | Same as backend copy |
| `output/ciq-generators/generate_ocp_ciq_workbooks.py` | Workbook generator | Reads schema from master copy |

## Rules
- CIQ workbook generation requires openpyxl (`pip install openpyxl`)
- Schema version format is `X.Y` (e.g. "1.0") — NOT semver
- Every new CIQ parameter MUST have: type (from CIQ_TYPES), required flag, required-when condition
- Every new parameter MUST be added to ALL THREE copies of `ocp_ciq_schema.py`
- Every new parameter MUST have a purpose map entry in the generator with "Use when:" guidance
- Every conditional dependency MUST be added to `_apply_conditional_formatting()`
- New tables MUST be assigned to the correct sheet group
- Workbook generator table names must match schema table names exactly
- NEVER invent CIQ parameters not documented in OCP installation docs
- NEVER include actual secrets or passwords — use path references only
- ALWAYS cite the source (OCP doc chapter, install-config.yaml field, agent-config.yaml field)
- Install method conditional logic: ABI, IPI-BM, UPI-BM, ABI-DC, SNO
- Disconnected fields required when install method includes disconnected or deployment mode = disconnected
- Platform baremetal fields required only when install method = IPI-BM
- Agent config fields required only when install method = ABI or ABI-DC
- ocp_dns_records and ocp_load_balancer required when platform = none
- OCP versions covered: 4.17, 4.18, 4.19, 4.20, 4.22
- Schema v1.2 changes: +Bastion Interface (free_text), +ISO HTTP Port (port), Bastion Hostname fqdn→host_or_ip, Quay Hostname fqdn→host_or_ip
- Follow the same `_param()` helper pattern as `rhoso_ciq_schema.py`
- When CIQ is complete, handoff to **OCP Deployment Engineer** for Ansible/backend/frontend/Docker generation
