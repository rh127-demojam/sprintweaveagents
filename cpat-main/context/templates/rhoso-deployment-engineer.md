# RHOSO Deployment Engineer — Output Template
> This file is loaded on-demand by the RHOSO Deployment Engineer agent during generation.
> Do not edit the structure without updating the slim rule reference.

## CPAT Architecture

```
React UI -> Flask API -> Ansible Runner -> OpenShift (via kubeconfig)

Phases:
  Register  -> Store CIQ + secrets (kubeconfig, pull-secret, SSH key)
  Generate  -> Render YAML from CIQ into artifacts/<cluster>/ (no oc apply)
  Review    -> View/download manifests in Artifacts Panel
  Deploy    -> oc apply reviewed manifests from artifacts/<cluster>/
  Validate  -> oc get / openstack CLI smoke checks
```

## CIQ-to-CR Mapping (15 templates + 1 task → 100% RHOSO CR coverage)

| CIQ Table(s) | Generated CR / Manifest | Template / Task |
|-----------|------------------------|----------|
| `rhoso_control_plane` + `rhoso_networks` | `openstack_nncp.yaml` | `openstack_nncp.yaml.j2` |
| `rhoso_networks` | `openstack_nad.yaml` | `openstack_nad.yaml.j2` |
| `rhoso_networks` + `rhoso_control_plane` | `openstack_metallb.yaml` | `openstack_metallb.yaml.j2` |
| `rhoso_networks` | `openstack_netconfig.yaml` | `openstack_netconfig.yaml.j2` |
| `rhoso_control_plane` + `rhoso_services` + `rhoso_pv_sizing` + `rhoso_cinder_backend` + `rhoso_neutron_config` + `rhoso_ceph_storage` + `rhoso_networks` | `openstack_control_plane.yaml` (fully CIQ-driven, ~555 lines, Ceph RBD, Watcher, Swift/RGW) | `openstack_control_plane.yaml.j2` |
| `rhoso_edpm_network_config` | EDPM network_config (embedded in NodeSet) | `edpm_network_config_template.j2` |
| `rhoso_data_plane` + `rhoso_data_plane_nodes` + `rhoso_edpm_network_config` + `rhoso_ceph_storage` | `openstack_dataplane_nodeset.yaml` (Ceph extraMounts) | `openstack_dataplane_nodeset.yaml.j2` |
| `rhoso_data_plane` | `openstack_dataplane_deployment.yaml` | `openstack_dataplane_deployment.yaml.j2` |
| `rhoso_data_plane_nodes` (unprovisioned) | `openstack_baremetalhosts.yaml` + BMC Secrets | `openstack_baremetalhosts.yaml.j2` |
| `rhoso_data_plane_nodes` + `rhoso_networks` (unprovisioned) | NMState provisioning Secrets | `openstack_nmstate_secrets.yaml.j2` |
| `rhoso_edpm_network_config` (when CPU pinning set) | Nova CPU pinning ConfigMap | `openstack_nova_cpu_pinning_cm.yaml.j2` |
| `rhoso_ceph_storage` (when Ceph External=yes) | `ceph-conf-files` Secret (ceph.conf + keyring) | `generate_ceph_secret.yml` (task) |
| `rhoso_disconnected` | `catalog_source.yaml` | `catalog_source.yaml.j2` |
| `rhoso_disconnected` | `image_digest_mirror_set.yaml` | `image_digest_mirror_set.yaml.j2` |
| `rhoso_disconnected` | `image_tag_mirror_set.yaml` | `image_tag_mirror_set.yaml.j2` |
| `rhoso_disconnected` | `operatorhub_disable_defaults.yaml` | `operatorhub_disable_defaults.yaml.j2` |

## Workflow Phases and Ansible Tags

| Phase | UI Button | `execution_mode` | Ansible Tags | What Happens |
|-------|-----------|-----------------|--------------|-------------|
| Register | Register Cluster | — | `register` | CIQ + files stored; inventory created |
| Generate | Install (generate) | `generate` | `rhoso` (with `rhoso_skip_generation: false`) | Jinja->YAML into `artifacts/<cluster>/` |
| Review | (Artifacts Panel) | — | — | User views/downloads YAML |
| Deploy | Install (deploy) | `deploy` | `rhoso` (with `rhoso_apply_manifests: true`) | `oc apply` reviewed artifacts |
| Full | Install (full) | `full` | `rhoso` | Generate + Deploy in one pass |

## Manifest Catalog (artifacts/<cluster>/)

| # | File | CR Kind | Applied When | Source CIQ |
|---|------|---------|-------------|-----------|
| 1 | `openstack_nncp.yaml` | NodeNetworkConfigurationPolicy | Network Preparation | control_plane + networks |
| 2 | `openstack_nad.yaml` | NetworkAttachmentDefinition | Network Preparation | networks |
| 3 | `openstack_metallb.yaml` | IPAddressPool + L2Advertisement | Network Preparation | networks + control_plane |
| 4 | `openstack_netconfig.yaml` | NetConfig | Network Preparation | networks |
| 5 | `openstack_control_plane.yaml` | OpenStackControlPlane (fully CIQ-driven) | Control Plane Deploy | control_plane + CIQ context vars (services, replicas, PV, Cinder, Neutron) |
| 6 | `edpm_network_config_template.j2` | (embedded in NodeSet ansibleVars) | Data Plane Deploy | edpm_network_config |
| 7 | `openstack_dataplane_nodeset.yaml` | OpenStackDataPlaneNodeSet | Data Plane Deploy | data_plane + nodes + edpm |
| 8 | `openstack_dataplane_deployment.yaml` | OpenStackDataPlaneDeployment | Data Plane Deploy | data_plane |
| 9 | `openstack_baremetalhosts.yaml` | BareMetalHost + BMC Secrets | Data Plane Deploy (unprovisioned) | nodes |
| 10 | `openstack_nmstate_secrets.yaml` | NMState provisioning Secrets | Data Plane Deploy (unprovisioned) | nodes + networks |
| 11 | `openstack_nova_cpu_pinning_cm.yaml` | Nova CPU pinning ConfigMap | Data Plane Deploy (when CPU pinning set) | edpm_network_config |
| 12 | `catalog_source.yaml` | CatalogSource | Disconnected Prep | disconnected |
| 13 | `image_digest_mirror_set.yaml` | ImageDigestMirrorSet | Disconnected Prep | disconnected |
| 14 | `image_tag_mirror_set.yaml` | ImageTagMirrorSet | Disconnected Prep | disconnected |
| 15 | `operatorhub_disable_defaults.yaml` | OperatorHub patch | Disconnected Prep | disconnected |

