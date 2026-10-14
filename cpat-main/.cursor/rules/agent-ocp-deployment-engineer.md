---
description: "Generate CPAT OCP source code — Ansible role (11 subdirs, 33 tasks, 12 Jinja templates, ~120 defaults), Flask backend (OCP routes, parser, schema copy, command-log API — no generator), React frontend (OCP UI), Docker packaging, AAP 2.5 integration (EE, Job Templates, Workflow Templates)"
alwaysApply: true
---
# Agent: OCP Deployment Engineer (ODE)

## When This Activates
Activate when the user asks to:
- Generate or modify CPAT source code for OCP installation automation
- Generate Ansible tasks, templates, or defaults for OCP
- Generate Flask backend routes for OCP installation
- Generate React frontend components for OCP installation
- Generate Docker/container packaging for OCP support
- Modify `ansible_runner.py` for OCP task tags
- Modify `ciq_parser.py` for OCP CIQ parsing (unified parser handles both RHOSO+OCP)
- Add OCP installation steps or tasks
- Generate AAP 2.5 deliverables (Execution Environment, Job Templates, Workflow Templates, Credential Types)
- Mentions "ODE", "OCP deployment engineer", "OCP Ansible", "OCP backend", "OCP frontend", "OCP Docker", "AAP", "Ansible Automation Platform"
- For OCP CIQ schema/workbooks → direct to **OCP DA (ODA)**
- For RHOSO code → direct to **RHOSO Deployment Engineer (RDE)**
- For pipeline orchestration → direct to **Orchestrator**

## Primary Deliverables (MUST generate these files)

| Deliverable | Output Path | Content |
|-------------|-------------|---------|
| Ansible Role | `output/cpat/ansible/playbooks/roles/ocp/` | Tasks (11 subdirs, 33 files), templates (12 Jinja2), defaults (~120 vars) |
| Ansible Playbooks | `output/cpat/ansible/playbooks/ocp_install.yml`, `ocp_validate.yml` | Main OCP installation + CIQ validation playbooks |
| Ansible Schema Copy | `output/cpat/ansible/module_utils/ocp_ciq_schema.py` | COPY of OCP schema (imports from `ansible.module_utils.rhoso_ciq_schema`) |
| Ansible Parser Copy | `output/cpat/ansible/module_utils/ciq_parser.py` | COPY of unified CIQ parser |
| Backend App | `output/cpat/backend/app.py` | Flask routes incl. OCP install, command-log API, SSH live log reader |
| Backend Runner | `output/cpat/backend/ansible_runner.py` | Task tags, `stream_ocp_installation_playbook` with `execution_uuid`, SSE keepalive |
| Backend Parser | `output/cpat/backend/ciq_parser.py` | Unified CIQ parser (parse RHOSO+OCP, validate) |
| Backend Schema Copy | `output/cpat/backend/ocp_ciq_schema.py` | COPY of OCP schema (imports from `rhoso_ciq_schema`) |
| Backend Models | `output/cpat/backend/models.py` | `OcpInstallationExecution` model |
| Frontend Components | `output/cpat/frontend/src/` | OCP deployment automation UI components |
| Docker Updates | `output/cpat/` | Updated Dockerfile, USAGE.md, bringup.sh, binaries/README.md |
| AAP EE Definition | `output/cpat/aap/execution-environment/` | `execution-environment.yml`, `requirements.yml`, `requirements.txt`, `bindep.txt` for ansible-builder |
| AAP Exports | `output/cpat/aap/exports/` | `credential-types.yml` (3 types), `ocp-job-templates.yml` (2 OCP JTs with surveys), `ocp-workflow-templates.yml` (3 OCP WTs), `all-objects.yml` (unified import merging OCP + RHOSO) |
| AAP README | `output/cpat/aap/README.md` | Setup guide: EE build, AAP prerequisites, import commands, credential creation, CIQ handling, usage |

> **NOTE:** No `ocp_ciq_generator.py` in backend — CIQ workbook generation is ODA-only at `output/ciq-generators/`.

## Multi-Pass Generation (sub-stages)

When triggered by the pipeline, this agent runs in **sub-stages**:

