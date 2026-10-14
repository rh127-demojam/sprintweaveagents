# RHOSO DA — Output Template
> This file is loaded on-demand by the RHOSO DA agent during generation.
> Do not edit the structure without updating the slim rule reference.

## CIQ Source of Truth

- Schema: `ansible/module_utils/rhoso_ciq_schema.py` (SCHEMA_VERSION 1.1.0)
- Workbook generator: `CIQTemplates/generate_rhoso_ciq_workbooks.py`
- Operator docs: `USAGE.md`, `CIQTemplates/README.md`
- Red Hat reference PDFs: `RHOSO/` (6 guides for RHOSO 18.0)

## CIQ Tables (9 tables, 82 parameters + 16 network cols + 11 node cols)

The schema uses a flat `list[dict]` structure with `_param()` helper (each entry has a `table` field). 7 parameter tables + 2 row tables.

| Table | Params | Key Content |
|-------|--------|-------------|
| `rhoso_details` | 10 | Cluster Name, Type, Environment, RHOSO/RHOCP Version, Deployment Mode, Multi-Env, Namespaces, Description |
| `rhoso_access` | 3 | Kubeconfig Path, RHOCP API URL, Pull Secret Path |
| `rhoso_disconnected` | 16 | Mirror Registry URL/CA/Pull Secret, IDMS/ITMS/ICSP Names, Disable Default CatalogSources, CatalogSource Name/NS/Image, Operator Source/NS, Mirrored Registry Path, DP Container Registry, DP YUM Mirror, Satellite |
| `rhoso_storage` | 2 | Storage Class, Storage Backend |
| `rhoso_control_plane` | 21 | CR Name, FQDN, Public VIP, OSP Secret, Mgmt/InternalAPI Network Names, MetalLB NS, NAD CNI Version, InternalAPI/Cell1-RabbitMQ/RabbitMQ/Glance/Cinder/Neutron/Nova/Placement VIPs, Datacentre NIC, Public Interface, Worker NNCP Interface, OVN Gateway Placement |
| `rhoso_edpm_network_config` | 16 | Physical Bridge, Topology, Nmstate, Update, Bridge Type, NIC1/NIC2, Bond Name, Bonding Options, Use DHCP/DHCPv6, DPDK MTU/RX Queue/OVS Extra, NTP Servers, Registry Secret |
| `rhoso_data_plane` | 14 | NodeSet Name, Deployment Name, Provisioning Mode, SSH User, SSH Key Path, AE Image, SSH/Nova Migration/Subscription/Libvirt Secret Names, Subscription Method, Org ID, Activation Key, RH Username |
| `rhoso_networks` | 16 cols | Network Name, CIDR, VLAN, Gateway, MTU, Purpose, DNS Domain, Subnet Name, Allocation Start/End, Whereabouts Start/End, MetalLB Start/End, NAD Master Interface, NAD Type |
| `rhoso_data_plane_nodes` | 11 cols | Node Name, Ansible Host, Role, Management IP, NIC1/NIC2 MAC, NUMA Topology, CPU Pinning, BMC Address, Boot MAC, BMH Namespace |

**Note:** Service enable flags, replicas, PV sizing, Cinder backend, and Neutron config parameters are NOT separate schema tables — they are consumed directly from CIQ merged parameters via `_load_ciq_context.yml` in the Ansible role.

## EDPM Required-When Matrix (16 parameters, schema v1.1.0)

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

## EDPM Topologies

| Topology | NICs | Bond | Bridge | Use Case |
|----------|------|------|--------|----------|
| `single_nic_vlans` | 1 | No | ovs_bridge | Lab / simple environments |
| `dual_nic_bond` | 2 | Linux bond | ovs_bridge | Production HA with LACP |
| `ovs_bond` | 2 | OVS bond | ovs_bridge | OVS-managed bonding |
| `linux_bond` | 2 | Linux bond | ovs_bridge | Kernel-level bonding |
| `ovs_dpdk` | 2 | OVS-DPDK bond | ovs_user_bridge | High-performance NFV workloads |

**Rule:** EDPM Jinja is generated from CIQ only. There is no EDPM Jinja template upload. The `custom` topology value was removed; current schema is v1.1.0.

## Registration Input Files