## Cluster Commands by Phase

| Phase | Command | Purpose |
|-------|---------|---------|
| Pre-check | `oc get nodes` | Verify RHOCP cluster access |
| Pre-check | `oc get crd \| grep openstack` | Verify OpenStack Operator CRDs |
| Network | `oc get nncp` | Verify NNCP applied |
| Network | `oc get net-attach-def -n openstack` | Verify NADs created |
| Network | `oc get ipaddresspool -n metallb-system` | Verify MetalLB pools |
| Network | `oc get netconfig -n openstack` | Verify NetConfig |
| Control Plane | `oc get openstackcontrolplane -n openstack` | Check control plane status |
| Control Plane | `oc get pods -n openstack` | Verify service pods running |
| Data Plane | `oc get openstackdataplanenodeset -n openstack` | Check NodeSet status |
| Data Plane | `oc get openstackdataplanedeployment -n openstack` | Check deployment status |
| Validation | `openstack endpoint list` | Verify service endpoints |
| Validation | `openstack network list` | Verify Neutron networks |
| Validation | `openstack compute service list` | Verify Nova compute |

## RHOSO PDF References for Manual Steps

Steps documented in Red Hat PDFs but not automated by CPAT (cite in MoPs as manual prerequisites or post-steps):

| Topic | PDF | Chapter | When to Cite | Status |
|-------|-----|---------|-------------|--------|
| Service enable/disable (Heat, Horizon, Barbican, Octavia, etc.) | Customizing | Ch 3.10-3.11 | When user needs services beyond default | **NOW AUTOMATED** via `rhoso_services` CIQ table |
| Cinder backend (NetApp ONTAP, PowerFlex) | Persistent Storage | Ch 4 | When configuring Cinder storage | **NOW AUTOMATED** via `rhoso_cinder_backend` CIQ table |
| Glance backend (cinder, S3) | Persistent Storage | Ch 5 | When configuring Glance storage | **NOW AUTOMATED** via `rhoso_services` Glance Backend |
| Neutron MTU, OVN tuning | Customizing | Ch 3 | When customizing network config | **NOW AUTOMATED** via `rhoso_neutron_config` CIQ table |
| Nova CPU pinning | Customizing | Ch 3 | When configuring CPU-intensive workloads | **NOW AUTOMATED** via ConfigMap template |
| BareMetalHost NMState secrets | Deploying | Ch 5 | When provisioning bare-metal nodes | **NOW AUTOMATED** via NMState secrets template |
| Multi-cell configuration | Customizing | Ch 3.6-3.8 | When deploying compute cells | Partial (Cell1 replicas automated) |
| Ceph integration | Persistent Storage | Ch 3 | When storage backend is Ceph | **NOW AUTOMATED** via `rhoso_ceph_storage` CIQ table + `generate_ceph_secret.yml` task + Ceph `extraMounts` in ControlPlane/NodeSet templates |
| Swift deployment (Ceph RGW) | Persistent Storage | Ch 6-7 | When deploying Swift with Ceph RGW | **NOW AUTOMATED** via `rhoso_ceph_storage` (RGW Enabled/Endpoint/TLS) in ControlPlane template |
| Manila backend configuration | Persistent Storage | Ch 8 | When configuring Manila backends | Not automated |
| Tempest validation | Validating | Ch 2 | Post-deployment testing | Not automated (by design) |
| must-gather diagnostics | Validating | Ch 1 | Troubleshooting | Not automated (by design) |

---

## CPAT Source Code Generation

This section provides the CPAT project blueprint, file-by-file code patterns, and generation modes.
Use these patterns when scaffolding a new CPAT project or enhancing existing CPAT code.

### Generation Modes

**FRESH** — No existing CPAT codebase. Output: `sprintweave-output/cpat/` with complete project.
**ENHANCE** — Existing CPAT codebase. Output: `sprintweave-output/cpat-patch/` with only changed files + `CHANGES.md`.

### Pattern G: CPAT Project Blueprint