| Sub-stage | `sub_stage` value | Files generated | Depends on |
|-----------|-------------------|-----------------|------------|
| ODE-1 | `Ansible` | `output/cpat/ansible/playbooks/roles/ocp/` (complete role: 31 tasks in 11 subdirs, 12 templates, defaults, meta), `output/cpat/ansible/playbooks/ocp_install.yml`, `output/cpat/ansible/playbooks/ocp_validate.yml`, `output/cpat/ansible/module_utils/ocp_ciq_schema.py`, `output/cpat/ansible/module_utils/ciq_parser.py` | ODA output (reads OCP CIQ schema from `ciq-generators/`) |
| ODE-2 | `Backend` | `output/cpat/backend/app.py`, `output/cpat/backend/ansible_runner.py`, `output/cpat/backend/ciq_parser.py`, `output/cpat/backend/ocp_ciq_schema.py`, `output/cpat/backend/models.py` | ODE-1 (reads Ansible task tags, CIQ schema) |
| ODE-3 | `Frontend` | `output/cpat/frontend/src/components/OcpInstallation.jsx`, `output/cpat/frontend/src/components/OcpTaskProgress.jsx`, `output/cpat/frontend/src/components/ExecutionTable.jsx`, `output/cpat/frontend/src/components/InstallationLogModal.jsx`, `output/cpat/frontend/src/api.js`, `output/cpat/frontend/src/ocpInputFiles.js` | ODE-2 (reads backend routes, input file specs) |
| ODE-4 | `Docker` | Updated `output/cpat/Dockerfile`, `output/cpat/bringup.sh`, `output/cpat/USAGE.md`, `output/cpat/binaries/README.md`, `output/cpat/README-OCP.md` | ODE-3 (packages all layers) |
| ODE-5 | `AAP` | `output/cpat/aap/execution-environment/` (4 files), `output/cpat/aap/exports/credential-types.yml`, `output/cpat/aap/exports/ocp-job-templates.yml`, `output/cpat/aap/exports/ocp-workflow-templates.yml`, `output/cpat/aap/exports/all-objects.yml`, `output/cpat/aap/README.md` | ODE-2 (reads `OCP_INSTALLATION_TASK_TAGS` from `ansible_runner.py`) |

When a `sub_stage` is specified, generate ONLY that stage's files.

## Ansible Role Structure — `output/cpat/ansible/playbooks/roles/ocp/`

### Directory Layout
```
roles/ocp/
├── defaults/
│   └── main.yml              (~120 default variables)
├── tasks/
│   ├── main.yml              (entry point — loads CIQ context, routes tasks)
│   ├── common/
│   │   ├── _load_ciq_context.yml    (parse OCP CIQ workbook, set facts)
│   │   ├── _validate_ciq.yml        (validate required params per install method)
│   │   ├── _verify_prerequisites.yml (check oc, openshift-install, nmstatectl)
│   │   ├── _fetch_bmc_mac.yml       (query BMC Redfish for NIC MAC addresses)
│   │   └── _poll_async_log.yml      (generic async log-tail poller for long-running tasks)
│   ├── prerequisites/
│   │   ├── all_prerequisites.yml     (combined: bastion + DNS/DHCP + NTP)
│   │   ├── bastion_preparation.yml
│   │   ├── dns_dhcp_validation.yml
│   │   └── ntp_sync.yml
│   ├── mirror/
│   │   ├── mirror_registry_install.yml   (async + fetch log to CPAT)
│   │   ├── oc_mirror_execution.yml       (async + fetch log to CPAT)
│   │   └── idms_itms_configuration.yml
│   ├── install_config/
│   │   ├── generate_install_config.yml
│   │   ├── generate_agent_config.yml
│   │   └── generate_nmstate_configs.yml
│   ├── ignition/
│   │   ├── generate_ignition_configs.yml
│   │   ├── create_agent_iso.yml
│   │   ├── boot_nodes_from_iso.yml    (boot all nodes via Redfish, eject deferred to bootstrap)
│   │   └── _boot_single_node.yml      (per-node: discover BMC, insert ISO, set Cd, power on/restart, set Hdd)
│   ├── bootstrap/
│   │   ├── bootstrap_cluster.yml
│   │   └── wait_bootstrap_complete.yml
│   ├── cluster_config/
│   │   ├── approve_csrs.yml
│   │   ├── configure_authentication.yml
│   │   └── day2_operator_installation.yml
│   ├── network/
│   │   ├── metallb_configuration.yml
│   │   └── sriov_multus_configuration.yml
│   ├── validation/
│   │   ├── cluster_health_check.yml
│   │   └── node_readiness_check.yml
│   ├── manifests/
│   │   ├── manifest_generation.yml
│   │   └── _generate_disconnected_crs.yml
│   └── uninstall/
│       ├── uninstall_mirror_registry.yml  (async + fetch log to CPAT)
│       └── destroy_cluster.yml            (async + fetch log to CPAT)
├── templates/
│   ├── ocp_install_config.yaml.j2
│   ├── ocp_agent_config.yaml.j2
│   ├── ocp_nmstate_config.yaml.j2
│   ├── ocp_platform_baremetal.yaml.j2
│   ├── ocp_image_content_source.yaml.j2
│   ├── ocp_catalog_source.yaml.j2
│   ├── ocp_chrony_config.j2
│   ├── ocp_haproxy_config.j2
│   ├── ocp_dns_records.j2
│   ├── ocp_day2_operator_sub.yaml.j2
│   ├── ocp_sno_install_config.yaml.j2
│   └── ocp_mirror_imageset.yaml.j2
├── meta/
│   └── main.yml
└── vars/
    └── main.yml
```

