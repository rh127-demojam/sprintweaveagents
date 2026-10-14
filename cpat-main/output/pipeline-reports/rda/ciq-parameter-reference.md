# RHOSO CIQ Parameter Reference

> Schema version: **1.3** | Tables: **15** | Parameters: **175+** | Network fields: **16** | Node fields: **16**

This document provides a quick-reference summary of all CIQ parameters defined in `rhoso_ciq_schema.py`.

## Tables Overview

| # | Table Key | Display Name | Parameter Count |
|---|-----------|-------------|-----------------|
| 1 | rhoso_details | RHOSO Details | 11 |
| 2 | rhoso_access | Cluster Access | 3 |
| 3 | rhoso_disconnected | Disconnected Environment | 16 |
| 4 | rhoso_storage | Persistent Storage | 2 |
| 5 | rhoso_ceph_storage | Ceph Storage | 12 |
| 6 | rhoso_control_plane | Control Plane | 29 |
| 7 | rhoso_services | OpenStack Services & HA Operators | 40 |
| 8 | rhoso_pv_sizing | PV Sizing & Resources | 10 |
| 9 | rhoso_cinder_backend | Cinder Backend | 8 |
| 10 | rhoso_neutron_config | Neutron Configuration | 5 |
| 11 | rhoso_edpm_network_config | EDPM Network Config | 24 |
| 12 | rhoso_data_plane | Data Plane | 13 |
| 13 | rhoso_networks | Networks (multi-row) | 16 fields |
| 14 | rhoso_data_plane_nodes | Data Plane Nodes (multi-row) | 16 fields |

### New in v1.3

| Table | Parameter | Purpose |
|-------|-----------|---------|
| `rhoso_details` | FIPS Enabled | Enable FIPS 140-3 compliance checks and iSCSI CHAP configuration |
| `rhoso_ceph_storage` | Ceph External | Use external Red Hat Ceph Storage cluster |
| `rhoso_ceph_storage` | Ceph Cluster Name | Ceph cluster name (e.g. ceph) |
| `rhoso_ceph_storage` | Ceph FSID | Ceph cluster FSID (UUID) |
| `rhoso_ceph_storage` | Ceph Mon Host | Ceph monitor hosts (comma-separated IPs) |
| `rhoso_ceph_storage` | Ceph Client Name | Ceph client auth user (e.g. openstack) |
| `rhoso_ceph_storage` | Ceph Client Key Path | Path to Ceph client keyring file |
| `rhoso_ceph_storage` | Ceph Pool Volumes | Ceph RBD pool for Block Storage (cinder) volumes |
| `rhoso_ceph_storage` | Ceph Pool Images | Ceph RBD pool for Image service (glance) images |
| `rhoso_ceph_storage` | Ceph Pool VMs | Ceph RBD pool for Compute (nova) ephemeral disks |
| `rhoso_ceph_storage` | Ceph RGW Enabled | Enable Ceph RADOS Gateway for Object Storage |
| `rhoso_ceph_storage` | Ceph RGW Endpoint | Ceph RGW endpoint URL |
| `rhoso_ceph_storage` | Ceph RGW TLS Enabled | Enable TLS for Ceph RGW endpoint |
| `rhoso_control_plane` | Messaging Bus Cluster | Default RabbitMQ cluster for messagingBus |
| `rhoso_control_plane` | Notifications Bus Cluster | Default RabbitMQ cluster for notificationsBus |
| `rhoso_services` | Watcher Enabled | Enable Watcher (Optimize) service |
| `rhoso_services` | Node Health Check Operator Enabled | Install Node Health Check Operator for HA |
| `rhoso_services` | Self Node Remediation Operator Enabled | Install Self Node Remediation Operator for HA |
| `rhoso_services` | Fence Agents Remediation Operator Enabled | Install Fence Agents Remediation Operator for HA |
| `rhoso_neutron_config` | MAC Binding Age Threshold | OVN mac_binding_age_threshold (set to 0 for RHOSO 18.0 known issue) |

## Conditional Parameters

Parameters are gated by a `when` condition:

| Condition | Meaning |
|-----------|---------|
| `always` | Required for all deployments |
| `disconnected` | Only when Deployment Mode = disconnected/airgapped/offline |
| `edpm_bond` | Only when EDPM topology uses bonded NICs |
| `edpm_dpdk` | Only when EDPM topology = ovs_dpdk |
| `activation_key` | Only when Subscription Method = activation_key |
| `username_password` | Only when Subscription Method = username_password |
| `pre_provisioned` | Only for pre-provisioned data plane nodes |
| `unprovisioned` | Only for bare-metal provisioning via Ironic |

## Type Library (38 types)