```
cpat/
  ansible/
    ansible.cfg
    playbooks/
      main.yml                              # Top-level playbook (tags: register, rhoso)
      roles/
        register/tasks/rhoso.yml            # Registration task
        rhoso/
          defaults/main.yml                 # Role defaults (all rhoso_ vars)
          tasks/                            # 22 task files
            main.yml                        # Dispatcher (includes installation_task.yml)
            _load_ciq_context.yml           # CIQ fact extraction (~156 lookups, all 15 tables)
            _validate_ciq.yml               # Schema validation
            _verify_required_crds.yml       # CRD pre-check
            _generate_control_plane_crs.yml # NNCP, NAD, MetalLB, NetConfig, ControlPlane
            _generate_data_plane_crs.yml    # NodeSet, Deployment, BareMetalHost
            _generate_disconnected_crs.yml  # CatalogSource, IDMS, ITMS, OperatorHub
            manifest_generation.yml         # Orchestrates all _generate_* + Ceph secret (tag: manifest_generation)
            prerequisites.yml               # (tag: prerequisites)
            prerequisite_operator_installation.yml  # NMState, MetalLB, Cert-Manager + HA Operators (NHC, SNR, FAR)
            generate_osp_secret.yml         # Generate osp-secret CR (tag: generate_osp_secret)
            generate_data_plane_secrets.yml # Generate 5 DP secrets (tag: generate_data_plane_secrets)
            generate_ceph_secret.yml        # Generate ceph-conf-files Secret when Ceph External=yes (tag: generate_ceph_secret)
            disconnected_environment_preparation.yml  # (tag: disconnected_environment_preparation)
            persistent_storage_configuration.yml      # (tag: persistent_storage_configuration)
            openstack_operator_installation_and_preparation.yml  # (tag: openstack_operator_...)
            rhocp_preparation_for_rhoso.yml           # (tag: rhocp_preparation_for_rhoso)
            network_preparation.yml                   # (tag: network_preparation)
            control_plane_deployment_and_verification.yml  # Ceph secret + ControlPlane CR (tag: control_plane_deployment_...)
            control_plane_customization.yml               # (tag: control_plane_customization)
            data_plane_deployment_and_verification.yml     # (tag: data_plane_deployment_...)
            post_deployment_validation.yml                # (tag: post_deployment_validation)
          templates/                        # 15 Jinja templates
            openstack_nncp.yaml.j2
            openstack_nad.yaml.j2
            openstack_metallb.yaml.j2
            openstack_netconfig.yaml.j2
            openstack_control_plane.yaml.j2          # Fully CIQ-driven (~555 lines, Ceph RBD, Watcher, Swift/RGW)
            edpm_network_config_template.j2
            openstack_dataplane_nodeset.yaml.j2
            openstack_dataplane_deployment.yaml.j2
            openstack_baremetalhosts.yaml.j2         # + BMC Secrets, bootMode, rootDeviceHints
            openstack_nmstate_secrets.yaml.j2        # NEW: per-node NMState provisioning secrets
            openstack_nova_cpu_pinning_cm.yaml.j2    # NEW: Nova CPU pinning ConfigMap
            catalog_source.yaml.j2
            image_digest_mirror_set.yaml.j2
            image_tag_mirror_set.yaml.j2
            operatorhub_disable_defaults.yaml.j2
    library/
      parse_ciq.py                          # Ansible module wrapping ciq_parser
      get_ciq_validation_schema.py          # Ansible module exposing schema
    module_utils/
      ciq_parser.py                         # Unified CIQ parser (RHOSO+OCP)
      rhoso_ciq_schema.py                   # RHOSO CIQ schema (COPY of ciq-generators/)
      ocp_ciq_schema.py                     # OCP CIQ schema (COPY of ciq-generators/)
  backend/
    app.py                                  # Flask routes
    ansible_runner.py                       # Playbook execution, task tags
    ciq_parser.py                           # CIQ XLSX parser
    models.py                               # SQLAlchemy models (Cluster, Execution)
    paths.py                                # Runtime data paths
    input_files.py                          # Upload file specs + save/load
    rhoso_ciq_schema.py                     # Re-export shim
    version.py                              # APP_VERSION
    requirements.txt                        # Flask, openpyxl, gunicorn, SQLAlchemy
    .gitignore                              # __pycache__, *.pyc, .env
  CIQTemplates/                             # Generated by RHOSO DA (see RDA template)
    generate_rhoso_ciq_workbooks.py         # Generic RHOSO CIQ (sample + template)
    generate_jio_rhoso_ciq.py              # JIO project CIQ (cloudmgmt + cloudxp)
    generate_core42_rhoso_ciq.py           # Core42 project CIQ (from HLD docs)
    generate_ocp_ciq_workbooks.py          # OCP 4.17 CIQ (install-config + agent-config)
    rhoso_ciq_schema.py
    requirements.txt
    README.md
    sample-rhoso.ciq.xlsx
    rhoso-ciq-template.xlsx
    JIO/                                    # JIO deployment artifacts (YAML manifests)
    CORE42/                                 # Core42 HLD documents (.docx, .pdf)
  LabRequirements/                          # Lab infrastructure requirements
    generate_lab_requirements_workbook.py   # Multi-sheet requirements generator
    requirements.txt
    lab-requirements.xlsx                   # Compute, network, NIC, storage, operators
  data/                                     # Runtime data (NOT source code)
    .gitignore                              # * then !.gitignore !README.md
    README.md                               # Documents runtime layout
  frontend/
    src/
      App.jsx                               # React Router + auth context
      api.js                                # Axios instance with /api/ base
      index.css                             # Global styles
      main.jsx                              # ReactDOM.createRoot entry
      components/
        Dashboard.jsx                       # Sidebar cluster list
        RegisterCluster.jsx                 # CIQ upload + cluster creation
        RhosoInstallation.jsx               # Task selection + SSE streaming
        ManifestArtifactsPanel.jsx           # Artifact viewer / download
        InputFilesModal.jsx                 # Drag-and-drop file upload
        ExecutionTable.jsx                  # Execution history list
        InstallationLogModal.jsx            # Live log viewer (SSE)
        RegistrationLogModal.jsx            # Registration log viewer
        Layout.jsx                          # Shell / navigation wrapper
        Login.jsx                           # Authentication form
        OcpDeploymentAutomation.jsx         # Top-level OCP route handler
      rhosoInputFiles.js                    # Input file field definitions
    nginx/
      default.conf                          # Reverse proxy config
    package.json                            # React + Vite dependencies
  RHOSO_Tasks/
    generate_rhoso_deployment_tasks_workbook.py  # Task brief generator
    requirements.txt
    README.md
    rhoso-deployment-overview.xlsx          # End-user brief
    rhoso-deployment-tasks.xlsx             # Technical brief
  docker/
    entrypoint.sh                           # Gunicorn + Nginx startup
  Dockerfile                                # Multi-stage (node + python)
  .dockerignore
  bringup.sh                                # Podman lifecycle
  README.md
  USAGE.md
```

### Pattern H: Ansible Task Files (22 files)

**File inventory with tags:**