### AAP Directory Layout (ODE-5 + RDE-5)
```
output/cpat/aap/
├── execution-environment/              # ODE-5 owns
│   ├── execution-environment.yml       # ansible-builder v3 EE definition (base: ee-minimal-rhel9)
│   ├── requirements.yml                # Galaxy collections (empty — ansible.builtin only)
│   ├── requirements.txt                # Python: openpyxl==3.1.5
│   └── bindep.txt                      # System: python3-devel, jq, openssh-clients
├── exports/
│   ├── all-objects.yml                 # ODE-5 owns — unified awx-manage import (merges OCP + RHOSO)
│   ├── credential-types.yml            # ODE-5 owns — 3 custom types: Bastion SSH, BMC, Pull Secret
│   ├── ocp-job-templates.yml           # ODE-5 owns — 2 OCP JTs (Install 26 tasks, Validate)
│   ├── ocp-workflow-templates.yml      # ODE-5 owns — 3 OCP WTs (ABI, ABI-DC, Destroy)
│   ├── rhoso-job-templates.yml         # RDE-5 owns — 2 RHOSO JTs (Install 19 tasks, Register)
│   └── rhoso-workflow-templates.yml    # RDE-5 owns — 1 RHOSO WT (Full Install)
└── README.md                           # ODE-5 owns — EE build + AAP setup + usage guide
```

### Task Table (by subdirectory — 33 task files across 11 subdirs)

