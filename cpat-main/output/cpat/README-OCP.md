# CPAT — OCP Installation Guide

Detailed documentation for **OpenShift Container Platform (OCP) 4.17–4.20**
bare-metal installation using CPAT.

> OCP is the platform layer — install it first. RHOSO is deployed on top of
> a running OCP cluster. See [README-RHOSO.md](README-RHOSO.md) for RHOSO.

**OCP CIQ Schema:** v1.1 — 14 param + 4 row tables, 177 total fields, 54 CIQ_TYPES, 25 dropdown lists

---

## Table of Contents

- [Supported Installation Methods](#supported-installation-methods)
- [Prerequisites](#prerequisites)
- [OCP Install Workflow](#ocp-install-workflow)
- [Installation Tasks (22)](#installation-tasks-22)
- [CIQ Parameter Reference (18 Tables)](#ciq-parameter-reference-18-tables)
- [Manifest Catalog (12 Templates)](#manifest-catalog-12-templates)
- [Input Files Reference](#input-files-reference)
- [CIQ Workbook Structure](#ciq-workbook-structure)
- [Ansible Role Structure](#ansible-role-structure)
- [API Reference (OCP Endpoints)](#api-reference-ocp-endpoints)
- [Manual CLI Usage](#manual-cli-usage)

---

## Supported Installation Methods

| Method | Description | Platform | Disconnected |
|--------|-------------|----------|--------------|
| **ABI** | Agent-based Installer — boots nodes from agent ISO | none / baremetal | No |
| **IPI-BM** | Installer-Provisioned Infrastructure — Bare Metal with BMC automation | baremetal | No |
| **UPI-BM** | User-Provisioned Infrastructure — manual ignition + PXE boot | none | No |
| **ABI-DC** | Agent-based Installer — Disconnected with mirror registry | none / baremetal | Yes |
| **SNO** | Single Node OpenShift — single-node ABI (1 master, 0 workers) | none | No/Yes |

### Node requirements

| Configuration | Control Plane | Workers | Total |
|---------------|---------------|---------|-------|
| Standard HA | 3 | 2+ | 5+ |
| Compact | 3 | 0 | 3 |
| Single Node (SNO) | 1 | 0 | 1 |

---

## Prerequisites

| Prerequisite | Description |
|--------------|-------------|
| Bastion host with Podman | Linux host with network access to bare metal nodes |
| `openshift-install`, `oc`, `oc-mirror` | **Baked into CPAT container image** — auto-downloaded during `./bringup.sh build` |
| Pull secret | From [console.redhat.com](https://console.redhat.com) — `pull-secret.json` (upload via CPAT UI) |
| SSH key pair | For CoreOS node access — public key uploaded via CPAT UI |
| DNS records | api, api-int, *.apps records pointing to VIP or LB |
| Load balancer (platform=none) | HAProxy (CPAT generates config), MetalLB, or external LB |
| DHCP/PXE (UPI only) | For network boot of nodes |
| Mirror registry (disconnected) | **CPAT installs** Quay mirror-registry on bastion (Task 4) |
| BMC access (ABI-DC / IPI) | Redfish/IPMI access to all nodes |

> **Note:** OCP binaries are downloaded automatically during CPAT image build.
> Override version: `podman build --build-arg OCP_VERSION=4.19 -t cpat:25.10.1 .`
> For air-gapped builds, place binaries in `binaries/` before building.

---

## OCP Install Workflow

### Generate → Review → Deploy

```
1. Register OCP cluster     Upload OCP CIQ workbook (.xlsx)
       ↓                    Parser reads ocp_details table (Type=OCP)
2. Generate Manifests       Renders install-config, agent-config, NMState,
       ↓                    HAProxy, DNS records, operator CRs
3. Review                   View YAML in UI or download ZIP
       ↓
4. Deploy Tasks             Execute tasks sequentially via Web UI
       ↓                    Real-time NDJSON log streaming
5. Cluster Ready            oc get clusterversion → Available
```

**API flow:**
```
POST /api/ocp/clusters/register          → Upload CIQ
POST /api/ocp-installations/run          → Start tasks (NDJSON stream)
GET  /api/ocp-installations/<id>         → Check status
GET  /api/clusters/<id>/artifacts        → List manifests
```

---

## Installation Tasks (22)

CPAT provides **22 OCP installation tasks** (1 generate + 21 deploy) mapped to
Ansible task files via `OCP_INSTALLATION_TASK_TAGS` in `backend/ansible_runner.py`.

### Task summary

| # | UI Task | Ansible Task Tag | Conditional | Description |
|---|---------|-----------------|-------------|-------------|
| 0 | Generate Manifests | `generate_manifests` | Always | Render all configs from CIQ (no apply) |
| 1 | Bastion Preparation | `bastion_preparation` | Always | Install tools, configure bastion host |
| 2 | DNS DHCP Validation | `dns_dhcp_validation` | Always | Verify DNS records resolve correctly |
| 3 | NTP Sync | `ntp_sync` | Always | Configure chrony NTP on bastion |
| 4 | Mirror Registry Install | `mirror_registry` | Disconnected | Install Quay mirror-registry on bastion |
| 5 | OC Mirror Execution | `oc_mirror` | Disconnected | Mirror OCP release + operator images |
| 6 | IDMS ITMS Configuration | `idms_itms_config` | Disconnected | Generate ImageDigestMirrorSet + CatalogSource CRs |
| 7 | Generate Install Config | `install_config` | Always | Render `install-config.yaml` from CIQ |
| 8 | Generate Agent Config | `agent_config` | ABI / ABI-DC | Render `agent-config.yaml` with NMState |
| 9 | Generate NMState Configs | `nmstate_configs` | NMState defined | Render per-host NMState YAML |
| 10 | Generate Ignition Configs | `ignition_configs` | UPI | Run `openshift-install create ignition-configs` |
| 11 | Create Agent ISO | `agent_iso` | ABI / ABI-DC | Run `openshift-install agent create image` |
| 12 | Bootstrap Cluster | `bootstrap` | Always | Wait for bootstrap to complete |
| 13 | Wait Install Complete | `wait_install` | Always | Wait for full install, copy kubeconfig |
| 14 | Approve CSRs | `approve_csrs` | Always | Auto-approve pending node CSRs |
| 15 | Configure Authentication | `auth_config` | Always | Verify cluster access, show version |
| 16 | Day-2 Operator Installation | `day2_operators` | Always | Install NMState, MetalLB, SR-IOV, etc. |
| 17 | MetalLB Configuration | `metallb_config` | MetalLB enabled | Configure IPAddressPool, L2Advertisement |
| 18 | SR-IOV Multus Configuration | `sriov_config` | SR-IOV/Multus | Configure SR-IOV network policies |
| 19 | Cluster Health Check | `health_check` | Always | Verify cluster operators, version |
| 20 | Node Readiness Check | `node_readiness` | Always | Verify all nodes Ready |
| 21 | Full Install | `full_install` | All steps | Execute all tasks sequentially |

### Shared context (every task)

Before any task runs, `roles/ocp/tasks/main.yml` includes `common/_load_ciq_context.yml`:

1. Loads CIQ parameters from Ansible inventory
2. Resolves install method flags: `ocp_is_abi`, `ocp_is_ipi`, `ocp_is_upi`, `ocp_is_sno`
3. Resolves disconnected flag: `ocp_is_disconnected`
4. Creates install/manifest directories
5. Validates CIQ fields per install method (`common/_validate_ciq.yml`)

### Task-to-install-method matrix

| Task | ABI | IPI-BM | UPI-BM | ABI-DC | SNO |
|------|-----|--------|--------|--------|-----|
| Mirror Registry Install | — | — | — | Yes | — |
| OC Mirror Execution | — | — | — | Yes | — |
| IDMS ITMS Configuration | — | — | — | Yes | — |
| Generate Agent Config | Yes | — | — | Yes | Yes |
| Generate Ignition Configs | — | — | Yes | — | — |
| Create Agent ISO | Yes | — | — | Yes | Yes |
| All other tasks | Yes | Yes | Yes | Yes | Yes |

---

## CIQ Parameter Reference (18 Tables)

The OCP CIQ workbook contains **18 named Excel tables** (14 parameter + 4 row tables).
The backend parser discovers tables via `ws.tables.values()` and matches by `displayName`.

### Table overview

| # | Excel Table Name | Sheet | Params | Description |
|---|-----------------|-------|--------|-------------|
| 1 | `ocp_details` | Environment | 15 | Cluster name, version, install method, platform |
| 2 | `ocp_access` | Environment | 4 | Pull secret, SSH key, kubeconfig paths |
| 3 | `ocp_proxy` | Environment | 5 | HTTP/HTTPS proxy configuration |
| 4 | `ocp_disconnected` | Environment | 14 | Mirror registry, IDMS, CatalogSource |
| 5 | `ocp_mirror_registry` | Environment | 8 | Quay mirror-registry settings |
| 6 | `ocp_platform_baremetal` | Platform | 12 | IPI VIPs, provisioning network, BMC |
| 7 | `ocp_agent_config` | Platform | 10 | ABI rendezvous IP, NTP, agent counts |
| 8 | `ocp_bastion` | Platform | 8 | Bastion host details |
| 9 | `ocp_load_balancer` | Platform | 8 | HAProxy / LB config (platform=none) |
| 10 | `ocp_networking` | Networking | 12 | Network CIDRs, MTU, IP families |
| 11 | `ocp_certificates` | Networking | 6 | API/Ingress certificates, CA |
| 12 | `ocp_ingress` | Networking | 6 | Ingress controller replicas, wildcard |
| 13 | `ocp_storage` | Storage & Operators | 8 | Default storage class, NFS, LSO, ODF |
| 14 | `ocp_day2_operators` | Storage & Operators | 12 | Day-2 operator enable toggles |
| 15 | `ocp_bmc_hosts` | Nodes | 14 cols | BMC host definitions (row table) |
| 16 | `ocp_nmstate_interfaces` | Nodes | 12 cols | NMState interface configs (row table) |
| 17 | `ocp_compute_nodes` | Nodes | 14 cols | Compute node inventory (row table) |
| 18 | `ocp_dns_records` | DNS Records | 8 cols | DNS record definitions (row table) |

### 1. OCP Cluster Details (`ocp_details`) — 15 params

| Parameter | Type | Required | When | Description |
|-----------|------|----------|------|-------------|
| Type | free_text | Yes | Always | Must be `OCP` |
| Cluster Name | cluster_name | Yes | Always | DNS-compatible cluster name |
| Base Domain | dns_domain | Yes | Always | Base domain (e.g. example.com) |
| OCP Version | enum | Yes | Always | 4.17, 4.18, 4.19, 4.20 |
| Install Method | enum | Yes | Always | ABI, IPI-BM, UPI-BM, ABI-DC, SNO |
| Platform | enum | Yes | Always | baremetal, vsphere, none, external |
| Deployment Mode | enum | Yes | Always | connected, disconnected |
| Architecture | enum | Yes | Always | amd64, arm64, ppc64le, s390x, multi |
| Control Plane Replicas | integer | Yes | Always | 3 (HA) or 1 (SNO) |
| Compute Replicas | integer | Yes | Always | 0 (SNO/compact), 2+ (HA) |
| Hyperthreading | enum | No | Always | Enabled / Disabled |
| FIPS Mode | yes/no | No | Always | FIPS 140-2/140-3 compliance |
| Publish | enum | No | Always | External / Internal |
| CPU Partitioning Mode | enum | No | Always | None / AllNodes |
| Feature Set | free_text | No | Always | e.g. TechPreviewNoUpgrade |

### 2. OCP Access (`ocp_access`) — 4 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Pull Secret Path | unix_path | Yes | Path to pull-secret.json |
| SSH Public Key Path | unix_path | Yes | Path to SSH public key |
| Kubeconfig Path | unix_path | No | Path to kubeconfig (post-install) |
| Credentials Mode | enum | No | Mint, Passthrough, Manual |

### 3. OCP Proxy (`ocp_proxy`) — 5 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| HTTP Proxy | http_url | No | HTTP proxy URL |
| HTTPS Proxy | https_url | No | HTTPS proxy URL |
| No Proxy | free_text | No | Domains/CIDRs excluded from proxy |
| Proxy CA Bundle Path | unix_path | No | Path to proxy CA certificate |
| Proxy Enabled | yes/no | No | Whether proxy is configured |

### 4. OCP Networking (`ocp_networking`) — 12 params

| Parameter | Type | Required | When | Description |
|-----------|------|----------|------|-------------|
| Network Type | enum | Yes | Always | OVNKubernetes |
| Cluster Network CIDR | cidr | Yes | Always | Pod network (default: 10.128.0.0/14) |
| Cluster Network Host Prefix | integer | Yes | Always | Per-node subnet prefix (default: 23) |
| Service Network CIDR | cidr | Yes | Always | Service network (default: 172.30.0.0/16) |
| Machine Network CIDR | cidr | Yes | Always | Node network CIDR |
| Cluster Network CIDR IPv6 | cidr | No | DualStack | IPv6 pod network |
| Service Network CIDR IPv6 | cidr | No | DualStack | IPv6 service network |
| Machine Network CIDR IPv6 | cidr | No | DualStack | IPv6 node network |
| IP Families | enum | No | Always | IPv4, IPv6, DualStack |
| Network MTU | mtu | No | Always | Cluster-wide MTU |
| Additional Trust Bundle | free_text | No | Disconnected | PEM CA bundle for mirror registry |
| Additional Trust Bundle Path | unix_path | No | Disconnected | Path to CA bundle file |

### 5. OCP Platform Baremetal (`ocp_platform_baremetal`) — 12 params

Required when Install Method = **IPI-BM**. Greyed out in CIQ for other methods.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| API VIP | ipv4/ipv6 | Yes | Virtual IP for Kubernetes API |
| Ingress VIP | ipv4/ipv6 | Yes | Virtual IP for *.apps ingress |
| Provisioning Network | enum | Yes | Managed / Disabled |
| Provisioning Network CIDR | cidr | No | Provisioning subnet CIDR |
| Provisioning MAC Address | mac | No | NIC MAC on provisioning network |
| Provisioning Network Interface | iface | No | NIC name on provisioning network |
| Provisioning DHCP Range | free_text | No | DHCP range (e.g. 172.22.0.10,172.22.0.254) |
| Cluster Provisioning IP | ipv4 | No | IP for provisioning services |
| Bootstrap OS Image URL | http_url | No | RHCOS bootstrap image URL |
| Cluster OS Image URL | http_url | No | RHCOS cluster image URL |
| External Bridge | iface | No | External network bridge |
| Libvirt URI | free_text | No | Libvirt connection URI |

### 6. OCP Agent Config (`ocp_agent_config`) — 10 params

Required when Install Method = **ABI**, **ABI-DC**, or **SNO**. Greyed out otherwise.

| Parameter | Type | Required | When | Description |
|-----------|------|----------|------|-------------|
| Rendezvous IP | ipv4/ipv6 | Yes | ABI | IP of rendezvous host (assisted-service) |
| Boot Artifacts Base URL | http_url | No | ABI | PXE asset server URL |
| Additional NTP Sources | ntp_list | No | ABI | Comma-separated NTP sources |
| Agent Additional Trust Bundle Path | unix_path | No | ABI-DC | CA bundle path for agent |
| Agent HTTP Proxy | http_url | No | ABI | HTTP proxy for agent discovery |
| Agent HTTPS Proxy | https_url | No | ABI | HTTPS proxy for agent discovery |
| Agent No Proxy | free_text | No | ABI | Proxy exclusions for agent |
| Control Plane Agent Count | integer | No | ABI | Expected control plane agents |
| Worker Agent Count | integer | No | ABI | Expected worker agents |
| Bootstrap In Place | yes/no | No | SNO | Enable bootstrap-in-place for SNO |

### 7. OCP Disconnected (`ocp_disconnected`) — 14 params

Required when Deployment Mode = **disconnected**. Greyed out for connected.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Mirror Registry URL | registry_host | Yes | Local mirror registry (host:port) |
| Mirror Registry CA Path | unix_path | Yes | Mirror registry CA certificate |
| Image Content Source - Source 1 | image_ref | Yes | Source registry (e.g. quay.io/openshift-release-dev/ocp-release) |
| Image Content Source - Mirror 1 | registry_host | Yes | Mirror location for source 1 |
| Image Content Source - Source 2 | image_ref | No | Source for art-dev images |
| Image Content Source - Mirror 2 | registry_host | No | Mirror for source 2 |
| IDMS Name | dns_label | No | ImageDigestMirrorSet name |
| ITMS Name | dns_label | No | ImageTagMirrorSet name |
| CatalogSource Name | dns_label | No | Disconnected CatalogSource name |
| CatalogSource Image | image_ref | No | Mirrored operator index image |
| Disable Default CatalogSources | yes/no | No | Disable default OperatorHub catalogs |
| OC Mirror Workspace | unix_path | No | oc-mirror workspace directory |
| Operator Index Image | image_ref | No | Operator index image to mirror |
| Registry Credentials Path | unix_path | No | Registry auth credentials path |

### 8. OCP Mirror Registry (`ocp_mirror_registry`) — 8 params

Used when hosting a Quay mirror-registry on the bastion. Greyed out for connected.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Quay Hostname | fqdn | Yes | Quay mirror-registry FQDN |
| Quay Root Directory | unix_path | No | Root directory for Quay data |
| Quay Version | free_text | No | Quay mirror-registry version |
| Quay Init Password | secret_text | No | Initial admin password (path ref preferred) |
| Quay TLS Cert Path | unix_path | No | TLS certificate path |
| Quay TLS Key Path | unix_path | No | TLS private key path |
| Quay Storage Backend | free_text | No | Storage backend type |
| Quay Storage Path | unix_path | No | Storage directory path |

### 9. OCP Bastion (`ocp_bastion`) — 9 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Bastion Hostname | fqdn | No | Bastion host FQDN |
| Bastion IP | ipv4 | No | Bastion IP address |
| Bastion DNS | host_or_ip | No | DNS server on bastion |
| Bastion OS | free_text | No | Operating system (e.g. RHEL 9.4) |
| Bastion RHEL Version | free_text | No | RHEL version |
| Bastion Disk Layout | free_text | No | Disk/LVM layout |
| Registry Mirror Enabled | yes/no | No | Bastion hosts mirror registry |
| DHCP TFTP Server | yes/no | No | Bastion serves DHCP/TFTP (UPI) |
| Bastion NTP Server | host_or_ip | No | NTP server for bastion |

### 10. OCP Load Balancer (`ocp_load_balancer`) — 8 params

Required when Platform = **none**. Greyed out for platform=baremetal.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Load Balancer Type | enum | Yes | HAProxy, MetalLB, F5, external, none |
| API Server Port | port | No | Kubernetes API port (default: 6443) |
| Machine Config Server Port | port | No | MCS port (default: 22623) |
| Ingress HTTPS Port | port | No | Ingress HTTPS port (default: 443) |
| Ingress HTTP Port | port | No | Ingress HTTP port (default: 80) |
| LB Backend Servers | free_text | No | Backend server list |
| LB Config Path | unix_path | No | Load balancer config file path |
| API VIP (platform none) | ipv4/ipv6 | Yes | Virtual IP for API |

### 11. OCP Certificates (`ocp_certificates`) — 6 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| API Certificate Path | unix_path | No | Custom API server certificate |
| Ingress Wildcard Cert Path | unix_path | No | Wildcard cert for *.apps |
| CA Bundle Path | unix_path | No | CA bundle for custom certs |
| Lets Encrypt Enabled | yes/no | No | Use Let's Encrypt |
| Custom CA Enabled | yes/no | No | Custom CA in use |
| Certificate Validity Days | integer | No | Cert validity in days |

### 12. OCP Storage (`ocp_storage`) — 8 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Default Storage Class | free_text | No | Default StorageClass name |
| CSI Driver | enum | No | NFS, ODF, LSO, Trident, hostpath, none |
| NFS Server | host_or_ip | No | NFS server hostname/IP |
| NFS Path | unix_path | No | NFS export path |
| LSO Enabled | yes/no | No | Enable Local Storage Operator |
| LSO Device Paths | free_text | No | Device paths for LSO |
| ODF Enabled | yes/no | No | Enable OpenShift Data Foundation |
| ODF Storage Class | free_text | No | ODF StorageClass name |

### 13. OCP Day-2 Operators (`ocp_day2_operators`) — 12 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| NMState Operator Enabled | yes/no | No | Kubernetes NMState Operator |
| MetalLB Operator Enabled | yes/no | No | MetalLB Operator |
| SR-IOV Operator Enabled | yes/no | No | SR-IOV Network Operator |
| Multus Enabled | yes/no | No | Multus CNI |
| LSO Operator Enabled | yes/no | No | Local Storage Operator |
| ODF Operator Enabled | yes/no | No | OpenShift Data Foundation |
| Cert Manager Enabled | yes/no | No | cert-manager Operator |
| Cluster Logging Enabled | yes/no | No | Cluster Logging (EFK/Loki) |
| Monitoring Stack Enabled | yes/no | No | Monitoring stack customization |
| GitOps Operator Enabled | yes/no | No | OpenShift GitOps (ArgoCD) |
| MCE Operator Enabled | yes/no | No | multicluster engine |
| Operator Install Plan Approval | enum | No | Automatic / Manual |

### 14. OCP Ingress (`ocp_ingress`) — 6 params

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Ingress Controller Replicas | integer | No | Ingress Controller replica count |
| Ingress Default Certificate Path | unix_path | No | Default Ingress certificate |
| Wildcard Policy | enum | No | WildcardsAllowed / WildcardsDisallowed |
| Route Admission Policy | free_text | No | Route admission config |
| Endpoint Publishing Strategy | enum | No | LoadBalancerService, HostNetwork, etc. |
| Ingress Node Selector | free_text | No | Node selector for Ingress pods |

### 15. OCP BMC Hosts (`ocp_bmc_hosts`) — 14 columns (row table)

One row per cluster node (masters + workers).

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Hostname | dns_label | Yes | Node hostname |
| Role | enum | Yes | master / worker |
| BMC Address | bmc_address | Yes (IPI) | Redfish/IPMI URI |
| BMC Username | username | Yes (IPI) | BMC login username |
| BMC Password Reference | free_text | Yes (IPI) | Vault path — **never plaintext** |
| Boot MAC Address | mac | Yes | NIC MAC for PXE boot |
| Boot Mode | enum | No | UEFI, legacy, UEFISecureBoot |
| Root Device Hint | free_text | No | e.g. `deviceName: /dev/sda` |
| Root Device Name | device_path | No | e.g. `/dev/sda` |
| Disable Certificate Verification | yes/no | No | Skip BMC TLS verification |
| Network Config | free_text | No | NMState config reference |
| CPU Count | integer | No | vCPUs (capacity planning) |
| Memory GB | integer | No | RAM in GB |
| Disk Size GB | integer | No | Primary disk size in GB |

### 16. OCP NMState Interfaces (`ocp_nmstate_interfaces`) — 12 columns (row table)

One row per network interface per host.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Host | dns_label | Yes | Hostname this config applies to |
| Interface Name | iface | Yes | e.g. eno1, bond0, bond0.300 |
| Type | enum | Yes | ethernet, bond, vlan, bridge |
| State | enum | Yes | up, down, absent |
| IPv4 Address | ipv4/ipv6 | No | Static IP address |
| Prefix Length | integer | No | Subnet prefix (e.g. 23, 24) |
| Gateway | ipv4/ipv6 | No | Default gateway |
| VLAN ID | vlan | No | 802.1Q VLAN ID |
| Bond Mode | enum | No | active-backup, 802.3ad, etc. |
| Bond Members | free_text | No | Comma-separated member interfaces |
| DNS Servers | free_text | No | Comma-separated DNS IPs |
| MTU | mtu | No | Interface MTU |

### 17. OCP Compute Nodes (`ocp_compute_nodes`) — 14 columns (row table)

Physical node inventory for capacity planning.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Hostname | dns_label | Yes | Node hostname |
| Role | enum | Yes | master / worker |
| CPU Count | integer | No | CPU cores |
| Memory GB | integer | No | RAM in GB |
| Disk Count | integer | No | Number of disks |
| Management IP | ipv4 | No | Management network IP |
| BMC Address | bmc_address | No | BMC/IPMI/Redfish address |
| Boot MAC | mac | No | Boot NIC MAC |
| NIC1 MAC | mac | No | Primary NIC MAC |
| NIC2 MAC | mac | No | Secondary NIC MAC |
| IPMI Username | username | No | IPMI/BMC username |
| Install Disk | device_path | No | OS installation disk |
| Labels | free_text | No | Kubernetes node labels |
| Disk Size GB | integer | No | Primary disk size |

### 18. OCP DNS Records (`ocp_dns_records`) — 8 columns (row table)

Required DNS records for the cluster (especially platform=none).

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Record Type | enum | Yes | A, AAAA, CNAME, PTR, SRV |
| Hostname | free_text | Yes | DNS record name |
| IP or Target | free_text | Yes | IP address or CNAME target |
| TTL | integer | No | Time to live (seconds) |
| Zone | dns_domain | No | DNS zone |
| Purpose | enum | Yes | api, api-int, apps-wildcard, master, worker, etcd, bootstrap |
| Cluster Name | cluster_name | No | Cluster name for record |
| Notes | free_text | No | Additional notes |

---

## Manifest Catalog (12 Templates)

CPAT generates **12 OCP Jinja2 templates** covering all installation methods.
Templates are at `ansible/playbooks/roles/ocp/templates/`.

| # | Template | Generates | Conditional |
|---|----------|-----------|-------------|
| 1 | `ocp_install_config.yaml.j2` | `install-config.yaml` (IPI/UPI/ABI) | Always |
| 2 | `ocp_sno_install_config.yaml.j2` | `install-config.yaml` (SNO) | When SNO |
| 3 | `ocp_agent_config.yaml.j2` | `agent-config.yaml` | When ABI/ABI-DC |
| 4 | `ocp_nmstate_config.yaml.j2` | Per-host NMState YAML | When NMState interfaces defined |
| 5 | `ocp_platform_baremetal.yaml.j2` | Bare metal platform snippet | When IPI/ABI |
| 6 | `ocp_image_content_source.yaml.j2` | ImageDigestMirrorSet CR | When disconnected |
| 7 | `ocp_catalog_source.yaml.j2` | CatalogSource CR | When disconnected |
| 8 | `ocp_chrony_config.j2` | chrony.conf | Always |
| 9 | `ocp_haproxy_config.j2` | HAProxy LB config | When platform=none |
| 10 | `ocp_dns_records.j2` | BIND zone file | When DNS records defined |
| 11 | `ocp_day2_operator_sub.yaml.j2` | Operator Subscription CRs | When day-2 operators enabled |
| 12 | `ocp_mirror_imageset.yaml.j2` | oc-mirror ImageSetConfiguration | When disconnected |

---

## Input Files Reference

Files uploaded via the CPAT UI during OCP cluster registration.

| Field | CIQ Parameter | Stored As | Required | Notes |
|-------|--------------|-----------|----------|-------|
| `ocp_pull_secret` | Pull Secret Path | `pull-secret.json` | Yes | From console.redhat.com |
| `ocp_ssh_public_key` | SSH Public Key Path | `ssh-public-key` | Yes | Generated on bastion (`~/.ssh/id_ed25519.pub`) |
| `ocp_mirror_pull_secret` | Mirror Pull Secret Path | `mirror-pull-secret.json` | When disconnected | CPAT generates merged pull secret during mirror registry setup |
| `ocp_mirror_ca` | Mirror Registry CA Path | `mirror-ca.crt` | When disconnected | Auto-generated by CPAT Task 4 (`/opt/quay/quay-rootCA/rootCA.pem`) |

> **For disconnected installs:** only `pull-secret.json` and `ssh-public-key` need to be uploaded
> manually. The mirror registry CA and merged pull secret are generated automatically by CPAT
> during Tasks 4–5 (Mirror Registry Install → OC Mirror Execution).

---

## CIQ Workbook Structure

The OCP CIQ workbook has **10 sheets** with identical styling to the RHOSO CIQ:

| # | Sheet | Contents |
|---|-------|----------|
| 1 | Versioning | Document metadata, sheet index, version history |
| 2 | Environment | ocp_details, ocp_access, ocp_proxy, ocp_disconnected, ocp_mirror_registry |
| 3 | Platform | ocp_platform_baremetal, ocp_agent_config, ocp_bastion, ocp_load_balancer |
| 4 | Networking | ocp_networking, ocp_certificates, ocp_ingress |
| 5 | Storage & Operators | ocp_storage, ocp_day2_operators |
| 6 | Nodes | ocp_bmc_hosts, ocp_nmstate_interfaces, ocp_compute_nodes (row tables) |
| 7 | DNS Records | ocp_dns_records (row table) |
| 8 | values (hidden) | 25 dropdown lists registered in Excel Name Manager |
| 9 | Guidelines | Full parameter catalog — color-coded (yellow=required, green=conditional, white=optional) |
| 10 | Operators | OCP Day-2 operator reference |

### Conditional formatting (dependency-based grey-out)

The workbook uses Excel conditional formatting with **cross-sheet references**
to grey out parameters that don't apply to the current selection:

| Trigger | When | What gets greyed out |
|---------|------|----------------------|
| Deployment Mode ≠ disconnected | Connected install | Disconnected + Mirror Registry tables (22 rows) |
| Install Method ≠ IPI-BM | Non-IPI install | Platform Baremetal table (12 rows) |
| Install Method ∉ {ABI, ABI-DC, SNO} | IPI or UPI | Agent Config table (10 rows) |
| Install Method ≠ SNO | Non-SNO install | Bootstrap In Place param |
| Install Method ≠ UPI-BM | Non-UPI install | DHCP TFTP Server param |
| Platform ≠ none | Platform=baremetal | Load Balancer table (8 rows) |
| IP Families ≠ DualStack | Single-stack | IPv6 CIDR fields (3 rows) |

CIQ workbook files: `output/ciq-workbooks/ocp/`
- `ocp-ciq-template.xlsx` — blank template
- `sample-ocp.ciq.xlsx` — pre-filled sample

---

## Ansible Role Structure

```
roles/ocp/
├── defaults/main.yml              ~170 default variables
├── meta/main.yml                  Galaxy metadata
├── vars/main.yml                  Derived flags, paths, constants
├── tasks/
│   ├── main.yml                   Entry point: CIQ load + task routing
│   ├── common/
│   │   ├── _load_ciq_context.yml  Load CIQ params, resolve flags
│   │   ├── _validate_ciq.yml     Per-method CIQ field validation
│   │   └── _verify_prerequisites.yml  Check openshift-install, oc, etc.
│   ├── prerequisites/
│   │   ├── bastion_preparation.yml    Install tools, create dirs
│   │   ├── dns_dhcp_validation.yml    Verify DNS records
│   │   └── ntp_sync.yml              Configure chrony
│   ├── mirror/
│   │   ├── mirror_registry_install.yml     Install Quay mirror-registry
│   │   ├── oc_mirror_execution.yml         Run oc-mirror
│   │   └── idms_itms_configuration.yml     Generate IDMS/CatalogSource CRs
│   ├── install_config/
│   │   ├── generate_install_config.yml     Render install-config.yaml
│   │   ├── generate_agent_config.yml       Render agent-config.yaml
│   │   └── generate_nmstate_configs.yml    Render per-host NMState
│   ├── ignition/
│   │   ├── generate_ignition_configs.yml   Create ignition configs (UPI)
│   │   └── create_agent_iso.yml            Create agent ISO (ABI)
│   ├── bootstrap/
│   │   ├── bootstrap_cluster.yml           Wait for bootstrap complete
│   │   └── wait_bootstrap_complete.yml     Wait for full install
│   ├── cluster_config/
│   │   ├── approve_csrs.yml                Auto-approve node CSRs
│   │   ├── configure_authentication.yml    Verify access, show version
│   │   └── day2_operator_installation.yml  Install day-2 operators
│   ├── network/
│   │   ├── metallb_configuration.yml       MetalLB IPAddressPool, L2Advert
│   │   └── sriov_multus_configuration.yml  SR-IOV network policies
│   ├── validation/
│   │   ├── cluster_health_check.yml        Cluster operator status
│   │   └── node_readiness_check.yml        All nodes Ready
│   └── manifests/
│       ├── manifest_generation.yml             Generate-only mode
│       └── _generate_disconnected_crs.yml      IDMS + CatalogSource CRs
└── templates/                     12 Jinja2 templates (listed above)
```

---

## API Reference (OCP Endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/ocp/clusters/register` | Register OCP cluster (CIQ upload) |
| `GET` | `/api/ocp-installations/tasks` | List available OCP task names |
| `POST` | `/api/ocp-installations/run` | Start OCP installation (NDJSON stream) |
| `GET` | `/api/ocp-installations` | List OCP executions |
| `GET` | `/api/ocp-installations/<id>` | Get OCP execution status |
| `GET` | `/api/ocp-installations/<id>/log` | Get/download OCP execution log |

### Example: Run OCP installation

```bash
curl -X POST http://localhost/api/ocp-installations/run \
  -H "Content-Type: application/json" \
  -d '{"cluster_id":"<uuid>","tasks":["install_config","agent_config"],"ocp_version":"4.19"}'
```

Response: NDJSON stream of execution events.

---

## Manual CLI Usage

### Run single task via Ansible

```bash
ansible-playbook ansible/playbooks/ocp_install.yml \
  -e '{"ocp_cluster_name":"lab-ocp","ocp_version":"4.19","ocp_task":"install_config"}'
```

### Valid `ocp_task` values

`full_install`, `generate_manifests`, `bastion_preparation`, `dns_dhcp_validation`,
`ntp_sync`, `mirror_registry`, `oc_mirror`, `idms_itms_config`, `install_config`,
`agent_config`, `nmstate_configs`, `ignition_configs`, `agent_iso`, `bootstrap`,
`wait_install`, `approve_csrs`, `auth_config`, `day2_operators`, `metallb_config`,
`sriov_config`, `health_check`, `node_readiness`

---

*CPAT v25.10.1 — OCP CIQ Schema v1.1 — OCP 4.17–4.20*