| File | Tag | Purpose | Internal? |
|------|-----|---------|-----------|
| `main.yml` | (none) | Dispatcher: loads CIQ context, includes `{{ installation_task }}.yml` | No |
| `_load_ciq_context.yml` | (none) | Extracts all 15 CIQ tables (~156 lookups) into Ansible facts | Yes (underscore) |
| `_validate_ciq.yml` | (none) | Validates all CIQ fields against Python schema | Yes |
| `_verify_required_crds.yml` | (none) | Checks CRDs exist on cluster via `oc get crd` | Yes |
| `_generate_control_plane_crs.yml` | (none) | Generates NNCP, NAD, MetalLB, NetConfig, ControlPlane CRs | Yes |
| `_generate_data_plane_crs.yml` | (none) | Generates NodeSet, Deployment, BareMetalHost CRs | Yes |
| `_generate_disconnected_crs.yml` | (none) | Generates CatalogSource, IDMS, ITMS, OperatorHub CRs | Yes |
| `manifest_generation.yml` | `manifest_generation` | Orchestrates all `_generate_*` includes + Ceph secret | No |
| `prerequisites.yml` | `prerequisites` | Pre-deployment checks | No |
| `prerequisite_operator_installation.yml` | `prerequisite_operator_installation` | NMState, MetalLB, Cert-Manager + HA Operators (NHC, SNR, FAR) | No |
| `generate_osp_secret.yml` | `generate_osp_secret` | Generate osp-secret (19 passwords + fernet key) | No |
| `generate_data_plane_secrets.yml` | `generate_data_plane_secrets` | Generate 5 DP secrets (SSH, migration, sub, registry, libvirt) | No |
| `generate_ceph_secret.yml` | `generate_ceph_secret` | Generate ceph-conf-files Secret (Ceph External=yes) | No |
| `disconnected_environment_preparation.yml` | `disconnected_environment_preparation` | Mirror/CatalogSource setup | No |
| `persistent_storage_configuration.yml` | `persistent_storage_configuration` | Storage class verification | No |
| `openstack_operator_installation_and_preparation.yml` | `openstack_operator_installation_and_preparation` | Operator install + wait | No |
| `rhocp_preparation_for_rhoso.yml` | `rhocp_preparation_for_rhoso` | RHOCP prereqs for RHOSO | No |
| `network_preparation.yml` | `network_preparation` | Apply NNCP, NAD, MetalLB, NetConfig | No |
| `control_plane_deployment_and_verification.yml` | `control_plane_deployment_and_verification` | Apply Ceph secret + ControlPlane CR + wait | No |
| `control_plane_customization.yml` | `control_plane_customization` | Post-deploy service tuning | No |
| `data_plane_deployment_and_verification.yml` | `data_plane_deployment_and_verification` | Apply NodeSet/Deployment CRs | No |
| `post_deployment_validation.yml` | `post_deployment_validation` | Smoke tests (oc get, openstack CLI) | No |

**Task naming convention:**
```yaml
- name: Control-plane CRs -- generate NodeNetworkConfigurationPolicy
  ansible.builtin.template:
    src: openstack_nncp.yaml.j2
    dest: "{{ rhoso_manifest_dir }}/openstack_nncp.yaml"
    mode: "0644"
  delegate_to: localhost
```

Pattern: `<Role> CRs -- <verb> <CRKind>` with `delegate_to: localhost` for all file I/O.

**Key task patterns:**
```yaml
# Template rendering (generate phase)
- name: <Role> CRs -- generate <CRKind>
  ansible.builtin.template:
    src: <template>.yaml.j2
    dest: "{{ rhoso_manifest_dir }}/<output>.yaml"
    mode: "0644"
  delegate_to: localhost

# Manifest application (deploy phase)
- name: <Role> CRs -- apply <CRKind>
  ansible.builtin.command:
    cmd: oc apply -f {{ rhoso_manifest_dir }}/<file>.yaml
  when: rhoso_apply_manifests | bool

# Wait for resource readiness
- name: <Role> CRs -- wait for <resource> readiness
  ansible.builtin.command:
    cmd: oc wait --for=condition=Available <resource> --timeout={{ rhoso_wait_timeout }}
  register: wait_result
  until: wait_result.rc == 0
  retries: 3
  delay: 30

# CRD existence check
- name: Verify required CRDs -- {{ item.name }}
  ansible.builtin.command:
    cmd: oc get crd {{ item.name }}
  loop: "{{ rhoso_required_crds_control_plane + rhoso_required_crds_data_plane }}"
  register: crd_check
  failed_when: crd_check.rc != 0
```

**To add a new task file:**
1. Create `ansible/playbooks/roles/rhoso/tasks/<new_task>.yml`
2. Add tag entry to `RHOSO_INSTALLATION_TASK_TAGS` in `backend/ansible_runner.py`
3. Add to `RHOSO_DEPLOY_TASKS` or generate task list in `ansible_runner.py`
4. Add to frontend `RhosoInstallation.jsx` task selection array

### Pattern I: Jinja Templates (15 files)

**Template-to-CIQ variable mapping:**

| Template | Key Variables | Multi-Doc? | Conditional |
|----------|--------------|------------|-------------|
| `openstack_nncp.yaml.j2` | `rhoso_networks`, `rhoso_worker_iface` | Yes (per network) | Always |
| `openstack_nad.yaml.j2` | `rhoso_networks`, `rhoso_openstack_ns` | Yes (per network) | Always |
| `openstack_metallb.yaml.j2` | `rhoso_networks`, `rhoso_metallb_ns` | Yes (per network) | Always |
| `openstack_netconfig.yaml.j2` | `rhoso_networks`, `rhoso_openstack_ns` | No | Always |
| `openstack_control_plane.yaml.j2` | `rhoso_*` (TLS, DNS, Galera, RabbitMQ, messagingBus, notificationsBus, Keystone, Glance (Ceph RBD), Cinder (NetApp/Ceph RBD), Neutron (mac_binding_age_threshold), Nova (Ceph RBD ephemeral), Heat, Horizon, Barbican, Watcher, Swift (Ceph RGW), Telemetry, OVN, Octavia, Designate, Ironic, Manila, `rhoso_ceph_*`) | No | Always |
| `edpm_network_config_template.j2` | `rhoso_edpm_*` topology vars, `rhoso_networks` | No | Always |
| `openstack_dataplane_nodeset.yaml.j2` | `rhoso_nodes`, `rhoso_nodeset_name`, `rhoso_edpm_*` (OVN mappings, tuned profile, kernel args, bootstrap cmd) | No | Always |
| `openstack_dataplane_deployment.yaml.j2` | `rhoso_deployment_name`, `rhoso_nodeset_name` | No | Always |
| `openstack_baremetalhosts.yaml.j2` | `rhoso_nodes` (BMC address, bootMode, rootDeviceHints, preprovisioningNetworkDataName) + BMC Secrets | Yes (per node) | When unprovisioned |
| `openstack_nmstate_secrets.yaml.j2` | `rhoso_nodes` (Provisioning NIC/VLAN/IP), `rhoso_networks` (ctlplane), DNS servers | Yes (per node) | When unprovisioned |
| `openstack_nova_cpu_pinning_cm.yaml.j2` | `rhoso_edpm_cpu_dedicated_set`, `rhoso_edpm_reserved_host_memory_mb`, `rhoso_edpm_initial_cpu_allocation_ratio` | No | When CPU pinning set |
| `catalog_source.yaml.j2` | `rhoso_disconnected_*` | No | When disconnected |
| `image_digest_mirror_set.yaml.j2` | `rhoso_disconnected_*` | No | When disconnected |
| `image_tag_mirror_set.yaml.j2` | `rhoso_disconnected_*` | No | When disconnected |
| `operatorhub_disable_defaults.yaml.j2` | (no CIQ vars) | No | When disconnected |