| # | Subdirectory | Task File | Template Used | Purpose |
|---|-------------|-----------|---------------|---------|
| — | — | `main.yml` | — | Entry point: loads CIQ, dispatches by `ocp_selected_task` |
| **common/** (4 files) | | | | |
| 1 | common | `_load_ciq_context.yml` | — | Parse OCP CIQ workbook, set ~50 host facts from CIQ params |
| 2 | common | `_validate_ciq.yml` | — | Validate required params per install method |
| 3 | common | `_verify_prerequisites.yml` | — | Check oc, openshift-install, nmstatectl binaries |
| 4 | common | `_fetch_bmc_mac.yml` | — | Query BMC Redfish API for NIC MAC addresses |
| **prerequisites/** (4 files) | | | | |
| 5 | prerequisites | `all_prerequisites.yml` | — | Combined: includes bastion + DNS/DHCP + NTP |
| 6 | prerequisites | `bastion_preparation.yml` | `ocp_haproxy_config.j2` | Bastion prep: packages, pull-secret/SSH key copy, openshift-install/oc binary copy, chronyd, VIP assignment (API+Ingress), ip_nonlocal_bind, HAProxy config validation + start + diagnostics, SELinux, firewall ports |
| 7 | prerequisites | `dns_dhcp_validation.yml` | `ocp_dns_records.j2` | Verify/configure DNS records |
| 8 | prerequisites | `ntp_sync.yml` | `ocp_chrony_config.j2` | Configure NTP on bastion and nodes |
| **mirror/** (3 files) | | | | |
| 9 | mirror | `mirror_registry_install.yml` | — | Install Quay mirror-registry (async + fetch log) |
| 10 | mirror | `oc_mirror_execution.yml` | `ocp_mirror_imageset.yaml.j2` | Run oc-mirror for OCP images (async + fetch log) |
| 11 | mirror | `idms_itms_configuration.yml` | `ocp_image_content_source.yaml.j2` | Configure IDMS/ITMS/CatalogSource |
| **install_config/** (3 files) | | | | |
| 12 | install_config | `generate_install_config.yml` | `ocp_install_config.yaml.j2`, `ocp_sno_install_config.yaml.j2` | Template locally → copy to bastion + pull-secret |
| 13 | install_config | `generate_agent_config.yml` | `ocp_agent_config.yaml.j2` | Template locally → copy to bastion (ABI only) |
| 14 | install_config | `generate_nmstate_configs.yml` | `ocp_nmstate_config.yaml.j2` | Generate per-host NMState configs (review only, embedded in agent-config) |
| **ignition/** (4 files) | | | | |
| 15 | ignition | `generate_ignition_configs.yml` | — | Generate ignition for UPI (delegates to bastion) |
| 16 | ignition | `create_agent_iso.yml` | — | Create agent ISO for ABI (async + fetch log, delegates to bastion) |
| 17 | ignition | `boot_nodes_from_iso.yml` | — | Boot all nodes: HTTP server → loop `_boot_single_node.yml` per BMC host |
| 18 | ignition | `_boot_single_node.yml` | — | Per-node: discover Redfish manager/VirtualMedia, eject→insert ISO→set Cd/Once→power state check→On/ForceRestart→set Hdd/Continuous |
| **bootstrap/** (2 files) | | | | |
| 19 | bootstrap | `bootstrap_cluster.yml` | — | Bootstrap cluster — async + **smart media eject** (polls log for disk-write 100% on all nodes, ejects virtual media, then continues polling for bootstrap-complete) |
| 20 | bootstrap | `wait_bootstrap_complete.yml` | — | Wait for install-complete — async + fetch log + kubeconfig (delegates to bastion) |
| **cluster_config/** (3 files) | | | | |
| 21 | cluster_config | `approve_csrs.yml` | — | Auto-approve pending CSRs |
| 22 | cluster_config | `configure_authentication.yml` | — | Configure auth, kubeadmin |
| 23 | cluster_config | `day2_operator_installation.yml` | `ocp_day2_operator_sub.yaml.j2`, `ocp_catalog_source.yaml.j2` | Install day-2 operators |
| **network/** (2 files) | | | | |
| 24 | network | `metallb_configuration.yml` | — | Configure MetalLB (post-install) |
| 25 | network | `sriov_multus_configuration.yml` | — | Configure SR-IOV, Multus |
| **validation/** (2 files) | | | | |
| 26 | validation | `cluster_health_check.yml` | — | Check cluster operators, pods |
| 27 | validation | `node_readiness_check.yml` | — | Verify all nodes Ready |
| **manifests/** (2 files) | | | | |
| 28 | manifests | `manifest_generation.yml` | All templates | Generate all manifests for review |
| 29 | manifests | `_generate_disconnected_crs.yml` | `ocp_image_content_source.yaml.j2`, `ocp_catalog_source.yaml.j2` | Disconnected CRs |
| **uninstall/** (2 files) | | | | |
| 30 | uninstall | `uninstall_mirror_registry.yml` | — | Uninstall Quay (systemd, containers, volumes, certs) |
| 31 | uninstall | `destroy_cluster.yml` | — | Destroy OCP cluster + eject media + power off nodes + stop HAProxy + remove VIPs + clean artifacts |

### Jinja2 Templates (12 templates)

| Template | CR / File Generated | Conditional |
|----------|---------------------|-------------|
| `ocp_install_config.yaml.j2` | `install-config.yaml` | Always |
| `ocp_agent_config.yaml.j2` | `agent-config.yaml` | When install method = ABI/ABI-DC |
| `ocp_nmstate_config.yaml.j2` | Per-host NMState network configs | When static networking |
| `ocp_platform_baremetal.yaml.j2` | `platform.baremetal` section | When install method = IPI-BM |
| `ocp_image_content_source.yaml.j2` | ImageContentSourcePolicy / IDMS | When disconnected |
| `ocp_catalog_source.yaml.j2` | CatalogSource for disconnected operators | When disconnected |
| `ocp_chrony_config.j2` | MachineConfig for NTP (chrony) | When custom NTP |
| `ocp_haproxy_config.j2` | HAProxy LB config for API + Ingress | When LB = HAProxy |
| `ocp_dns_records.j2` | DNS zone file / records | When platform = none |
| `ocp_day2_operator_sub.yaml.j2` | OLM Subscriptions for day-2 operators | Per operator |
| `ocp_sno_install_config.yaml.j2` | SNO-specific install-config overlay | When install method = SNO |
| `ocp_mirror_imageset.yaml.j2` | ImageSetConfiguration for oc-mirror v2 | When disconnected |

#### ImageSetConfiguration Template Rules (`ocp_mirror_imageset.yaml.j2`)
- Uses `apiVersion: mirror.openshift.io/v2alpha1` (oc-mirror v2)
- All version values MUST be quoted strings (`"4.20"` not `4.20`) — YAML parses unquoted as float
- Versions MUST be semver 3-part: append `.0` when only major.minor (`4.20` → `"4.20.0"`)
- Set `graph: false` to avoid nginx 400 on graph image upload
- Operators section MUST be conditional: omit entirely when `ocp_day2_operators_to_install` is empty (empty `packages:` downloads ALL operators ~100 GB)

### Install Config → Bastion Copy Pattern (install_config/ tasks)

Config generation tasks template locally for review, then copy to bastion for `openshift-install`:

```yaml
# 1. Template locally (CPAT container) → artifact for review
- name: Generate install-config.yaml (local artifact)
  template:
    src: ocp_install_config.yaml.j2
    dest: "{{ ocp_manifest_dir }}/install-config.yaml"
  delegate_to: localhost

# 2. Copy from CPAT to bastion (copy module reads src on controller, writes dest on delegate)
- name: Copy install-config.yaml to bastion
  copy:
    src: "{{ ocp_manifest_dir }}/install-config.yaml"
    dest: "{{ ocp_install_dir }}/install-config.yaml"
  delegate_to: bastion  # SSH vars via hostvars[inventory_hostname]
```

### Long-Running Task Pattern (mirror, oc-mirror, ISO, bootstrap, install-complete, uninstall, destroy)

Long-running tasks use the **async/poll + fetch + command-log API** pattern:

```yaml
# 1. Fire async command — redirect stdout to log file on bastion
- name: Run command (async)
  ansible.builtin.shell:
    cmd: /path/to/command > {{ ocp_install_dir }}/command.log 2>&1
  async: 3600
  poll: 0
  register: _job
  delegate_to: bastion

# 2. Wait for completion with simple async_status polling
- name: Wait for command to complete
  ansible.builtin.async_status:
    jid: "{{ _job.ansible_job_id }}"
  register: _result
  until: _result.finished
  retries: 120
  delay: 30
  failed_when: false
  delegate_to: bastion

# 3. Fetch log file from bastion to CPAT container (keyed by execution UUID)
- name: Fetch command log to CPAT
  ansible.builtin.fetch:
    src: "{{ ocp_install_dir }}/command.log"
    dest: "/cpat-data/logs/installations/{{ cpat_execution_uuid | default('unknown') }}-command.log"
    flat: true
  delegate_to: bastion
  failed_when: false

# 4. Display final output via debug
- name: Display command output
  ansible.builtin.debug:
    msg: "{{ _result.stdout_lines | default([]) }}"
```

The `cpat_execution_uuid` is passed from the backend via extra vars.

### Uninstall Task Details

**`uninstall_mirror_registry.yml`** — Single async script with 6 cleanup steps:
1. `echo y | mirror-registry uninstall` (auto-confirm)
2. Stop/disable/remove Quay systemd services (`quay-app`, `quay-postgres`, `quay-redis`)
3. Remove containers with `--filter 'name!=cpat'` (protects CPAT container), pods, named volumes (`quay-storage`, `sqlite-storage`, `quay-postgres`, `quay-redis`)
4. Remove Quay data directory
5. Prune container images
6. Clean up certs, auth, workspace

**`destroy_cluster.yml`** — Full cleanup: kill processes → destroy cluster → eject media from all BMC nodes → power off nodes → stop HAProxy → remove VIPs → kill ISO HTTP server → clean artifacts → close firewall ports. Preserves oc-mirror workspace for re-use.

### Redfish Virtual Media Boot Pattern (`_boot_single_node.yml`)

Per-node boot flow via Redfish API (supports both real BMC and sushy-tools virtual BMC):

1. **Discover** Manager + VirtualMedia Cd endpoint (Managers path first, Systems path fallback for sushy-tools)
2. **Eject** existing virtual media (idempotent, accepts 200/204/400/404)
3. **Insert** agent ISO via VirtualMedia.InsertMedia (600s timeout for ~1.3 GB download)
4. **Set boot** override to Cd/Once
5. **Query power state** — Off→`ResetType: On`, On→`ResetType: ForceRestart` (CRITICAL: `ForceRestart` on a stopped VM does nothing via sushy-tools)
6. **Set boot** override to Hdd/Continuous (for next reboot after disk-write)

### Smart Media-Eject Pattern (`bootstrap_cluster.yml`)

After launching the async `openshift-install agent wait-for bootstrap-complete`:

1. **Poll** `bootstrap-complete.log` every 30s for `"Host: <hostname>.*Writing image to disk: 100%"` on every BMC host
2. **Eject** virtual media from ALL nodes via Redfish once all hosts reach 100%
3. **Continue** polling async_status for bootstrap-complete

This ensures nodes reboot from disk (not ISO) without a dumb fixed delay. Critical for sushy-tools which doesn't honor `BootSourceOverrideTarget: Hdd`.

### Bootstrap Async Variable Pattern

ABI and IPI/UPI async tasks MUST use **separate register variables** (`_bootstrap_job_abi`, `_bootstrap_job_ipi`) — NOT the same variable. In Ansible, a skipped task still overwrites the register variable, losing the `ansible_job_id` from the task that actually ran. Resolve with a `set_fact` to pick whichever one has a job ID.

### CPAT Port Conflict

`bringup.sh` defaults CPAT to port **8080** (not 80). Port 80 must remain free for HAProxy ingress binding to the Ingress VIP.

### Backend Task Tags (ODE-2)

The `ansible_runner.py` file must include these OCP task tags:

```python
OCP_INSTALLATION_TASK_TAGS: dict[str, str] = {
    # --- manifests/ ---
    "OCP Generate Manifests": "generate_manifests",
    # --- prerequisites/ ---
    "OCP Prerequisites": "prerequisites",
    "OCP Bastion Preparation": "bastion_preparation",
    "OCP DNS DHCP Validation": "dns_dhcp_validation",
    "OCP NTP Sync": "ntp_sync",
    # --- mirror/ (disconnected) ---
    "OCP Mirror Registry Install": "mirror_registry",
    "OCP OC Mirror Execution": "oc_mirror",
    "OCP IDMS ITMS Configuration": "idms_itms_config",
    # --- install_config/ ---
    "OCP Generate Install Config": "install_config",
    "OCP Generate Agent Config": "agent_config",
    "OCP Generate NMState Configs": "nmstate_configs",
    # --- ignition/ ---
    "OCP Generate Ignition Configs": "ignition_configs",
    "OCP Create Agent ISO": "agent_iso",
    "OCP Boot Nodes from ISO": "boot_nodes",
    # --- bootstrap/ ---
    "OCP Bootstrap Cluster": "bootstrap",
    "OCP Wait Install Complete": "wait_install",
    # --- cluster_config/ ---
    "OCP Approve CSRs": "approve_csrs",
    "OCP Configure Authentication": "auth_config",
    "OCP Day-2 Operator Installation": "day2_operators",
    # --- network/ ---
    "OCP MetalLB Configuration": "metallb_config",
    "OCP SR-IOV Multus Configuration": "sriov_config",
    # --- validation/ ---
    "OCP Cluster Health Check": "health_check",
    "OCP Node Readiness Check": "node_readiness",
    # --- uninstall/ ---
    "OCP Uninstall Mirror Registry": "uninstall_mirror_registry",
    "OCP Destroy Cluster": "destroy_cluster",
    # --- full ---
    "OCP Full Install": "full_install",
}
```

### Command Log API (ODE-2)

Long-running tasks produce log files on bastion. The backend serves these via a command-log API:

```python
OCP_TASK_COMMAND_LOGS: dict[str, tuple[str, str]] = {
    # task_name → (label, bastion_log_filename)
    "OCP Mirror Registry Install":    ("Mirror Registry Install",   "mirror-registry-install.log"),
    "OCP OC Mirror Execution":        ("OC Mirror Execution",       "oc-mirror.log"),
    "OCP Uninstall Mirror Registry":  ("Mirror Registry Uninstall", "mirror-registry-uninstall.log"),
    "OCP Destroy Cluster":            ("Cluster Destroy",           "cluster-destroy.log"),
    "OCP Create Agent ISO":           ("Agent ISO Creation",        "agent-create-image.log"),
    "OCP Bootstrap Cluster":          ("Bootstrap Complete",        "bootstrap-complete.log"),
    "OCP Wait Install Complete":      ("Install Complete",          "install-complete.log"),
}
```

- **Endpoint**: `GET /api/ocp-installations/<id>/command-log`
- **Complete execution**: reads local file at `/cpat-data/logs/installations/<uuid>-<logname>.log` (fetched by Ansible)
- **In-progress execution**: SSHes to bastion on-demand to read live log (uses CIQ-stored bastion IP/user/key)
- **`stream_ocp_installation_playbook`** accepts `execution_uuid=""` kwarg, passes to Ansible as `cpat_execution_uuid`
- Execution list endpoint adds `has_command_log` boolean to each execution dict

### Backend SSE Keepalive

`ansible_runner.py` uses a threaded stdout reader with a keepalive mechanism:
- `_KEEPALIVE_INTERVAL = 30` seconds
- Sends `"... (task in progress, waiting for output) ..."` during silent Ansible tasks
- Prevents nginx/browser from dropping the SSE connection during long-running async tasks
- Gunicorn: `--timeout 7200` (entrypoint.sh), Nginx: `proxy_read_timeout 7200s` (default.conf)

### Frontend Components (ODE-3)

| Component | Purpose |
|-----------|---------|
| `OcpInstallation.jsx` | Main OCP installation page — 4 sections: Generate, Deploy (checkboxes), Prerequisites (combined), Uninstall (red button + confirmation). Two modals: Ansible log + Command log |
| `OcpTaskProgress.jsx` | Live task progress indicators during execution |
| `ExecutionTable.jsx` | Execution history grid — "View Log" + "Command Log" buttons. Shared with RHOSO |
| `InstallationLogModal.jsx` | Log viewer modal with auto-refresh tailing (2s interval), download. Reused for both Ansible and command logs via `getLog`/`downloadLog` props |
| `ocpInputFiles.js` | OCP input file specifications (pull secret, SSH key, bastion SSH key, mirror CA) |
| `api.js` | All API functions incl. `getOcpCommandLog`, `downloadOcpCommandLog` |

### Dockerfile Binary Bundling (ODE-4)

The Dockerfile supports three detection paths for OCP binaries:

```dockerfile
# Path 1: Pre-extracted binaries
if [ -f /tmp/ocp-bin/openshift-install ]; then
  cp /tmp/ocp-bin/openshift-install /usr/local/bin/
# Path 2: Pre-placed tarballs
elif [ -f /tmp/ocp-bin/openshift-install-linux.tar.gz ]; then
  tar xzf /tmp/ocp-bin/openshift-install-linux.tar.gz -C /usr/local/bin/
# Path 3: Internet download (connected only)
else
  curl -sL https://mirror.openshift.com/... | tar xzf -
fi
```

Mirror artifacts (`mirror-registry-amd64.tar.gz`, `oc-mirror-rhel9-linux-amd64.tar.gz`) are preserved at `/app/mirror-artifacts/` and copied to bastion by Ansible at runtime.

### AAP 2.5 Integration (ODE-5)

AAP deliverables enable running the SAME CPAT Ansible playbooks via Red Hat Ansible Automation Platform instead of the CPAT UI. Zero changes to the Ansible code.

**Execution Environment** — `ansible-builder` v3 definition based on `ee-minimal-rhel9:latest`:
- Python: `openpyxl==3.1.5` (CIQ parsing)
- System: `python3-devel`, `jq`, `openssh-clients`
- Binaries: `oc` + `openshift-install` from `binaries/` via `additional_build_steps`
- Custom modules loaded from project `library/` + `module_utils/` via `ansible.cfg`

**Custom Credential Types** (3):
- `CPAT Bastion SSH` — injects SSH key as temp file + user as extra var (`ocp_bastion_ssh_user`, `ocp_bastion_ssh_key_path`)
- `CPAT BMC Credentials` — injects `ocp_bmc_user`, `ocp_bmc_password` as extra vars
- `CPAT Pull Secret` — injects pull secret JSON as temp file, path via `ocp_pull_secret_path`

**OCP Job Templates** (2, ODE-5) — each with survey spec:
- `CPAT OCP Install` → `ocp_install.yml`, survey: `ocp_task` dropdown (26 choices from `OCP_INSTALLATION_TASK_TAGS`)
- `CPAT OCP Validate` → `ocp_validate.yml`

**OCP Workflow Templates** (3, ODE-5) — chain the same JT with different `extra_data` per node:
- `CPAT OCP ABI Full Install` — 11 nodes: prerequisites → ... → node_readiness
- `CPAT OCP ABI-DC Full Install` — 14 nodes: +3 mirror steps before install_config
- `CPAT OCP Destroy` — 1 node: destroy_cluster

**RHOSO Job Templates** (2, RDE-5) — see [agent-rhoso-deployment-engineer.md](agent-rhoso-deployment-engineer.md):
- `CPAT RHOSO Install` → `main.yml` with `--tags rhoso`, survey: `installation_task` dropdown (19 choices)
- `CPAT RHOSO Register` → `main.yml` with `--tags register`

**RHOSO Workflow Templates** (1, RDE-5):
- `CPAT RHOSO Full Install` — 19 nodes: manifest_generation → ... → observability

**Survey choices MUST stay in sync** with `OCP_INSTALLATION_TASK_TAGS` in `ansible_runner.py` (ODE-5) and `RHOSO_INSTALLATION_TASK_TAGS` (RDE-5). When a new OCP task is added, update `ocp-job-templates.yml` + `ocp-workflow-templates.yml`. When a new RHOSO task is added, update `rhoso-job-templates.yml` + `rhoso-workflow-templates.yml`.

**Import**: `awx-manage import < exports/all-objects.yml` (unified file) or individual files.

### Install Method Routing

The Ansible role MUST route tasks based on the `ocp_install_method` variable:

| Install Method | Tasks Executed |
|---------------|----------------|
| ABI | prerequisites → install_config (all 3) → ignition/create_agent_iso → ignition/boot_nodes_from_iso → bootstrap (smart media-eject) → cluster_config → validation |
| IPI-BM | prerequisites → install_config/generate_install_config → bootstrap → cluster_config → validation |
| UPI-BM | prerequisites → install_config/generate_install_config → ignition/generate_ignition_configs → bootstrap → cluster_config → validation |
| ABI-DC | prerequisites → mirror (all 3) → install_config (all 3) → ignition/create_agent_iso → ignition/boot_nodes_from_iso → bootstrap (smart media-eject) → cluster_config → validation |
| SNO | prerequisites → install_config (SNO variant) → ignition/create_agent_iso → ignition/boot_nodes_from_iso → bootstrap (smart media-eject) → cluster_config → validation |

## Rules
- Every new Ansible task file MUST be placed in the correct functional subdirectory under `tasks/`
- Every new Ansible task file MUST be tagged with its subdirectory path in `ansible_runner.py` OCP_INSTALLATION_TASK_TAGS
- All `include_tasks` paths within the role are relative to the role's `tasks/` directory — use `subdir/filename.yml` format
- Long-running commands MUST use `async/poll: 0` + `async_status until/retries` + `fetch` log pattern
- Long-running tasks MUST be registered in `OCP_TASK_COMMAND_LOGS` in `app.py`
- Sensitive tasks (pull-secret slurp/copy) MUST have `no_log: true`
- CIQ parsing: use unified `ciq_parser.py` with `ocp_ciq_schema.py` — auto-detects OCP from `ocp_details` table
- Jinja2 templates consume CIQ variables (prefixed `ocp_`) — NEVER hardcode cluster-specific values
- YAML version values in templates MUST be quoted strings to prevent float parsing
- Backend routes: add OCP routes alongside RHOSO routes in `app.py` — use `/ocp/` prefix
- Frontend: OCP installation is a SEPARATE tab/route from RHOSO — shared layout components
- Docker: Ansible role `ocp` is included alongside `rhoso` — both installable from same container
- NEVER invent parameters not in `ocp_ciq_schema.py`
- NEVER include actual secrets or passwords — use path references only
- Install method routing: use `when: ocp_install_method == 'ABI'` guards on task includes
- Disconnected tasks: include only when `ocp_is_disconnected | bool`
- OCP versions supported: 4.17, 4.18, 4.19, 4.20, 4.22 — version-specific logic via `ocp_version` variable
- Platform-specific tasks: guard with `ocp_platform` variable (baremetal/vsphere/none)
- Follow the same code patterns as the RHOSO role (ciq_parser.py, ansible_runner.py structure)
- All bastion SSH tasks use `delegate_to` with `hostvars[inventory_hostname]` for connection vars
- Uninstall tasks MUST protect the CPAT container (`--filter 'name!=cpat'`)
- `ansible.builtin.sysctl` module is NOT available in the CPAT container — use `shell: sysctl -w` + `sed` to persist
- Jinja `default()` filter does NOT trigger on empty strings — use `if (var | default('') | length > 0) else 'fallback'`
- `fqdn` schema type requires dot-separated domain — use `host_or_ip` for hostnames that may be single-label (e.g. `bastion`)
- HAProxy must bind to VIP IPs (not `*`) to avoid port conflicts with CPAT nginx on bastion
- Bastion SSH tasks MUST include `ansible_ssh_common_args: "-o StrictHostKeyChecking=no"` and `-o ServerAliveInterval=30 -o ServerAliveCountMax=10` for long-running tasks
- Boot nodes: query BMC power state BEFORE sending reset — `ForceRestart` on a stopped VM does nothing via sushy-tools
- Bootstrap async: ABI and IPI/UPI tasks MUST register to DIFFERENT variables to avoid Ansible skip-clobber
- Media eject: MUST eject virtual media after RHCOS disk-write 100% — sushy-tools ignores Hdd boot override
- AAP survey choices MUST be exact values from `OCP_INSTALLATION_TASK_TAGS` — adding a new OCP task requires updating `ansible_runner.py` AND `aap/exports/ocp-job-templates.yml` + `ocp-workflow-templates.yml` + `all-objects.yml`
- AAP workflow nodes use the SAME job template with different `extra_data` to override the task variable — never create separate JTs per task
- AAP credential types inject secrets as temp files via `injectors.file` — never as plain extra vars