| Type | Description | Regex Pattern |
|------|-------------|---------------|
| dns_label | DNS label / Kubernetes name (lowercase) | `^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$` |
| k8s_name | Kubernetes resource name | `^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$` |
| cluster_name | Cluster / environment name | `^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$` |
| fqdn | Fully qualified domain name | `^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$` |
| dns_domain | DNS domain (may be single label) | `^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$` |
| ipv4 | IPv4 address | `^((25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\.){3}(25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)$` |
| host_or_ip | IPv4 address or hostname | `^(((25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\.){3}(25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\|([A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*))$` |
| cidr | IPv4 CIDR (e.g. 192.168.0.0/24) | `^((25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\.){3}(25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)/([0-9]\|[1-2][0-9]\|3[0-2])$` |
| unix_path | Absolute Unix filesystem path | `^(/[^/\0]+)+/?$` |
| unix_path_or_empty | Absolute Unix path or empty | `^((/[^/\0]+)+/?)?$` |
| https_url | HTTPS URL | `^https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+$` |
| http_url | HTTP or HTTPS URL | `^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+$` |
| registry_host | Container registry host[:port][/path] | `^[A-Za-z0-9]([A-Za-z0-9._\-]*[A-Za-z0-9])?(:[0-9]{1,5})?(/[A-Za-z0-9._\-]+)*$` |
| image_ref | Container image reference | `^[A-Za-z0-9]([A-Za-z0-9._\-/:@]*[A-Za-z0-9])?$` |
| registry_path | Registry repository path | `^[A-Za-z0-9]([A-Za-z0-9._\-/]*[A-Za-z0-9])?$` |
| yes_no | Boolean yes/no | `(?i)^(yes\|no\|true\|false\|1\|0)$` |
| vlan | VLAN ID 1-4094 | `^([1-9]\|[1-9][0-9]\|[1-9][0-9]{2}\|[1-3][0-9]{3}\|40[0-8][0-9]\|409[0-4])$` |
| mtu | MTU (100-99999) | `^[1-9][0-9]{2,4}$` |
| mac | MAC address | `^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$` |
| iface | Network interface name | `^[A-Za-z][A-Za-z0-9._\-]{0,31}$` |
| username | Unix / SSH username | `^[A-Za-z_][A-Za-z0-9._\-]{0,63}$` |
| org_id | Red Hat Organization ID | `^[A-Za-z0-9_\-]{1,64}$` |
| activation_key | Red Hat activation key | `^[A-Za-z0-9._\-]{1,256}$` |
| cni_version | CNI version (e.g. 0.3.1) | `^[0-9]+\.[0-9]+(\.[0-9]+)?$` |
| integer | Non-negative integer | `^[0-9]+$` |
| ntp_list | Comma-separated NTP hostnames | `^([A-Za-z0-9]([A-Za-z0-9.\-]*[A-Za-z0-9])?)(,\s*[A-Za-z0-9]([A-Za-z0-9.\-]*[A-Za-z0-9])?)*$` |
| bonding_options | Linux bonding_options key=value string | `^(?:[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9._+\-:]+(?:,[A-Za-z0-9._+\-:]+)*(?:\s+[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9._+\-:]+(?:,[A-Za-z0-9._+\-:]+)*)*)$` |
| free_text | Free-form text (max 2048) | `^[\s\S]{0,2048}$` |
| enum_type | CIQ Type = RHOSO | `(?i)^(rhoso\|red\s*hat\s*openstack\s*services\s*on\s*openshift)$` |
| enum_environment | Environment | `(?i)^(lab\|test\|staging\|prod\|development)$` |
| enum_rhoso_version | Supported RHOSO version | `^18\.0$` |
| enum_rhocp_version | RHOCP version 4.x | `^4\.(1[4-8]\|[0-9]{1,2})$` |
| enum_deployment_mode | Deployment mode | `(?i)^(connected\|disconnected\|airgapped\|offline)$` |
| enum_storage_backend | Storage backend | `(?i)^[A-Za-z][A-Za-z0-9 +\-/().]*[A-Za-z0-9)]$` |
| enum_ovn_gateway | OVN gateway placement | `(?i)^(control-plane\|data-plane\|networker)$` |
| enum_dp_mode | Data plane provisioning mode | `(?i)^(pre-provisioned\|unprovisioned)$` |
| enum_edpm_topology | EDPM network config topology | `(?i)^(single_nic_vlans\|dual_nic_bond\|ovs_bond\|linux_bond\|ovs_dpdk)$` |
| enum_edpm_bridge | EDPM bridge type | `(?i)^(ovs_bridge\|ovs_user_bridge)$` |
| enum_subscription | Subscription method | `(?i)^(activation_key\|username_password)$` |

## Generated Workbooks

| File | Purpose |
|------|---------|
| `output/ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx` | Pre-filled with Nokia lab sample values |
| `output/ciq-workbooks/rhoso/rhoso-ciq-template.xlsx` | Blank template for customer data entry |

## Source Files

| File | Purpose |
|------|---------|
| `output/ciq-generators/rhoso_ciq_schema.py` | Canonical schema (standalone copy) |
| `output/ciq-generators/generate_rhoso_ciq_workbooks.py` | Generator script |
| `output/ciq-generators/requirements.txt` | Python dependencies |