**Multi-document YAML pattern:**
```jinja2
{% for net in rhoso_networks %}
---
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: {{ net['Network Name'] }}-{{ cluster_name }}
  namespace: {{ rhoso_openstack_ns }}
spec:
  desiredState:
    interfaces:
      # ...
{% endfor %}
```

**Conditional field pattern:**
```jinja2
{% if (rhoso_some_var | default('')) | length > 0 %}
  someField: {{ rhoso_some_var }}
{% endif %}
```

**Template naming:** `openstack_<resource>.yaml.j2` (exception: `edpm_network_config_template.j2`)

**To add a new CR template:**
1. Create `ansible/playbooks/roles/rhoso/templates/openstack_<resource>.yaml.j2`
2. Add rendering task to appropriate `_generate_*.yml` file
3. Update `_generate_control_plane_crs.yml` or `_generate_data_plane_crs.yml`
4. Add CRD check entry to `defaults/main.yml` if applicable

### Pattern J: Ansible Defaults (`defaults/main.yml`)

```yaml
# Mode flags
rhoso_apply_manifests: true
rhoso_skip_generation: false
rhoso_validate_ciq: true
rhoso_wait_timeout: 60m
rhoso_manifest_dir: "/cpat-data/artifacts/{{ cluster_name | default('rhoso') }}"

# CR naming
rhoso_control_plane_name: openstack-control-plane
rhoso_nodeset_name: openstack-data-plane
rhoso_deployment_name: data-plane-deploy
rhoso_osp_secret_name: osp-secret
rhoso_ansible_ssh_secret_name: dataplane-ansible-ssh-private-key-secret
rhoso_nova_migration_secret_name: nova-migration-ssh-key
rhoso_subscription_secret_name: subscription-manager
rhoso_libvirt_secret_name: libvirt-secret
rhoso_operator_channel: stable-v1.0
rhoso_operator_source: redhat-operators

# EDPM network defaults
rhoso_physical_bridge_name: br-ex
rhoso_edpm_net_topology: dual_nic_bond
rhoso_edpm_bridge_type: ovs_bridge
rhoso_edpm_nic1_name: nic1
rhoso_edpm_nic2_name: nic2
rhoso_edpm_bond_name: bond0

# Service enable/disable
rhoso_tls_pod_level: false
rhoso_dns_vip: ""
rhoso_dns_upstream_servers: ""
rhoso_worker_dns_servers: ""
rhoso_horizon_enabled: false
rhoso_heat_enabled: false
rhoso_barbican_enabled: false
rhoso_octavia_enabled: false
rhoso_designate_enabled: false
rhoso_ironic_enabled: false
rhoso_manila_enabled: false
rhoso_telemetry_enabled: false
rhoso_watcher_enabled: false
rhoso_fips_enabled: false

# Messaging / Notifications Bus
rhoso_messaging_bus_cluster: ""
rhoso_notifications_bus_cluster: ""

# Replicas (per-component, not per-service)
rhoso_dns_replicas: 1
rhoso_galera_replicas: 1
rhoso_galera_cell1_replicas: 1
rhoso_memcached_replicas: 1
rhoso_rabbitmq_replicas: 3
rhoso_rabbitmq_cell1_replicas: 3
rhoso_keystone_replicas: 1
rhoso_glance_replicas: 1
rhoso_glance_backend: ""
rhoso_cinder_api_replicas: 1
rhoso_cinder_scheduler_replicas: 1
rhoso_neutron_replicas: 1
rhoso_nova_api_replicas: 1
rhoso_nova_scheduler_replicas: 1
rhoso_nova_conductor_cell0_replicas: 1
rhoso_nova_conductor_cell1_replicas: 1
rhoso_nova_metadata_enabled: true
rhoso_nova_cell1_metadata_replicas: 1
rhoso_nova_cell1_novnc_replicas: 1
rhoso_placement_replicas: 1
rhoso_horizon_replicas: 1
rhoso_heat_api_replicas: 1
rhoso_heat_engine_replicas: 1
rhoso_barbican_api_replicas: 1
rhoso_barbican_worker_replicas: 1
rhoso_ovn_nb_replicas: 3
rhoso_ovn_sb_replicas: 3

# PV sizing
rhoso_galera_storage: "5G"
rhoso_galera_cell1_storage: "5G"
rhoso_ovn_nb_storage: "10G"
rhoso_ovn_sb_storage: "10G"
rhoso_telemetry_storage: ""
rhoso_telemetry_storage_class: ""
rhoso_telemetry_retention: "24h"
rhoso_telemetry_scrape_interval: "30s"
rhoso_rabbitmq_cpu_limit: ""
rhoso_rabbitmq_memory_limit: ""

# Cinder backend
rhoso_cinder_default_volume_type: ""
rhoso_cinder_volume_backend_name: ""
rhoso_cinder_volume_driver: ""
rhoso_cinder_storage_protocol: ""
rhoso_cinder_netapp_hostname: ""
rhoso_cinder_netapp_vserver: ""
rhoso_cinder_volume_secret: ""
rhoso_cinder_volume_net_attachments: ""

# Ceph storage (v1.3)
rhoso_ceph_external: false
rhoso_ceph_cluster_name: "ceph"
rhoso_ceph_fsid: ""
rhoso_ceph_mon_host: ""
rhoso_ceph_client_name: "openstack"
rhoso_ceph_client_key_path: ""
rhoso_ceph_pool_volumes: "volumes"
rhoso_ceph_pool_images: "images"
rhoso_ceph_pool_vms: "vms"
rhoso_ceph_rgw_enabled: false
rhoso_ceph_rgw_endpoint: ""
rhoso_ceph_rgw_tls_enabled: false

# Neutron config
rhoso_neutron_global_physnet_mtu: ""
rhoso_neutron_physical_network_mtus: ""
rhoso_neutron_api_timeout: ""
rhoso_ovn_emit_need_to_frag: ""
rhoso_mac_binding_age_threshold: ""

# HA Operators (v1.3)
rhoso_node_health_check_enabled: false
rhoso_self_node_remediation_enabled: false
rhoso_fence_agents_remediation_enabled: false

# EDPM performance tuning
rhoso_edpm_ovn_bridge_mappings: "datacentre:br-ex"
rhoso_edpm_tuned_profile: ""
rhoso_edpm_kernel_args: ""
rhoso_edpm_cpu_dedicated_set: ""
rhoso_edpm_reserved_host_memory_mb: ""
rhoso_edpm_initial_cpu_allocation_ratio: ""
rhoso_edpm_sshd_allowed_ranges: ""
rhoso_edpm_bootstrap_command: ""

# Disconnected
rhoso_disconnected_modes: [disconnected, airgapped, offline]
rhoso_wait_mcp_timeout: 45m

# CRD checklists (7 control plane + 4 data plane + 1 unprovisioned)
rhoso_required_crds_control_plane:
  - {name: openstacks.operator.openstack.org, kind: OpenStack, purpose: "..."}
  # ... 7 entries
rhoso_required_crds_data_plane:
  - {name: openstackdataplanenodesets.dataplane.openstack.org, ...}
  # ... 4 entries (includes openstackdataplaneservices CRD)
rhoso_required_crds_unprovisioned:
  - {name: baremetalhosts.metal3.io, kind: BareMetalHost, purpose: "..."}
```