| File | CIQ Parameter | Purpose |
|------|--------------|---------|
| Kubeconfig | `Kubeconfig Path` | RHOCP cluster-admin access |
| Pull Secret | `Pull Secret Path` | Registry authentication JSON |
| SSH Private Key | `Data Plane SSH Private Key Path` | Ansible SSH to data plane nodes |
| Mirror Registry CA | `Mirror Registry CA Path` | CA cert for disconnected mirror (when disconnected) |
| Mirror Pull Secret | `Mirror Pull Secret Path` | Mirror registry auth (when disconnected) |

**No EDPM Jinja upload.** The UI `INPUT_FILE_SPECS` does not include an EDPM template field.

## RHOSO PDF-to-CIQ Gap Matrix (updated after schema extension)

| Gap Category | PDF Source | In CIQ? | Status |
|-------------|-----------|---------|--------|
| Core deployment (operator, namespace, networks, control plane, data plane) | Deploying (97pp) | YES | Covered |
| Disconnected (oc-mirror, CatalogSource, IDMS/ITMS, Satellite) | Disconnected (12pp) | YES | Covered |
| EDPM network config (topology, NIC, bond, DPDK) | Deploying (97pp) | YES | Covered |
| Multi-env flag | Multi-env (35pp) | YES | Covered |
| Service enable/disable (Heat, Horizon, Barbican, Manila, Ironic, Octavia, Designate) | Customizing (70pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| Service replicas (Nova, Neutron, Keystone, Cinder, Barbican, Galera, RabbitMQ, OVN) | Customizing (70pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| PV sizing (Galera, OVN, Telemetry) | Customizing (70pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| RabbitMQ resource limits (CPU, memory) | Customizing (70pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| Cinder backend (NetApp ONTAP FC/iSCSI, PowerFlex) | Persistent Storage (126pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| Glance backend selection (cinder, S3) | Persistent Storage (126pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| Neutron MTU, OVN frag, API timeout | Customizing (70pp) | YES | Consumed via `_load_ciq_context.yml` from merged CIQ params |
| TLS pod-level enablement | Customizing (70pp) | YES | `rhoso_control_plane` table |
| DNS VIP, upstream servers | Customizing (70pp) | YES | `rhoso_control_plane` table |
| EDPM performance tuning (CPU pinning, hugepages, tuned profile) | Deploying (97pp) | YES | **Extended** — `rhoso_edpm_network_config` |
| EDPM custom bootstrap command | Deploying (97pp) | YES | **Extended** — `rhoso_edpm_network_config` |
| BareMetalHost provisioning (rootDeviceHints, bootMode, NMState) | Deploying (97pp) | YES | **Extended** — node fields + NMState template |
| Nova CPU pinning ConfigMap | Customizing (70pp) | YES | **Extended** — new template `openstack_nova_cpu_pinning_cm.yaml.j2` |
| Telemetry storage class, retention, scrape interval | Customizing (70pp) | YES | **Extended** — `rhoso_pv_sizing` table |
| Multi-cell (cell templates, cell-specific VIPs) | Customizing (70pp) | PARTIAL | Cell1 replicas/VIPs in CIQ; multi-cell orchestration not automated |
| Operator resource limits / tolerations | Customizing (70pp) | NO | Low priority — operational |
| Pod placement / Topology CRs | Customizing (70pp) | NO | Only when CPAT adds topology support |
| Image mode (bootc) data plane | Customizing (70pp) | NO | Only when CPAT adds bootc provisioning |
| Proxy config for data plane | Customizing (70pp) | NO | Only when CPAT adds proxy support |
| Ceph pools / monitors / fsid / RBD user | Persistent Storage (126pp) | NO | Only when CPAT adds Ceph templates |
| Swift deployment (PV, external nodes, ring power) | Persistent Storage (126pp) | NO | Only when CPAT adds Swift templates |
| Manila backend configuration (CephFS, CephFS-NFS) | Persistent Storage (126pp) | NO | Only when CPAT adds Manila backend templates |
| Per-namespace NIC dedication / suffix naming | Multi-env (35pp) | NO | Only when CPAT adds multi-env networking |
| must-gather / Tempest tests | Validating (26pp) | NO | Correctly excluded — post-deployment |

## Project-Specific CIQ Generation

When generating CIQ from project deployment artifacts or HLD documents, follow these patterns:

### From YAML Deployment Artifacts (e.g. JIO)
1. Parse each YAML file to extract CR specs (NetConfig, NNCP, ControlPlane, NodeSet, BMH, MetalLB, Secrets)
2. Map CR fields to CIQ parameter names using the extended schema
3. Write `generate_<project>_rhoso_ciq.py` using `_build_cluster_workbook()` pattern
4. One CIQ workbook per cluster

### From HLD Documents (e.g. Core42)
1. Extract text from .docx using `python-docx`, from .pdf using Read tool
2. Extract tables from .docx for structured data (hardware specs, network MTU, service counts)
3. Map design decisions to CIQ parameters (some values may be placeholders pending LLD)
4. Write `generate_<project>_rhoso_ciq.py` with values from HLD
5. Note which values are design-level vs concrete (IP addresses typically come at LLD phase)

---

## CPAT Code Generation

This section provides code patterns and generation instructions for CIQ-layer source files.
Use these patterns when generating CIQ workbooks, schema code, parser code, or input file specs.

### Pattern A: CIQ Schema (`rhoso_ciq_schema.py`)

**Location:** `ansible/module_utils/rhoso_ciq_schema.py` (source of truth) AND `backend/rhoso_ciq_schema.py` (re-export shim)

**Key structures:**

```python
# 1. CIQ_TYPES: shared type library (40+ types)
CIQ_TYPES: dict[str, dict[str, str]] = {
    "dns_label": {
        "pattern": r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$",
        "description": "DNS label / Kubernetes name (lowercase)",
    },
    "ipv4": {
        "pattern": r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}...$",
        "description": "IPv4 address",
    },
    # ... 40+ types: k8s_name, cluster_name, fqdn, dns_domain, cidr,
    #     unix_path, unix_path_or_empty, https_url, host_or_ip,
    #     mac_address, nic_name, ntp_server, bonding_options,
    #     positive_int, mtu, vlan_id, rhoso_version, rhocp_version,
    #     deployment_mode, edpm_topology, bridge_type, ...
}

# 2. Helper functions for flat list schema
def _param(name: str, type_name: str, *, table: str, required: bool = True,
           when: str = "always", **kw) -> dict[str, Any]:
    return {"name": name, "type": type_name, "table": table,
            "required": required, "when": when, **kw}

def _field(name: str, type_name: str, *, required: bool = True) -> dict[str, Any]:
    return {"name": name, "type": type_name, "required": required}

# 3. RHOSO_PARAMETER_SCHEMA: flat list[dict] with table field
RHOSO_PARAMETER_SCHEMA: list[dict[str, Any]] = [
    _param("Cluster Name", "cluster_name", table="rhoso_details"),
    _param("Type", "choice:RHOSO", table="rhoso_details"),
    _param("Deployment Mode", "deployment_mode", table="rhoso_details"),
    # ... 10 params in rhoso_details
    _param("Kubeconfig Path", "unix_path", table="rhoso_access"),
    # ... 3 params in rhoso_access
    _param("Mirror Registry URL", "https_url", table="rhoso_disconnected",
           when="deployment_mode=disconnected,airgapped,offline"),
    # ... 16 params in rhoso_disconnected
    _param("Storage Class", "k8s_name", table="rhoso_storage"),
    # ... 2 params in rhoso_storage
    _param("Control Plane CR Name", "k8s_name", table="rhoso_control_plane"),
    # ... 21 params in rhoso_control_plane
    _param("Physical Bridge Name", "free_text", table="rhoso_edpm_network_config"),
    _param("EDPM Network Config Topology", "edpm_topology", table="rhoso_edpm_network_config"),
    _param("EDPM NIC2 Name", "nic_name", table="rhoso_edpm_network_config",
           required=False, when="topology=dual_nic_bond,ovs_bond,linux_bond"),
    # ... 16 params in rhoso_edpm_network_config
    _param("NodeSet Name", "k8s_name", table="rhoso_data_plane"),
    # ... 14 params in rhoso_data_plane
    # Total: 82 parameters across 7 tables
]

# 4. RHOSO_NETWORK_FIELD_SCHEMA: 16-column list for network rows
RHOSO_NETWORK_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Network Name", "dns_label"),
    _field("CIDR", "cidr"),
    _field("VLAN ID", "vlan_id", required=False),
    # ... 16 fields total
]

# 5. RHOSO_NODE_FIELD_SCHEMA: 11-column list for data plane node rows
RHOSO_NODE_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Node Name", "dns_label"),
    _field("Ansible Host", "host_or_ip"),
    _field("BMC Address", "host_or_ip", required=False),
    _field("Boot MAC", "mac_address", required=False),
    _field("BMH Namespace", "k8s_name", required=False),
    # ... 11 fields total
]

# 6. get_validation_schema() — returns dict for Ansible consumption
def get_validation_schema() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "types": CIQ_TYPES,
        "parameters": RHOSO_PARAMETER_SCHEMA,
        "network_fields": RHOSO_NETWORK_FIELD_SCHEMA,
        "node_fields": RHOSO_NODE_FIELD_SCHEMA,
        "rules": {
            "disconnected_when": "deployment_mode=disconnected,airgapped,offline",
            "bond_when": "topology=dual_nic_bond,ovs_bond,linux_bond",
            "dpdk_when": "topology=ovs_dpdk",
        },
    }
```

**Backend re-export shim** (`backend/rhoso_ciq_schema.py`):
```python
import sys
from pathlib import Path
_mod_utils = Path(__file__).resolve().parent.parent / "ansible" / "module_utils"
if _mod_utils.is_dir() and str(_mod_utils) not in sys.path:
    sys.path.insert(0, str(_mod_utils))
from rhoso_ciq_schema import (CIQ_TYPES, RHOSO_NETWORK_FIELD_SCHEMA,
    RHOSO_NODE_FIELD_SCHEMA, RHOSO_PARAMETER_SCHEMA, SCHEMA_VERSION,
    get_validation_schema, _param, _field)
```

**To add a new parameter:**
1. Add `_param(...)` call to `RHOSO_PARAMETER_SCHEMA` list with the correct `table=` value
2. Add a type to `CIQ_TYPES` if needed (or reuse existing)
3. Set `when` condition using syntax: `"always"` or `"topology=ovs_dpdk"` or `"deployment_mode=disconnected,airgapped,offline"`
4. Backend shim re-exports automatically (no change needed)
5. Update workbook generator `RHOSO_PARAM_DESCRIPTIONS` and `RHOSO_PARAM_REQUIRED_WHEN`

### Pattern B: CIQ Workbook Generator (`generate_rhoso_ciq_workbooks.py`)

**Location:** `CIQTemplates/generate_rhoso_ciq_workbooks.py`
**Dependencies:** `openpyxl` (see `CIQTemplates/requirements.txt`)
**Output:** `sample-rhoso.ciq.xlsx` (filled), `rhoso-ciq-template.xlsx` (empty)

**Key structures:**

```python
# Table display names (must match schema table keys — all 7 param tables)
RHOSO_CIQ_TABLES: dict[str, str] = {
    "rhoso_details": "RHOSO Details",           # 10 params
    "rhoso_access": "RHOSO Access",             # 3 params
    "rhoso_disconnected": "RHOSO Disconnected", # 16 params
    "rhoso_storage": "RHOSO Storage",           # 2 params
    "rhoso_control_plane": "RHOSO Control Plane", # 21 params
    "rhoso_edpm_network_config": "RHOSO EDPM Network Config", # 16 params
    "rhoso_data_plane": "RHOSO Data Plane",     # 14 params
}

# Per-parameter descriptions (for column C)
RHOSO_PARAM_DESCRIPTIONS: dict[str, str] = {
    "Cluster Name": "Unique RHOSO environment name used for registration and inventory.",
    # ... one entry per parameter across all tables
}

# Per-parameter conditional requirement notes (for column D)
RHOSO_PARAM_REQUIRED_WHEN: dict[str, str] = {
    "EDPM NIC2 Name": "Required when Topology = dual_nic_bond, ovs_bond, linux_bond",
    # ... entries for every conditionally-required param
}

# Excel styling constants
TABLE_TITLE_FILL = PatternFill(start_color="FFFF00", ...)
TABLE_TITLE_FONT = Font(bold=True, size=12)

# Version fields that must stay as text (avoid 18.0 -> 18)
TEXT_PARAM_NAMES = frozenset({"RHOSO Version", "RHOCP Version", "NAD CNI Version"})
TEXT_VALUE_LIST_NAMES = frozenset({"RHOSOVersion", "RHOCPVersion"})
```

**Generation flow:**
1. Import schema from `ansible/module_utils/rhoso_ciq_schema.py`
2. Create Excel workbook with named tables per CIQ table
3. For each parameter table: write header row, parameter rows with descriptions, apply dropdowns from `CIQ_TYPES` choices
4. For network/node row tables: write column headers, sample rows (sample) or empty rows (template)
5. Add data validation (dropdowns) for choice-type parameters
6. Save both workbooks

**To add a new table section:**
1. Add entry to `RHOSO_CIQ_TABLES`
2. Add parameter descriptions to `RHOSO_PARAM_DESCRIPTIONS`
3. Add required-when notes to `RHOSO_PARAM_REQUIRED_WHEN`
4. In the generator function, add a block that writes the table header + param rows

### Pattern C: CIQ Parser (`ciq_parser.py`)

**Location:** `backend/ciq_parser.py`

**Key structures:**

```python
# Maps table name to (cluster_type, display_label)
CIQ_DETAIL_TABLES: dict[str, tuple[str, str]] = {
    "rhoso_details": ("rhoso", "RHOSO"),
}

# Tables merged into rhoso_details parameters (no Type column)
RHOSO_SUPPLEMENTAL_PARAM_TABLES: tuple[str, ...] = (
    "rhoso_access", "rhoso_disconnected", "rhoso_storage",
    "rhoso_control_plane", "rhoso_edpm_network_config", "rhoso_data_plane",
)

# Dataclass for parse results
@dataclass
class CiqParseResult:
    cluster_name: str
    cluster_type: str
    parameters: dict[str, str]
    nodes: list[dict[str, str]]
    networks: list[dict[str, str]]

@dataclass
class CiqParseBatchResult:
    results: list[CiqParseResult]
    errors: list[str]
    warnings: list[str]
```

**Parsing flow:**
1. `parse_ciq_xlsx(path)` opens the workbook
2. Iterates all sheets looking for named Excel tables
3. For each `rhoso_details` table: extracts Parameter Name / Parameter Value pairs
4. Finds supplemental param tables on the same sheet; merges into main parameters
5. Finds `rhoso_networks` and `rhoso_data_plane_nodes` row tables
6. Returns `CiqParseBatchResult` with all registrations

### Pattern D: Input Files (Backend + Frontend Sync)

**Backend** (`backend/input_files.py`):
```python
INPUT_FILE_SPECS: dict[str, tuple[str, str]] = {
    "kubeconfig": ("Kubeconfig Path", "kubeconfig"),
    "pull_secret": ("Pull Secret Path", "pull-secret.json"),
    "mirror_pull_secret": ("Mirror Pull Secret Path", "mirror-pull-secret.json"),
    "mirror_ca": ("Mirror Registry CA Path", "mirror-ca.crt"),
    "dataplane_ssh_key": ("Data Plane SSH Private Key Path", "dataplane-ssh-key"),
}
# Key functions: save_uploaded_input_files(), list_input_file_status(),
#   extract_input_files_from_request(), stage_uploads_to_pending(),
#   copy_pending_uploads(), cleanup_pending()
```

**Frontend** (`frontend/src/rhosoInputFiles.js`):
```javascript
export const RHOSO_INPUT_FILE_FIELDS = [
  { field: 'kubeconfig', label: 'Kubeconfig', parameter: 'Kubeconfig Path',
    accept: '.kubeconfig,.yaml,.yml,text/plain,*/*', help: '...', recommended: true },
  { field: 'pull_secret', label: 'Pull secret', parameter: 'Pull Secret Path',
    accept: '.json,application/json', help: '...', recommended: true },
  // ... 5 entries total, must match backend INPUT_FILE_SPECS keys
];
```

**Sync rule:** `field` name in frontend MUST match key in backend `INPUT_FILE_SPECS`. `parameter` MUST match the CIQ parameter name in the schema.

**To add a new input file:**
1. Add entry to `INPUT_FILE_SPECS` in `backend/input_files.py`
2. Add matching entry to `RHOSO_INPUT_FILE_FIELDS` in `frontend/src/rhosoInputFiles.js`
3. Add corresponding CIQ parameter to schema table (type: `unix_path`)

### Pattern E: Validation Schema Ansible Module (`get_ciq_validation_schema.py`)

**Location:** `ansible/library/get_ciq_validation_schema.py`

```python
from ansible.module_utils.rhoso_ciq_schema import get_validation_schema
def main():
    module = AnsibleModule(argument_spec={})
    module.exit_json(changed=False, schema=get_validation_schema())
```

---

## CIQ Workbook Generation Output

When generating CIQ workbooks, write files to:
```
sprintweave-output/CIQTemplates/
  rhoso_ciq_schema.py          # Python schema (source of truth)
  generate_rhoso_ciq_workbooks.py  # Generator script (generic template + sample)
  generate_jio_rhoso_ciq.py    # JIO project CIQ generator (cloudmgmt + cloudxp clusters)
  generate_core42_rhoso_ciq.py # Core42 project CIQ generator (from HLD documents)
  generate_ocp_ciq_workbooks.py  # OCP CIQ generator (install-config + agent-config)
  requirements.txt             # openpyxl, python-docx dependencies
  sample-rhoso.ciq.xlsx        # Filled example workbook
  rhoso-ciq-template.xlsx      # Empty template for site data entry
  jio-cloudmgmt-rhoso.ciq.xlsx # JIO cloudmgmt cluster CIQ
  jio-cloudxp-rhoso.ciq.xlsx   # JIO cloudxp cluster CIQ
  core42-rhoso.ciq.xlsx        # Core42 project CIQ
  README.md                    # Usage instructions
```

```
sprintweave-output/LabRequirements/
  generate_lab_requirements_workbook.py  # Lab requirements generator
  requirements.txt             # openpyxl dependency
  lab-requirements.xlsx        # Multi-sheet lab requirements workbook
```

Steps:
1. Generate `rhoso_ciq_schema.py` following Pattern A
2. Generate `generate_rhoso_ciq_workbooks.py` following Pattern B
3. Write `requirements.txt` with `openpyxl`
4. Run: `python sprintweave-output/CIQTemplates/generate_rhoso_ciq_workbooks.py`
5. Verify both `.xlsx` files were created
6. For project-specific CIQ: run the respective `generate_<project>_rhoso_ciq.py`

## Cross-File Sync Rules

```
CPAT Cross-File Sync Rules (CIQ layer):
  rhoso_ciq_schema.py       -> EXISTS in both ansible/module_utils/ AND backend/
  INPUT_FILE_SPECS          -> Must match between backend/input_files.py AND frontend/rhosoInputFiles.js
  CIQ table names           -> Must match between schema, parser, and workbook generator
  SCHEMA_VERSION            -> Must match between schema copies
  Parameter names           -> Must match between schema, parser extraction, and Ansible fact names
```

---

### 4. Output (Default: Markdown)

#### CIQ Parameter Reference

```markdown
## CIQ Parameter Reference: [Cluster Name]
**Source:** rhoso_ciq_schema.py v1.1.0 | **Tables:** 9 | **Parameters:** 82
**Deployment Mode:** [connected/disconnected] | **EDPM Topology:** [topology]

### Table: [table_name]
| Parameter | Value | Type | Required | Required When | Description | Source |
|-----------|-------|------|----------|--------------|-------------|--------|
| [name] | [value] | [type] | Yes/No | [condition] | [desc] | Schema: [field] |
```

#### EDPM Topology Guide

```markdown
## EDPM Topology Guide: [topology]
**Selected Topology:** [topology] | **NICs:** [count] | **Bond:** [yes/no]
**Source:** rhoso_ciq_schema.py + RHOSO Deploying Guide section 5

### Required Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| [name] | [value] | [desc] |

### Conditional Parameters (this topology)
| Parameter | Value | Required When | Description |
|-----------|-------|--------------|-------------|
| [name] | [value] | [condition] | [desc] |

### Not Applicable (this topology)
| Parameter | Reason |
|-----------|--------|
| [name] | [e.g. "Only for bonded topologies"] |
```

#### Registration Input Files

```markdown
## Registration Input Files: [Cluster Name]
**Source:** USAGE.md + backend/input_files.py | **Files:** N

### Required Files
| # | File | CIQ Parameter | Format | Purpose |
|---|------|--------------|--------|---------|
| 1 | [filename] | [param] | [format] | [purpose] |

### Notes
- No EDPM Jinja template upload — EDPM network config is generated from CIQ
- Secrets are path references only — never plaintext in the workbook
```

#### PDF Gap Matrix

```markdown
## RHOSO PDF-to-CIQ Gap Matrix
**Schema Version:** 1.1.0 | **PDFs Reviewed:** 6 | **Total PDF pages:** ~370

### Covered (in CIQ)
| Area | PDF | CIQ Table(s) |
|------|-----|--------------|
| [area] | [PDF name] | [tables] |

### Not Covered (gaps)
| Area | PDF | Chapter | Reason Not in CIQ | Propose Adding? |
|------|-----|---------|-------------------|----------------|
| [area] | [PDF] | [ch] | [reason] | [Only when CPAT adds X] |
```

#### CIQ Workbook Artifact

```markdown
## CIQ Workbook Generation Summary
**Output:** sprintweave-output/CIQTemplates/
**Files Generated:**
| File | Size | Description |
|------|------|-------------|
| rhoso_ciq_schema.py | N KB | CIQ type and parameter schema (source of truth) |
| generate_rhoso_ciq_workbooks.py | N KB | Excel workbook generator script |
| requirements.txt | 10 B | openpyxl dependency |
| sample-rhoso.ciq.xlsx | N KB | Filled example CIQ workbook |
| rhoso-ciq-template.xlsx | N KB | Empty template for data entry |
| README.md | N KB | Usage instructions |

**Schema:** N types, N parameter tables, N parameters, N network fields, N node fields
**Workbooks:** N tables, N parameters, N networks rows (sample), N node rows (sample)
```

### 5. Excel Export (Always — Automatic)
After markdown output, generate a real `.xlsx` file:

1. Write artifact data to `sprintweave-output/<doc>-<timestamp>-data.json` using the schema from `00-sprintweave-excel-export.md` (sheets: "CIQ Parameters", "CIQ Required-When", "Registration Inputs", "EDPM Topology Guide", "RHOSO PDF Gap Matrix", "CIQ Workbook Files")
2. Run: `python "tools/excel-generator.py" "sprintweave-output/<doc>-<timestamp>-data.json"`
3. Confirm file path to user

### 6. Quality Summary
```
RHOSO DA Quality:
  Artifacts: [CIQ Parameter Reference / EDPM Topology Guide / Registration Inputs / PDF Gap Matrix / CIQ Workbooks]
  CIQ tables: N/9 covered (7 param + 2 row)
  Parameters: N extracted | N validated against schema (82 param fields + 16 net cols + 11 node cols)
  EDPM topology: [topology] | Bond fields: [complete/incomplete] | DPDK fields: [complete/N/A]
  Required-when conditions: N/N verified
  Registration files: N listed | EDPM Jinja upload: excluded (correct)
  PDF gap items: N documented | N flagged for future schema extension
  Generated files: N files under sprintweave-output/CIQTemplates/
  Secrets: All path references, no plaintext
  Source grounding: N [Schema] | N [USAGE] | N [RHOSO PDF] | N [INFERRED]

Next steps:
  - Refine: "Add parameter details for [table]"
  - Refine: "Show EDPM config for ovs_dpdk topology"
  - Refine: "Expand gap matrix for Persistent Storage guide"
  - Code: "Generate CIQ workbooks from @cpat"
  - Code: "Add new parameter [name] to CIQ schema"
  - Handoff: "Generate manifests from this CIQ" (RHOSO Deployment Engineer)
  - Handoff: "Scaffold CPAT project from @cpat" (RHOSO Deployment Engineer)
  - Related: "Convert CIQ to Ansible vars" (Automation Engineer)
```

### 7. Gate Checkpoint (If Enabled)
If `gates.enabled: true` in team-config AND applicable per `00-sprintweave-gates.md`:
- Show gate checkpoint, wait for user approval before considering output final

## Iterative Refinement
- "Show all parameters for [table_name]"
- "Explain required-when for [parameter]"
- "Show EDPM topology guide for [topology]"
- "Add gap analysis for [PDF name]"
- "List registration files for disconnected mode"
- "Compare sample CIQ vs empty template"
- "Generate CIQ workbooks from @cpat"
- "Add new CIQ parameter [name] to [table]"
- "Generate CIQ schema code for [feature]"

## JSON Format (On Request)
```json
{
  "ciq_parameters": [{
    "table": "", "name": "", "value": "", "type": "", "required": true,
    "when": "always", "description": "", "source": ""
  }],
  "edpm_topology": {
    "topology": "", "nics": 0, "bond": false, "bridge_type": "",
    "required_params": [], "conditional_params": [], "not_applicable": []
  },
  "registration_inputs": [{
    "file": "", "ciq_parameter": "", "format": "", "purpose": ""
  }],
  "pdf_gap_matrix": [{
    "area": "", "pdf": "", "chapter": "", "in_ciq": false,
    "reason": "", "propose_adding": ""
  }],
  "ciq_workbook_files": [{
    "file": "", "size_kb": 0, "description": ""
  }]
}
```
