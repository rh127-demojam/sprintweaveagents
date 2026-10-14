# CPAT — RHOSO Deployment Guide

Detailed documentation for **Red Hat OpenStack Services on OpenShift (RHOSO) 18.0**
deployment using CPAT.

> RHOSO runs on top of an existing OCP cluster. Install OCP first.
> See [README-OCP.md](README-OCP.md) for OCP installation.

**RHOSO CIQ Schema:** v1.4 — 18 tables, ~210 parameters, 20 dropdown lists

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [RHOSO Install Workflow](#rhoso-install-workflow)
- [Installation Tasks (19)](#installation-tasks-19)
- [Prerequisite Operators](#prerequisite-operators)
- [CIQ Parameter Reference (18 Tables)](#ciq-parameter-reference-18-tables)
- [Manifest Catalog (15 Templates)](#manifest-catalog-15-templates)
- [Input Files Reference](#input-files-reference)
- [CIQ Workbook Structure](#ciq-workbook-structure)
- [Ansible Role Structure](#ansible-role-structure)
- [API Reference (RHOSO Endpoints)](#api-reference-rhoso-endpoints)
- [Manual CLI Usage](#manual-cli-usage)

---

## Prerequisites

RHOSO deployment requires a **running OCP cluster** (installed via CPAT or manually).

| Prerequisite | Description |
|--------------|-------------|
| Running RHOCP cluster | OCP 4.14+ with cluster-admin access |
| Bastion / host with Podman | Linux host with network access to OCP API |
| Kubeconfig | cluster-admin kubeconfig file (path provided in CIQ) |
| Pull secret | Red Hat registry pull-secret.json (path provided in CIQ) |
| SSH key to compute nodes | Private key for Ansible SSH access to EDPM nodes |
| Network connectivity | Bastion must reach OCP API and EDPM node IPs |
| EDPM compute nodes | RHEL 9.x hosts with SSH access for data plane |

CPAT does **not** install OCP, provision the bastion, or manage network infrastructure.

---

## RHOSO Install Workflow

### Generate → Review → Deploy

```
1. Register RHOSO cluster    Upload RHOSO CIQ workbook (.xlsx)
       ↓                     Parser reads rhoso_details table (Type=RHOSO)
2. Generate Manifests        Renders NNCP, NAD, MetalLB, NetConfig,
       ↓                     ControlPlane, DataPlane CRs from CIQ
3. Review                    View YAML in UI or download ZIP
       ↓
4. Deploy Tasks              Execute tasks sequentially via Web UI
       ↓                     Real-time NDJSON log streaming
5. RHOSO Ready               openstack endpoint list → All services active
```

**API flow:**
```
POST /api/clusters/register              → Upload CIQ
POST /api/rhoso-installations/run        → Start tasks (NDJSON stream)
GET  /api/rhoso-installations/<id>       → Check status
GET  /api/clusters/<id>/artifacts        → List manifests
```

### Execution modes

| Mode | API value | Behavior |
|------|-----------|----------|
| Generate | `generate` | Render templates only (no `oc apply`) |
| Deploy | `deploy` | Apply previously generated manifests |
| Full | `full` | Generate + apply in one pass |

Optional flag: `re_render_manifests` — regenerate templates before applying.

---

## Installation Tasks (19)

CPAT provides **19 RHOSO installation tasks** (1 generate + 18 deploy) mapped to
Ansible task files via `INSTALLATION_TASK_TAGS` in `backend/ansible_runner.py`.

### Task summary

| # | UI Task | Ansible Task File | Description |
|---|---------|-------------------|-------------|
| 0 | Generate Manifests for Review | `manifest_generation.yml` | Render all CRs from CIQ (no apply) |
| 1 | Pre-requisites | `prerequisites.yml` | Validate CIQ, kubeconfig, pull secret, cluster-admin |
| 2 | Verify Required CRDs | `_verify_required_crds.yml` | Check OpenStack CRDs exist |
| 3 | Prerequisite Operator Installation | `prerequisite_operator_installation.yml` | Install NMState, MetalLB, Cert-Manager |
| 4 | Disconnected Environment Preparation | `disconnected_environment_preparation.yml` | CatalogSource, IDMS/ITMS, OperatorHub patch |
| 5 | Generate OSP Secret | `generate_osp_secret.yml` | Create osp-secret with 19 service passwords |
| 6 | Generate Data Plane Secrets | `generate_data_plane_secrets.yml` | SSH key, subscription, nova-migration secrets |
| 7 | Generate Ceph Secret | `generate_ceph_secret.yml` | Ceph client keyring secret (when Ceph external) |
| 8 | Persistent Storage Configuration | `persistent_storage_configuration.yml` | Configure StorageClass for Galera, OVN, telemetry |
| 9 | Trident Storage Configuration | `trident_storage_configuration.yml` | TridentBackendConfig + StorageClass (when Trident) |
| 10 | Generate Storage CRs | `_generate_storage_crs.yml` | Render Trident/LSO manifests |
| 11 | OpenStack Operator Installation | `openstack_operator_installation_and_preparation.yml` | Subscription, InstallPlan, OpenStack init CR |
| 12 | RHOCP Preparation for RHOSO | `rhocp_preparation_for_rhoso.yml` | Namespace, privileged labels, osp-secret |
| 13 | Network Preparation | `network_preparation.yml` | NNCP, NAD, MetalLB IPAddressPool, NetConfig |
| 14 | Control Plane Deployment | `control_plane_deployment_and_verification.yml` | Apply OpenStackControlPlane CR, wait for ready |
| 15 | Control Plane Customization | `control_plane_customization.yml` | Post-deploy tuning (Horizon, Barbican, services) |
| 16 | Data Plane Deployment | `data_plane_deployment_and_verification.yml` | NodeSet + Deployment CRs, wait for EDPM ready |
| 17 | Post-Deployment Validation | `post_deployment_validation.yml` | Verify services, endpoints, compute availability |
| 18 | Observability Configuration | `observability_configuration.yml` | MonitoringStack CR (when Observability enabled) |

---

## Prerequisite Operators

Task 3 installs these operators before RHOSO deployment:

| Operator | Namespace | Channel | Purpose |
|----------|-----------|---------|---------|
| **Kubernetes NMState** | `openshift-nmstate` | `stable` | Worker NIC / VLAN configuration via NNCP |
| **MetalLB** | `metallb-system` | `stable` | L2 VIP advertisement for RHOSO services |
| **Cert-Manager** | `cert-manager-operator` | `stable-v1` | TLS certificate management |

Optional operators (enabled via CIQ service flags):

| Operator | CIQ Flag | Purpose |
|----------|----------|---------|
| Local Storage Operator | `LSO Enabled` | Local disk PV provisioning |
| Cluster Observability Operator | `Observability Enabled` | Prometheus monitoring stack |
| NetApp Trident CSI | `Trident Enabled` | NetApp ONTAP dynamic PV provisioning |
| Node Health Check | `Node Health Check Operator Enabled` | HA node failure detection |
| Self Node Remediation | `Self Node Remediation Operator Enabled` | Automated self-healing reboot |
| Fence Agents Remediation | `Fence Agents Remediation Operator Enabled` | BMC-based fencing for HA |

---

## CIQ Parameter Reference (18 Tables)

The RHOSO CIQ workbook contains **18 named Excel tables** (16 parameter + 2 row tables).
The backend parser discovers tables via `ws.tables.values()` and matches by `displayName`.

### Table overview

| # | Excel Table Name | Sheet | Params | Description |
|---|-----------------|-------|--------|-------------|
| 1 | `rhoso_details` | Environment | 11 | Cluster identity, version, deployment mode |
| 2 | `rhoso_access` | Environment | 3 | Kubeconfig, API URL, pull secret paths |
| 3 | `rhoso_disconnected` | Environment | 16 | Mirror registry, IDMS, CatalogSource |
| 4 | `rhoso_storage` | Storage | 2 | Default StorageClass, backend |
| 5 | `rhoso_ceph_storage` | Storage | 12 | External Ceph cluster config |
| 6 | `rhoso_trident_storage` | Storage | 12 | NetApp Trident CSI config |
| 7 | `rhoso_lso_storage` | Storage | 7 | Local Storage Operator config |
| 8 | `rhoso_cinder_backend` | Storage | 8 | Cinder storage backend |
| 9 | `rhoso_multipath` | Storage | 4 | iSCSI/FC multipath config |
| 10 | `rhoso_control_plane` | Control Plane | 27 | Control plane CRs, VIPs, networking |
| 11 | `rhoso_services` | Control Plane | 35 | Service enable flags + replicas |
| 12 | `rhoso_observability` | Control Plane | 5 | Cluster Observability Operator |
| 13 | `rhoso_pv_sizing` | Control Plane | 10 | PV sizes for Galera, OVN, telemetry |
| 14 | `rhoso_neutron_config` | Control Plane | 5 | Neutron MTU, MAC binding |
| 15 | `rhoso_edpm_network_config` | Data Plane | 24 | EDPM bridge, topology, bond, DPDK |
| 16 | `rhoso_data_plane` | Data Plane | 14 | NodeSet, deployment, SSH, subscription |
| 17 | `rhoso_networks` | Networks | 16 cols | Network definitions (row table) |
| 18 | `rhoso_data_plane_nodes` | Data Plane | 16 cols | Compute node inventory (row table) |

### 1. RHOSO Details (`rhoso_details`) — 11 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Cluster Name | cluster_name | Yes | Unique RHOSO deployment name |
| Type | enum | Yes | Must be `RHOSO` |
| Environment | enum | Yes | lab, test, staging, prod, development |
| RHOSO Version | version | Yes | 18.0 |
| RHOCP Version | version | Yes | 4.14–4.18 |
| Deployment Mode | enum | Yes | connected, disconnected, airgapped, offline |
| Multi Environment on Single RHOCP | yes/no | Yes | Multiple RHOSO envs on one OCP |
| OpenStack Namespace | k8s_name | Yes | Namespace for services (e.g. openstack) |
| OpenStack Operators Namespace | k8s_name | Yes | Namespace for operators |
| FIPS Enabled | yes/no | No | FIPS 140-3 compliance |
| Description | free_text | No | Deployment description |

### 2. RHOSO Access (`rhoso_access`) — 3 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Kubeconfig Path | unix_path | Yes | Absolute path to kubeconfig |
| RHOCP API URL | https_url | No | OCP API endpoint |
| Pull Secret Path | unix_path | Yes | Path to pull-secret.json |

### 3. RHOSO Disconnected (`rhoso_disconnected`) — 16 params

Required when Deployment Mode = disconnected / airgapped / offline.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Mirror Registry URL | registry_host | Yes | Local mirror registry host:port |
| Mirror Registry CA Path | unix_path | No | Mirror registry CA certificate |
| Mirror Pull Secret Path | unix_path | No | Pull secret for mirror registry |
| ImageDigestMirrorSet Name | k8s_name | No | IDMS resource name |
| ImageTagMirrorSet Name | k8s_name | No | ITMS resource name |
| ImageContentSourcePolicy Name | k8s_name | No | ICSP name (deprecated) |
| Disable Default CatalogSources | yes/no | No | Disable default OperatorHub catalogs |
| CatalogSource Name | k8s_name | Yes | Mirrored CatalogSource name |
| CatalogSource Namespace | k8s_name | Yes | CatalogSource namespace |
| CatalogSource Image | image_ref | Yes | Mirrored operator index image |
| Operator Source | k8s_name | Yes | CatalogSource for Subscriptions |
| Operator Source Namespace | k8s_name | No | Operator source namespace |
| Mirrored Registry OpenStack Path | registry_path | No | Registry path for OpenStack images |
| Data Plane Container Registry | registry_host | No | Registry for EDPM containers |
| Data Plane YUM Mirror URL | http_url | No | YUM mirror for RHEL packages |
| Satellite Capsule URL | https_url | No | Red Hat Satellite endpoint |

### 4. RHOSO Storage (`rhoso_storage`) — 2 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Storage Class | k8s_name | Yes | Default StorageClass for PVCs |
| Storage Backend | enum | No | Ceph, NFS, LSO, NetApp ONTAP, LVM Storage |

### 5. RHOSO Ceph Storage (`rhoso_ceph_storage`) — 12 params

Greyed out when Ceph External ≠ yes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Ceph External | yes/no | No | Use external Ceph cluster |
| Ceph Cluster Name | free_text | No | Ceph cluster name (default: ceph) |
| Ceph FSID | free_text | No | Ceph cluster UUID |
| Ceph Mon Host | free_text | No | Monitor host IPs (comma-separated) |
| Ceph Client Name | free_text | No | Auth user (e.g. openstack) |
| Ceph Client Key Path | unix_path | No | Path to Ceph keyring |
| Ceph Pool Volumes | free_text | No | RBD pool for Cinder volumes |
| Ceph Pool Images | free_text | No | RBD pool for Glance images |
| Ceph Pool VMs | free_text | No | RBD pool for Nova ephemeral disks |
| Ceph RGW Enabled | yes/no | No | Enable RADOS Gateway |
| Ceph RGW Endpoint | http_url | No | RGW endpoint URL |
| Ceph RGW TLS Enabled | yes/no | No | TLS for RGW |

### 6. RHOSO Trident Storage (`rhoso_trident_storage`) — 12 params

Greyed out when Trident Enabled ≠ yes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Trident Enabled | yes/no | No | Enable NetApp Trident CSI |
| Trident Image Registry | registry_host | No | Container registry for Trident |
| Trident Image | image_ref | No | Trident controller image |
| Trident Autosupport Image | image_ref | No | Trident autosupport image |
| Trident Backend Name | free_text | No | TridentBackendConfig name |
| Trident Storage Driver Name | free_text | No | ontap-san, ontap-nas, etc. |
| Trident Management LIF | host_or_ip | No | ONTAP management LIF |
| Trident Data LIF | host_or_ip | No | ONTAP data LIF |
| Trident SVM | free_text | No | ONTAP Storage Virtual Machine |
| Trident Secret Name | k8s_name | No | K8s Secret with ONTAP credentials |
| Trident Storage Class Name | k8s_name | No | StorageClass from Trident |
| Trident Volume Binding Mode | free_text | No | Immediate / WaitForFirstConsumer |

### 7. RHOSO LSO Storage (`rhoso_lso_storage`) — 7 params

Greyed out when LSO Enabled ≠ yes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| LSO Enabled | yes/no | No | Enable Local Storage Operator |
| LSO Storage Class Name | k8s_name | No | StorageClass from LSO |
| LSO Device Types | free_text | No | Device types (disk, part) |
| LSO Device Mechanical Properties | free_text | No | NonRotational / Rotational |
| LSO Min Device Size | free_text | No | Minimum device size (e.g. 100Gi) |
| LSO Volume Mode | free_text | No | Block / Filesystem |
| LSO Node Selector Label | free_text | No | Node label for LSO discovery |

### 8. RHOSO Cinder Backend (`rhoso_cinder_backend`) — 8 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Cinder Default Volume Type | free_text | No | Default volume type name |
| Cinder Volume Backend Name | free_text | No | Backend name in cinder.conf |
| Cinder Volume Driver | free_text | No | Driver class path |
| Cinder Storage Protocol | free_text | No | nfs, iscsi, fc, nvme-tcp |
| Cinder NetApp Server Hostname | host_or_ip | No | NetApp management IP |
| Cinder NetApp Vserver | free_text | No | NetApp SVM name |
| Cinder Volume Secret Name | k8s_name | No | K8s Secret for backend credentials |
| Cinder Volume Network Attachments | free_text | No | NADs for storage network |

### 9. RHOSO Multipath (`rhoso_multipath`) — 4 params

Greyed out when Multipath Enabled ≠ yes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Multipath Enabled | yes/no | No | Enable multipath for iSCSI/FC |
| Multipath Config Secret Name | k8s_name | No | K8s Secret with multipath.conf |
| Multipath User Friendly Names | yes/no | No | Human-readable device names |
| Multipath Find Multipaths | yes/no | No | Auto-detect multipaths |

### 10. RHOSO Control Plane (`rhoso_control_plane`) — 27 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Control Plane CR Name | k8s_name | Yes | OpenStackControlPlane CR name |
| Control Plane FQDN | fqdn | No | Public FQDN for API endpoints |
| Public VIP | ipv4 | No | Public-facing virtual IP |
| OSP Secret Name | k8s_name | Yes | osp-secret with service passwords |
| Management Network Name | dns_label | No | Override management network name |
| Internal API Network Name | dns_label | No | Override internal API network name |
| MetalLB Namespace | k8s_name | Yes | MetalLB namespace (metallb-system) |
| NAD CNI Version | cni_version | Yes | CNI spec version (e.g. 0.3.1) |
| Internal API VIP | ipv4 | No | VIP for Internal API |
| Cell1 RabbitMQ VIP | ipv4 | No | VIP for Cell1 RabbitMQ |
| RabbitMQ VIP | ipv4 | No | VIP for default RabbitMQ |
| Glance/Cinder/Neutron/Nova/Placement Internal VIP | ipv4 | No | Per-service VIPs |
| Datacentre NIC | iface | No | NIC for br-ex on workers |
| Public Interface | iface | No | External-facing NIC |
| Worker NNCP Interface | iface | Yes | NIC for NNCP VLAN sub-interfaces |
| OVN Gateway Placement | enum | Yes | control-plane / data-plane / networker |
| TLS Pod Level Enabled | yes/no | No | Enable inter-pod TLS |
| Operator Channel | free_text | No | OLM channel |
| Operator Install Plan Approval | free_text | No | Manual / Automatic |
| DNS VIP | ipv4 | No | VIP for Designate DNS |
| DNS Upstream Servers | free_text | No | Upstream DNS servers |
| Worker DNS Servers | free_text | No | DNS for worker nodes |
| Messaging Bus Cluster | k8s_name | No | RabbitMQ cluster name |
| Notifications Bus Cluster | k8s_name | No | Notifications RabbitMQ name |

### 11. RHOSO Services (`rhoso_services`) — 35 params

Service enable flags and per-service replica counts.

| Parameter | Type | Description |
|-----------|------|-------------|
| Horizon/Heat/Telemetry/Barbican/Octavia/Designate/Ironic/Manila/Watcher Enabled | yes/no | Enable respective service |
| Node Health Check/Self Node Remediation/Fence Agents Remediation Operator Enabled | yes/no | HA operator flags |
| LSO Enabled / Observability Enabled / Trident Enabled | yes/no | Prerequisite operator flags |
| Glance Backend | free_text | PVC, cinder, swift, file |
| Glance/Nova API/Nova Scheduler/Neutron/Keystone/Cinder API/Cinder Scheduler Replicas | integer | Per-service replicas |
| Nova Conductor Cell0/Cell1 Replicas | integer | Conductor replicas per cell |
| Nova Metadata Enabled / Nova Cell1 Metadata/noVNC Replicas | yes/no + integer | Metadata service |
| Barbican API/Worker / Placement / Horizon / Heat API/Engine Replicas | integer | More service replicas |
| Memcached / Galera / Galera Cell1 / RabbitMQ / RabbitMQ Cell1 / DNS Replicas | integer | Infrastructure replicas |
| OVN NB / OVN SB Replicas | integer | OVN database replicas |

### 12. RHOSO Observability (`rhoso_observability`) — 5 params

Greyed out when Cluster Observability Enabled ≠ yes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Cluster Observability Enabled | yes/no | No | Enable Cluster Observability Operator |
| Observability Operator Channel | free_text | No | OLM channel |
| Observability Install Plan Approval | free_text | No | Automatic / Manual |
| Observability Monitoring Stack Enabled | yes/no | No | Deploy MonitoringStack CR |
| Observability Monitoring Stack Name | k8s_name | No | MonitoringStack instance name |

### 13. RHOSO PV Sizing (`rhoso_pv_sizing`) — 10 params

| Parameter | Type | Description |
|-----------|------|-------------|
| Galera Storage Request | free_text | PVC size for Galera (e.g. 50Gi) |
| Galera Cell1 Storage Request | free_text | PVC size for Cell1 Galera |
| OVN NB / SB Storage Request | free_text | PVC size for OVN databases |
| Telemetry Storage Request / Class / Retention / Scrape Interval | free_text | Telemetry PV config |
| RabbitMQ CPU / Memory Limit | free_text | RabbitMQ resource limits |

### 14. RHOSO Neutron Config (`rhoso_neutron_config`) — 5 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Neutron Global Physnet MTU | integer | No | Global physical network MTU |
| Neutron Physical Network MTUs | free_text | No | Per-physnet MTU overrides |
| Neutron API Timeout | integer | No | API request timeout (seconds) |
| OVN Emit Need To Frag | yes/no | No | Enable OVN fragmentation ICMP |
| MAC Binding Age Threshold | integer | No | OVN MAC binding age (0 for RHOSO 18.0) |

### 15. RHOSO EDPM Network Config (`rhoso_edpm_network_config`) — 24 params

| Parameter | Type | Required | When | Description |
|-----------|------|----------|------|-------------|
| Physical Bridge Name | iface | Yes | Always | OVS bridge (default: br-ex) |
| EDPM Network Config Topology | enum | Yes | Always | single_nic_vlans, dual_nic_bond, ovs_bond, linux_bond, ovs_dpdk |
| EDPM Network Config Nmstate | yes/no | Yes | Always | Use NMState for network config |
| EDPM Network Config Update | yes/no | Yes | Always | Allow network config updates |
| EDPM Bridge Type | enum | Yes | Always | ovs_bridge / ovs_user_bridge |
| EDPM NIC1 Name | iface | Yes | Always | Primary NIC |
| EDPM NIC2 Name | iface | Yes | Bond only | Secondary NIC for bonding |
| EDPM Bond Name | iface | Yes | Bond only | Bond interface name |
| EDPM Bonding Options | bonding | No | Bond only | e.g. mode=802.3ad lacp_rate=fast |
| EDPM Use DHCP / DHCPv6 | yes/no | Yes | Always | Enable DHCP on management |
| EDPM DPDK MTU / RX Queue / OVS Extra | various | DPDK | DPDK only | DPDK-specific settings |
| NTP Servers | ntp_list | No | Always | Comma-separated NTP hostnames |
| Registry Secret Name | k8s_name | No | Always | Container registry auth |
| EDPM OVN Bridge Mappings / Tuned Profile / Kernel Args | free_text | No | Always | Performance tuning |
| EDPM CPU Dedicated Set / Reserved Host Memory MB / CPU Allocation Ratio | various | No | Always | CPU/memory tuning |
| EDPM SSHD Allowed Ranges / Bootstrap Command | free_text | No | Always | SSH hardening, pre-deploy |

### 16. RHOSO Data Plane (`rhoso_data_plane`) — 14 params

| Parameter | Type | Required | When | Description |
|-----------|------|----------|------|-------------|
| Data Plane NodeSet Name | k8s_name | Yes | Always | OpenStackDataPlaneNodeSet CR name |
| Data Plane Deployment Name | k8s_name | Yes | Always | OpenStackDataPlaneDeployment CR name |
| Data Plane Provisioning Mode | enum | Yes | Always | pre-provisioned / unprovisioned |
| Data Plane SSH User | username | Yes | Always | SSH user on compute nodes |
| Data Plane SSH Private Key Path | unix_path | Yes | Always | SSH private key path |
| Data Plane Ansible EE Image | image_ref | No | Always | Custom Ansible EE image |
| Ansible SSH / Nova Migration / Subscription / Libvirt Secret Name | k8s_name | Yes | Always | K8s Secret names |
| Subscription Method | enum | Yes | Always | activation_key / username_password |
| Red Hat Organization ID | org_id | Yes | activation_key | Org ID for activation key |
| Red Hat Activation Key | activation_key | Yes | activation_key | Activation key name |
| Red Hat Username | username | Yes | username_password | Portal username |

### 17. RHOSO Networks (`rhoso_networks`) — 16 columns (row table)

One row per network (ctlplane, internalapi, storage, tenant, external, etc.).

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Network Name | dns_label | Yes | Unique network name |
| CIDR | cidr | Yes | Network CIDR (e.g. 172.17.0.0/24) |
| VLAN | vlan | No | 802.1Q VLAN ID (1–4094) |
| Gateway | ipv4 | No | Default gateway |
| MTU | mtu | Yes | Network MTU |
| Purpose | enum | Yes | Control plane, Internal API, Storage, Tenant, External |
| DNS Domain | dns_domain | Yes | DNS domain suffix |
| Subnet Name | dns_label | Yes | NetConfig subnet name |
| Allocation Start / End | ipv4 | Yes | NetConfig IPAM range |
| Whereabouts Start / End | ipv4 | Yes | Whereabouts IPAM range |
| MetalLB Start / End | ipv4 | No | MetalLB VIP pool |
| NAD Master Interface | iface | Yes | Host interface for NAD |
| NAD Type | enum | Yes | macvlan, bridge, ipvlan |

### 18. RHOSO Data Plane Nodes (`rhoso_data_plane_nodes`) — 16 columns (row table)

One row per compute/networker node.

| Column | Type | Required | When | Description |
|--------|------|----------|------|-------------|
| Node Name | dns_label | Yes | Always | Compute node hostname |
| Ansible Host | host_or_ip | Yes | Pre-provisioned | SSH target IP |
| Role | enum | Yes | Always | compute, networker, compute-networker |
| Management IP | ipv4 | Yes | Pre-provisioned | Management network IP |
| NIC1 / NIC2 MAC | mac | No | Always | NIC MAC addresses |
| NUMA Topology | enum | No | Always | NUMA configuration |
| CPU Pinning | enum | No | Always | enabled / disabled |
| BMC Address | bmc_address | Yes | Unprovisioned | BMC/Redfish URI |
| Boot MAC Address | mac | Yes | Unprovisioned | PXE boot MAC |
| BMH Namespace | k8s_name | No | Unprovisioned | BareMetalHost namespace |
| Root Device Hint | device_path | No | Unprovisioned | Boot disk path |
| Boot Mode | enum | No | Unprovisioned | UEFI, legacy, UEFISecureBoot |
| Provisioning NIC / VLAN / IP | various | No | Unprovisioned | Provisioning network details |

---

## Manifest Catalog (15 Templates)

CPAT generates every RHOSO deployment CR via CIQ-driven Jinja2 templates.
Templates are at `ansible/playbooks/roles/rhoso/templates/`.

| # | Template | CR Kind | Conditional |
|---|----------|---------|-------------|
| 1 | `openstack_nncp.yaml.j2` | NodeNetworkConfigurationPolicy | Always |
| 2 | `openstack_nad.yaml.j2` | NetworkAttachmentDefinition | Always |
| 3 | `openstack_metallb.yaml.j2` | IPAddressPool + L2Advertisement | Always |
| 4 | `openstack_netconfig.yaml.j2` | NetConfig | Always |
| 5 | `openstack_control_plane.yaml.j2` | OpenStackControlPlane | Always |
| 6 | `edpm_network_config_template.j2` | EDPM NIC config (os-net-config) | Always |
| 7 | `openstack_dataplane_nodeset.yaml.j2` | OpenStackDataPlaneNodeSet | Always |
| 8 | `openstack_dataplane_deployment.yaml.j2` | OpenStackDataPlaneDeployment | Always |
| 9 | `openstack_baremetalhosts.yaml.j2` | BareMetalHost + BMC Secrets | Unprovisioned |
| 10 | `openstack_nmstate_secrets.yaml.j2` | NMState provisioning Secrets | Unprovisioned |
| 11 | `openstack_nova_cpu_pinning_cm.yaml.j2` | Nova CPU pinning ConfigMap | CPU Dedicated Set |
| 12 | `catalog_source.yaml.j2` | CatalogSource | Disconnected |
| 13 | `image_digest_mirror_set.yaml.j2` | ImageDigestMirrorSet | Disconnected |
| 14 | `image_tag_mirror_set.yaml.j2` | ImageTagMirrorSet | Disconnected |
| 15 | `operatorhub_disable_defaults.yaml.j2` | OperatorHub patch | Disconnected |

---

## Input Files Reference

Files uploaded via the CPAT UI during RHOSO cluster registration.

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

---

## CIQ Workbook Structure

The RHOSO CIQ workbook has **9 sheets**:

| # | Sheet | Contents |
|---|-------|----------|
| 1 | Versioning | Document metadata, sheet index, version history |
| 2 | Environment | rhoso_details, rhoso_access, rhoso_disconnected |
| 3 | Storage | rhoso_storage, rhoso_ceph_storage, rhoso_trident_storage, rhoso_lso_storage, rhoso_cinder_backend, rhoso_multipath |
| 4 | Control Plane | rhoso_control_plane, rhoso_services, rhoso_observability, rhoso_pv_sizing, rhoso_neutron_config |
| 5 | Networks | rhoso_networks (row table) |
| 6 | Data Plane | rhoso_edpm_network_config, rhoso_data_plane, rhoso_data_plane_nodes (row table) |
| 7 | values (hidden) | 20 dropdown lists registered in Excel Name Manager |
| 8 | Guidelines | Full parameter catalog — color-coded (yellow=required, green=conditional, white=optional) |
| 9 | Operators | Prerequisite operator reference |

### Conditional formatting (18 rules)

The workbook greys out irrelevant parameters based on selections:

| Trigger | When | What gets greyed out |
|---------|------|----------------------|
| Deployment Mode ≠ disconnected | Connected | Disconnected table |
| EDPM Topology ≠ bond type | Single NIC | Bond fields (NIC2, Bond Name, Options) |
| EDPM Topology ≠ ovs_dpdk | Non-DPDK | DPDK fields (MTU, RX Queue, OVS Extra) |
| Subscription Method ≠ activation_key | username/password | Org ID, Activation Key |
| Subscription Method ≠ username_password | activation_key | Username field |
| Ceph External ≠ yes | No Ceph | Ceph storage params |
| Ceph RGW Enabled ≠ yes | No RGW | RGW endpoint, TLS |
| Trident Enabled ≠ yes | No Trident | Trident storage params |
| LSO Enabled ≠ yes | No LSO | LSO storage params |
| Multipath Enabled ≠ yes | No multipath | Multipath params |
| Observability Enabled ≠ yes | No observability | Observability params |
| DP Mode ≠ unprovisioned | Pre-provisioned | BMC, Boot MAC columns |
| DP Mode ≠ pre-provisioned | Unprovisioned | Ansible Host, Management IP columns |
| Service Enabled ≠ yes | Service disabled | Respective replica counts |

CIQ workbook files: `output/ciq-workbooks/rhoso/`
- `rhoso-ciq-template.xlsx` — blank template
- `sample-rhoso.ciq.xlsx` — pre-filled sample

---

## Ansible Role Structure

```
roles/rhoso/
├── defaults/main.yml              ~210 default variables
├── tasks/
│   ├── main.yml                   Entry point: CIQ load + task routing
│   ├── common/
│   │   ├── _load_ciq_context.yml  Load CIQ params
│   │   ├── _validate_ciq.yml     CIQ field validation
│   │   └── _verify_required_crds.yml  Check OpenStack CRDs
│   ├── prerequisites/
│   │   └── prerequisites.yml                     Validate CIQ, cluster access
│   │   └── prerequisite_operator_installation.yml NMState, MetalLB, Cert-Manager
│   │   └── disconnected_environment_preparation.yml IDMS, CatalogSource
│   ├── secrets/
│   │   ├── generate_osp_secret.yml               19 service passwords
│   │   ├── generate_data_plane_secrets.yml        SSH, subscription, nova-migration
│   │   └── generate_ceph_secret.yml               Ceph keyring
│   ├── storage/
│   │   ├── persistent_storage_configuration.yml   StorageClass config
│   │   ├── trident_storage_configuration.yml      Trident backend + StorageClass
│   │   └── _generate_storage_crs.yml              Render storage manifests
│   ├── control_plane/
│   │   ├── openstack_operator_installation_and_preparation.yml
│   │   ├── rhocp_preparation_for_rhoso.yml
│   │   ├── control_plane_deployment_and_verification.yml
│   │   ├── control_plane_customization.yml
│   │   └── _generate_control_plane_crs.yml
│   ├── network/
│   │   └── network_preparation.yml               NNCP, NAD, MetalLB, NetConfig
│   ├── data_plane/
│   │   ├── data_plane_deployment_and_verification.yml
│   │   └── _generate_data_plane_crs.yml
│   ├── post_deployment/
│   │   ├── post_deployment_validation.yml
│   │   └── observability_configuration.yml
│   └── manifests/
│       ├── manifest_generation.yml               Generate-only mode
│       └── _generate_disconnected_crs.yml        IDMS, CatalogSource CRs
└── templates/                     15 Jinja2 templates (listed above)
```

---

## API Reference (RHOSO Endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/clusters/register` | Register RHOSO cluster (CIQ upload, NDJSON stream) |
| `POST` | `/api/rhoso-installations/run` | Start RHOSO installation (NDJSON stream) |
| `GET` | `/api/rhoso-installations` | List RHOSO executions |
| `GET` | `/api/rhoso-installations/<id>` | Get execution status |
| `GET` | `/api/rhoso-installations/<id>/log` | Get/download execution log |

### Example: Run RHOSO installation

```bash
curl -X POST http://localhost/api/rhoso-installations/run \
  -H "Content-Type: application/json" \
  -d '{"cluster_id":"<uuid>","tasks":["prerequisites","network_preparation"],"execution_mode":"deploy"}'
```

Response: NDJSON stream of execution events.

---

## Manual CLI Usage

### Run single task via Ansible

```bash
ansible-playbook ansible/playbooks/main.yml \
  -e '{"rhoso_cluster_name":"nokia-lab-01","rhoso_selected_task":"network_preparation"}'
```

### Run full deployment

```bash
ansible-playbook ansible/playbooks/main.yml \
  -e '{"rhoso_cluster_name":"nokia-lab-01","rhoso_selected_task":"full_install"}'
```

---

*CPAT v25.10.1 — RHOSO CIQ Schema v1.4 — RHOSO 18.0 on RHOCP 4.14–4.18*