**All variables use `rhoso_` prefix.** Never use unprefixed vars in the role.
**~163 default variables across 10 blocks** (mode flags, CR naming, EDPM, services, replicas, PV, Cinder, Ceph, Neutron, HA, disconnected, CRDs).

### Pattern K: Flask Backend (6 modules)

**`app.py` — Route inventory:**
```python
# Routes follow /api/ prefix pattern, all return jsonify()
@app.route("/api/login", methods=["POST"])
@app.route("/api/clusters", methods=["GET", "POST"])
@app.route("/api/clusters/<int:cluster_id>", methods=["GET", "DELETE"])
@app.route("/api/rhoso/install", methods=["POST"])  # SSE streaming
@app.route("/api/rhoso/executions/<int:cluster_id>", methods=["GET"])
@app.route("/api/clusters/<int:cluster_id>/artifacts", methods=["GET"])
@app.route("/api/clusters/<int:cluster_id>/artifacts/<filename>", methods=["GET"])
@app.route("/api/clusters/<int:cluster_id>/input-files", methods=["GET", "POST"])
@app.route("/api/version", methods=["GET"])

# SSE streaming pattern (for install):
def generate():
    for event_type, payload in stream_playbook(MAIN_PLAYBOOK, extra_vars, tags):
        yield f"data: {json.dumps({'type': event_type, **payload})}\n\n"
    return Response(generate(), mimetype="text/event-stream")
```

**`ansible_runner.py` — Task tag registry:**
```python
RHOSO_INSTALLATION_TASK_TAGS = {
    "Generate Manifests for Review": "manifest_generation",
    "Pre-requisites": "prerequisites",
    "Prerequisite Operator Installation": "prerequisite_operator_installation",
    "Generate OSP Secret": "generate_osp_secret",
    "Generate Data Plane Secrets": "generate_data_plane_secrets",
    "Generate Ceph Secret": "generate_ceph_secret",
    "Disconnected Environment Preparation": "disconnected_environment_preparation",
    "Persistent Storage Configuration": "persistent_storage_configuration",
    "OpenStack Operator Installation and Preparation": "openstack_operator_installation_and_preparation",
    "RHOCP Preparation for RHOSO": "rhocp_preparation_for_rhoso",
    "Network Preparation": "network_preparation",
    "Control Plane Deployment and Verification": "control_plane_deployment_and_verification",
    "Control Plane Customization": "control_plane_customization",
    "Data Plane Deployment and Verification": "data_plane_deployment_and_verification",
    "Post-Deployment Validation": "post_deployment_validation",
    # ... 16 entries total, UI display name -> Ansible tag
}
RHOSO_GENERATE_TASK = "Generate Manifests for Review"
RHOSO_DEPLOY_TASKS = [name for name in RHOSO_INSTALLATION_TASK_TAGS
                      if name != RHOSO_GENERATE_TASK]

def stream_playbook(playbook_path, extra_vars, tags=None) -> Iterator[tuple[str, Any]]:
    # subprocess.Popen with ansible-playbook, yields (event_type, payload)
```

**`models.py` — SQLAlchemy models:**
```python
class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    cluster_type = db.Column(db.String, default="rhoso")
    parameters = db.Column(db.Text)  # JSON
    nodes = db.Column(db.Text)       # JSON
    networks = db.Column(db.Text)    # JSON
    def to_dict(self): ...

class RhosoInstallationExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("cluster.id"))
    task_name = db.Column(db.String)
    execution_mode = db.Column(db.String)
    status = db.Column(db.String)
    log_path = db.Column(db.String)
    def to_dict(self): ...
```

**`paths.py` — Data directory layout:**
```python
DATA_DIR = _resolve_data_dir()     # <repo>/data (local) or /cpat-data (container)
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
SECRETS_DIR = os.path.join(DATA_DIR, "secrets")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
DATABASE_PATH = os.path.join(DATA_DIR, "cpat.db")

def ensure_data_dirs() -> None: ...          # mkdir -p all dirs
def cluster_artifacts_dir(name) -> str: ...  # artifacts/<safe-name>/
def list_cluster_artifacts(name) -> list: ...
def read_cluster_artifact(name, file) -> tuple: ...
```

**`version.py`:**
```python
APP_VERSION = os.environ.get("CPAT_VERSION", "25.7.4")
```

### Pattern L: React Frontend

**`App.jsx` — Router structure:**
```jsx
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="register" element={<RegisterCluster />} />
            <Route path="rhoso/:clusterId" element={<RhosoInstallation />} />
            <Route path="ocp" element={<OcpDeploymentAutomation />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}
```

**`api.js` — Axios instance:**
```javascript
import axios from 'axios';
const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
export default api;
```

**`RhosoInstallation.jsx` — Key structure:**
```jsx
const RHOSO_DEPLOY_TASKS = [
  "Pre-requisites",
  "Prerequisite Operator Installation",
  "Generate OSP Secret",
  "Generate Data Plane Secrets",
  "Generate Ceph Secret",
  "Disconnected Environment Preparation",
  "Persistent Storage Configuration",
  "OpenStack Operator Installation and Preparation",
  "RHOCP Preparation for RHOSO",
  "Network Preparation",
  "Control Plane Deployment and Verification",
  "Control Plane Customization",
  "Data Plane Deployment and Verification",
  "Post-Deployment Validation",
  // 16 tasks matching backend RHOSO_INSTALLATION_TASK_TAGS keys
];

function RhosoInstallation() {
  const [selectedTasks, setSelectedTasks] = useState([]);
  const [executionMode, setExecutionMode] = useState('generate');
  // SSE streaming via EventSource for live logs
  // ManifestArtifactsPanel integration for review phase
}
```

**Component patterns:**
- All components are functional with hooks (`useState`, `useEffect`, `useMemo`, `useCallback`)
- API calls use the shared `api` Axios instance
- SSE streaming via native `EventSource` for live log output
- `ManifestArtifactsPanel` displays generated YAML with expand/collapse

**`rhosoInputFiles.js` — Must sync with backend:**
```javascript
export const RHOSO_INPUT_FILE_FIELDS = [
  { field: 'kubeconfig', label: 'Kubeconfig', parameter: 'Kubeconfig Path',
    accept: '.kubeconfig,.yaml,.yml,text/plain,*/*', help: '...', recommended: true },
  // ... 5 entries, field names MUST match backend INPUT_FILE_SPECS keys
];
```

### Pattern M: Docker/Infra

**`Dockerfile` — Multi-stage build:**
```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + Nginx + Ansible
FROM python:3.12-slim
RUN apt-get update && apt-get install -y nginx ansible-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/
COPY ansible/ /app/ansible/
COPY CIQTemplates/ /app/CIQTemplates/
COPY RHOSO_Tasks/ /app/RHOSO_Tasks/
COPY --from=frontend-build /build/dist /app/static
COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
```

**`docker/entrypoint.sh`:**
```bash
#!/usr/bin/env bash
set -e
export CPAT_DATA_DIR="${CPAT_DATA_DIR:-/cpat-data}"
mkdir -p "$CPAT_DATA_DIR"
# Start gunicorn (Flask) on 127.0.0.1:5000
gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 600 app:app &
# Start nginx on port 80 (reverse proxy)
nginx -g 'daemon off;'
```

**`bringup.sh` — Podman lifecycle:**
```bash
#!/usr/bin/env bash
# Usage: ./bringup.sh [build|start|stop|restart|logs|shell]
IMAGE_NAME="cpat"
VERSION="YY.M.W"  # e.g. 25.7.4
CONTAINER_NAME="cpat"
DATA_VOLUME="cpat-data"
# Commands: podman build, podman run -d -p 8080:80 -v ..., podman stop, etc.
```

**`frontend/nginx/default.conf`:**
```nginx
server {
    listen 80;
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_buffering off;  # SSE streaming
    }
    location / {
        root /app/static;
        try_files $uri /index.html;
    }
}
```

### Pattern N: Runtime Data Directory (`data/`)

**Purpose:** Holds ALL mutable runtime state. Never source code.

**`data/.gitignore`:**
```
*
!.gitignore
!README.md
```

**`data/README.md`:**
```markdown
# CPAT Runtime Data

This directory holds all mutable runtime state for CPAT.
Created at startup by `paths.ensure_data_dirs()`.

| Path | Content |
|------|---------|
| `cpat.db` | SQLite database (clusters, installation executions) |
| `uploads/` | Registered CIQ .xlsx workbooks |
| `secrets/<cluster-id>/` | Uploaded kubeconfig, pull secrets, SSH keys (0600) |
| `logs/registrations/` | Registration execution logs |
| `logs/installations/` | RHOSO task execution logs |
| `artifacts/<cluster>/` | Generated OpenStack CR manifests for review |

Local dev: `<repo>/data/`  Container: `/cpat-data`
```

### Pattern O: RHOSO Deployment Tasks (`RHOSO_Tasks/`)

**`generate_rhoso_deployment_tasks_workbook.py`** generates two Excel workbooks:
- `rhoso-deployment-overview.xlsx` — End-user brief (sheets: cover, how_it_works, tasks, files_created, cluster_commands, glossary)
- `rhoso-deployment-tasks.xlsx` — Technical brief (sheets: cover, workflow, overview, shared_preamble, task_details, helpers, templates)

**Dependencies:** `openpyxl`
**Usage:** `python RHOSO_Tasks/generate_rhoso_deployment_tasks_workbook.py`

---

## Cross-File Integration Rules

```
CPAT Cross-File Sync Rules:
  rhoso_ciq_schema.py       -> EXISTS in both ansible/module_utils/ AND backend/
  INPUT_FILE_SPECS          -> Must match between backend/input_files.py AND frontend/rhosoInputFiles.js
  RHOSO_INSTALLATION_TASK_TAGS -> Must match between backend/ansible_runner.py AND frontend RHOSO_DEPLOY_TASKS
  Task file names           -> Must match tag slugs in ansible_runner.py (underscore-separated)
  Jinja var names           -> Must match facts set by _load_ciq_context.yml
  rhoso_ prefix             -> ALL Ansible role variables use this prefix
  CIQ table names           -> Must match between schema, parser, and workbook generator
  SCHEMA_VERSION            -> Must match between schema copies
```

---

## Output Formats

### FRESH Mode Output

```
sprintweave-output/
  cpat/
    ansible/          (complete Ansible role tree — 15 templates, 22 tasks, ~163 defaults, Ceph/HA/Watcher)
    backend/          (complete Flask application)
    CIQTemplates/     (CIQ schema + generators — generic, JIO, Core42, OCP)
    LabRequirements/  (lab requirements workbook generator)
    data/             (runtime dir — .gitignore + README.md only)
    frontend/         (complete React application)
    RHOSO_Tasks/      (deployment task workbook generator)
    docker/           (entrypoint.sh)
    Dockerfile
    .dockerignore
    bringup.sh
    README.md
    USAGE.md
```

### ENHANCE Mode Output

```
sprintweave-output/
  cpat-patch/
    <only new or modified files with their full directory paths>
    CHANGES.md        (summary of what was added/modified and why)
```

---

### 4. Output (Default: Markdown)

#### CPAT Workflow MoP

```markdown
## CPAT RHOSO Deployment Workflow: [Cluster Name]
**Source:** USAGE.md + Ansible roles | **Phases:** 5 | **Mode:** [connected/disconnected]
**EDPM Topology:** [topology] | **Provisioning:** [pre-provisioned/unprovisioned]

### Phase Overview
| # | Phase | CPAT Action | Key Manifests | Verification |
|---|-------|------------|---------------|-------------|
| 1 | Register | Upload CIQ + files | — | Cluster appears in dashboard |
| 2 | Generate | Click Install (generate) | [list] | Artifacts panel shows files |
| 3 | Review | Open Artifacts Panel | — | All YAML reviewed |
| 4 | Deploy | Click Install (deploy) | [list] | `oc get` shows resources |
| 5 | Validate | CLI checks | — | Endpoints responding |

### Phase 1: Register
**Action:** Upload CIQ workbook and input files via CPAT UI
**Files Required:**
| File | Purpose |
|------|---------|
| [CIQ xlsx] | Deployment parameters |
| [kubeconfig] | RHOCP cluster access |
| [pull-secret.json] | Registry auth |
| [SSH private key] | Data plane Ansible access |

**Verify:** Cluster name appears in CPAT sidebar
**Source:** USAGE.md Registration
```

#### Manifest Catalog

```markdown
## Manifest Catalog: [Cluster Name]
**Source:** Ansible roles + Jinja templates | **Files:** N | **Mode:** [connected/disconnected]

| # | File | CR Kind | Source CIQ | Applied Phase | oc verify |
|---|------|---------|-----------|--------------|-----------|
| 1 | [file] | [kind] | [tables] | [phase] | [command] |
```

#### Deployment Task Brief (High-Level)

```markdown
## RHOSO Deployment Overview: [Cluster Name]
**Source:** USAGE.md | **Audience:** End user / project manager
**Phases:** 5 | **Estimated Duration:** [X hours]

### Workflow
| Step | What | Who | Duration | Depends On |
|------|------|-----|----------|-----------|
| 1 | [action] | [role] | [time] | [prereqs] |
```

#### CPAT Source Code Scaffold Summary

```markdown
## CPAT Source Code Scaffold: [Project Name]
**Mode:** [FRESH / ENHANCE] | **Output:** sprintweave-output/cpat[-patch]/
**Files Generated:**
| Layer | Files | Key Patterns |
|-------|-------|-------------|
| Ansible Tasks | 22 | Template rendering, oc apply, wait loops, Ceph secret, HA operators |
| Ansible Templates | 15 | Multi-doc YAML, conditional fields, NMState secrets, CPU pinning CM, Ceph extraMounts |
| Ansible Defaults | 1 | rhoso_ prefixed vars (~163 defaults across 10 blocks) |
| Flask Backend | 8 | /api/ routes, SSE streaming, SQLAlchemy |
| React Frontend | 11 | Functional components, hooks, SSE EventSource |
| Docker/Infra | 4 | Multi-stage build, Nginx proxy |
| CIQ Generators | 5+ | Generic, JIO, Core42, OCP workbook generators |
| Lab Requirements | 2 | Multi-sheet compute/network/storage requirements |
| Runtime Data | 2 | .gitignore + README.md |
| RHOSO Tasks | 3 | Overview + technical Excel briefs |

**Total:** N files | **Cross-file sync rules:** 8
```

### 5. Excel Export (Always — Automatic)
After markdown output, generate a real `.xlsx` file:

1. Write artifact data to `sprintweave-output/<doc>-<timestamp>-data.json` using the schema from `00-sprintweave-excel-export.md` (sheets: "CPAT Workflow", "Manifest Catalog", "Deploy Tasks", "Cluster Commands", "CPAT Source Files")
2. Run: `python "tools/excel-generator.py" "sprintweave-output/<doc>-<timestamp>-data.json"`
3. Confirm file path to user

### 6. Quality Summary
```
RHOSO Deployment Engineer Quality:
  Artifacts: [Workflow MoP / Manifest Catalog / Task Brief / CPAT Scaffold / Code Enhancement]
  Mode: [FRESH / ENHANCE]
  Phases: 5 | All have verification: [yes/no]
  Manifests cataloged: N/15
  Commands listed: N | All have expected output: [yes/no]
  Source files generated: N | Layers: [Ansible/Backend/Frontend/Docker/Data/Tasks]
  Cross-file sync: N/8 rules verified
  Task brief type: [high-level / technical / both]
  Source traceability: N/N linked to USAGE/Ansible/PDF sections
  Manual steps cited: N (from Customizing/Storage PDFs)
  PII: Clean | Secrets: path refs only
  Source grounding: N [USAGE] | N [Ansible] | N [RHOSO PDF] | N [INFERRED]

Next steps:
  - Refine: "Add commands for [phase]"
  - Refine: "Show technical brief with Ansible task details"
  - Code: "Scaffold CPAT project from @cpat"
  - Code: "Add new Ansible task for [feature]"
  - Code: "Add React component for [feature]"
  - Handoff: "Review CIQ parameters for this cluster" (RHOSO DA)
  - Related: "Convert workflow to Ansible playbook" (Automation Engineer)
  - Related: "Generate test cases for deployment verification" (QA Architect)
  - Related: "Write admin guide for this deployment" (Technical Writer)
```

### 7. Gate Checkpoint (If Enabled)
If `gates.enabled: true` in team-config AND applicable per `00-sprintweave-gates.md`:
- Show gate checkpoint, wait for user approval before considering output final

## Iterative Refinement
- "Add phase details for [phase]"
- "Show manifest catalog for disconnected mode"
- "Add verification commands for [phase]"
- "Show technical task brief with Ansible coverage"
- "Add manual steps from [PDF name]"
- "Compare generate vs deploy execution modes"
- "Scaffold CPAT project from @cpat"
- "Add Ansible task for [feature]"
- "Add Jinja template for [CR kind]"
- "Add Flask route for [endpoint]"
- "Add React component for [feature]"

## JSON Format (On Request)
```json
{
  "cpat_workflow": {
    "cluster_name": "", "mode": "connected", "topology": "",
    "phases": [{
      "phase": 1, "name": "", "action": "", "manifests": [],
      "verification": [], "source": ""
    }]
  },
  "manifest_catalog": [{
    "file": "", "cr_kind": "", "source_ciq": [], "phase": "",
    "oc_verify": ""
  }],
  "deploy_tasks": [{
    "step": 1, "task": "", "role": "", "audience": "high-level",
    "duration": "", "depends_on": "", "source": ""
  }],
  "cluster_commands": [{
    "phase": "", "command": "", "purpose": "", "expected_output": ""
  }],
  "cpat_source_files": [{
    "file": "", "layer": "", "purpose": "", "pattern": "",
    "sync_with": ""
  }]
}
```
