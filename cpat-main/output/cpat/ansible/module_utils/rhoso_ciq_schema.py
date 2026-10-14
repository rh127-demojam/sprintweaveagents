# -*- coding: utf-8 -*-
"""RHOSO CIQ field types and regexp patterns (Python source of truth).

Ansible consumes this schema via parse_ciq / get_validation_schema() and
performs the actual per-field validation. Patterns are Python/Ansible-
compatible RE2-style regex (no lookbehind required).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Shared type library: name -> {pattern, description}
# ---------------------------------------------------------------------------

CIQ_TYPES: dict[str, dict[str, str]] = {
    "dns_label": {
        "pattern": r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$",
        "description": "DNS label / Kubernetes name (lowercase)",
    },
    "k8s_name": {
        "pattern": r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$",
        "description": "Kubernetes resource name",
    },
    "cluster_name": {
        "pattern": r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$",
        "description": "Cluster / environment name",
    },
    "fqdn": {
        "pattern": (
            r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
            r"[a-zA-Z]{2,}$"
        ),
        "description": "Fully qualified domain name",
    },
    "dns_domain": {
        "pattern": (
            r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
            r"[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
        ),
        "description": "DNS domain (may be single label)",
    },
    "ipv4": {
        "pattern": (
            r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        ),
        "description": "IPv4 address",
    },
    "host_or_ip": {
        "pattern": (
            r"^("
            r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
            r"|"
            r"([A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
            r"(\.[A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*)"
            r")$"
        ),
        "description": "IPv4 address or hostname",
    },
    "cidr": {
        "pattern": (
            r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
            r"/([0-9]|[1-2][0-9]|3[0-2])$"
        ),
        "description": "IPv4 CIDR (e.g. 192.168.0.0/24)",
    },
    "unix_path": {
        "pattern": r"^(/[^/\0]+)+/?$",
        "description": "Absolute Unix filesystem path",
    },
    "unix_path_or_empty": {
        "pattern": r"^((/[^/\0]+)+/?)?$",
        "description": "Absolute Unix path or empty",
    },
    "https_url": {
        "pattern": r"^https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+$",
        "description": "HTTPS URL",
    },
    "http_url": {
        "pattern": r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+$",
        "description": "HTTP or HTTPS URL",
    },
    "registry_host": {
        "pattern": (
            r"^[A-Za-z0-9]([A-Za-z0-9._\-]*[A-Za-z0-9])?"
            r"(:[0-9]{1,5})?(/[A-Za-z0-9._\-]+)*$"
        ),
        "description": "Container registry host[:port][/path]",
    },
    "image_ref": {
        "pattern": (
            r"^[A-Za-z0-9]([A-Za-z0-9._\-/:@]*[A-Za-z0-9])?$"
        ),
        "description": "Container image reference",
    },
    "registry_path": {
        "pattern": r"^[A-Za-z0-9]([A-Za-z0-9._\-/]*[A-Za-z0-9])?$",
        "description": "Registry repository path",
    },
    "yes_no": {
        "pattern": r"(?i)^(yes|no|true|false|1|0)$",
        "description": "Boolean yes/no",
    },
    "vlan": {
        "pattern": (
            r"^([1-9]|[1-9][0-9]|[1-9][0-9]{2}|[1-3][0-9]{3}|40[0-8][0-9]|409[0-4])$"
        ),
        "description": "VLAN ID 1-4094",
    },
    "mtu": {
        "pattern": r"^[1-9][0-9]{2,4}$",
        "description": "MTU (100-99999)",
    },
    "mac": {
        "pattern": r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        "description": "MAC address",
    },
    "iface": {
        "pattern": r"^[A-Za-z][A-Za-z0-9._\-]{0,31}$",
        "description": "Network interface name",
    },
    "username": {
        "pattern": r"^[A-Za-z_][A-Za-z0-9._\-]{0,63}$",
        "description": "Unix / SSH username",
    },
    "org_id": {
        "pattern": r"^[A-Za-z0-9_\-]{1,64}$",
        "description": "Red Hat Organization ID",
    },
    "activation_key": {
        "pattern": r"^[A-Za-z0-9._\-]{1,256}$",
        "description": "Red Hat activation key",
    },
    "cni_version": {
        "pattern": r"^[0-9]+\.[0-9]+(\.[0-9]+)?$",
        "description": "CNI version (e.g. 0.3.1)",
    },
    "semver_minor": {
        "pattern": r"^[0-9]+\.[0-9]+$",
        "description": "Major.minor version (e.g. 18.0)",
    },
    "integer": {
        "pattern": r"^[0-9]+$",
        "description": "Non-negative integer",
    },
    "ntp_list": {
        "pattern": (
            r"^([A-Za-z0-9]([A-Za-z0-9.\-]*[A-Za-z0-9])?)"
            r"(,\s*[A-Za-z0-9]([A-Za-z0-9.\-]*[A-Za-z0-9])?)*$"
        ),
        "description": "Comma-separated NTP hostnames",
    },
    "bonding_options": {
        # Linux kernel bonding_options for linux_bond (RHOSO / os-net-config).
        # Space-separated key=value pairs. Supports official examples and RHEL modes:
        #   mode=802.3ad|active-backup|balance-rr|balance-xor|broadcast|balance-tlb|balance-alb|0-6
        #   lacp_rate=fast|slow
        #   updelay / miimon / downdelay (ms)
        #   xmit_hash_policy=layer2|layer2+3|layer3+4|encap2+3|encap3+4|vlan+srcmac
        #   arp_ip_target=ip[,ip...]  primary=iface  ad_select=...  etc.
        "pattern": (
            r"^(?:"
            r"[A-Za-z_][A-Za-z0-9_]*="
            r"[A-Za-z0-9._+\-:]+"
            r"(?:,[A-Za-z0-9._+\-:]+)*"
            r"(?:\s+[A-Za-z_][A-Za-z0-9_]*="
            r"[A-Za-z0-9._+\-:]+"
            r"(?:,[A-Za-z0-9._+\-:]+)*"
            r")*"
            r")$"
        ),
        "description": (
            "Linux bonding_options key=value string "
            "(e.g. mode=802.3ad lacp_rate=fast updelay=1000 miimon=100 "
            "xmit_hash_policy=layer3+4)"
        ),
    },
    "ovs_extra": {
        "pattern": r"^[A-Za-z0-9=_\-.\s/]+$",
        "description": "OVS extra arguments",
    },
    "free_text": {
        "pattern": r"^[\s\S]{0,2048}$",
        "description": "Free-form text (max 2048)",
    },
    "enum_type": {
        "pattern": r"(?i)^(rhoso|red\s*hat\s*openstack\s*services\s*on\s*openshift)$",
        "description": "CIQ Type = RHOSO",
    },
    "enum_environment": {
        "pattern": r"(?i)^(lab|test|staging|prod|development)$",
        "description": "Environment",
    },
    "enum_rhoso_version": {
        "pattern": r"^18\.0$",
        "description": "Supported RHOSO version",
    },
    "enum_rhocp_version": {
        "pattern": r"^4\.(1[4-8]|[0-9]{1,2})$",
        "description": "RHOCP version 4.x",
    },
    "enum_deployment_mode": {
        "pattern": r"(?i)^(connected|disconnected|airgapped|offline)$",
        "description": "Deployment mode",
    },
    "enum_storage_backend": {
        "pattern": (
            r"(?i)^[A-Za-z][A-Za-z0-9 +\-/().]*[A-Za-z0-9)]$"
        ),
        "description": "Storage backend (e.g. NFS, Ceph, Local Storage Operator, NetApp ONTAP FC (Trident))",
    },
    "enum_ovn_gateway": {
        "pattern": r"(?i)^(control-plane|data-plane|networker)$",
        "description": "OVN gateway placement",
    },
    "enum_dp_mode": {
        "pattern": r"(?i)^(pre-provisioned|unprovisioned)$",
        "description": "Data plane provisioning mode",
    },
    "enum_edpm_topology": {
        "pattern": (
            r"(?i)^(single_nic_vlans|dual_nic_bond|ovs_bond|linux_bond|"
            r"ovs_dpdk)$"
        ),
        "description": (
            "EDPM network config topology "
            "(CIQ-driven template generation; no custom Jinja upload)"
        ),
    },
    "enum_edpm_bridge": {
        "pattern": r"(?i)^(ovs_bridge|ovs_user_bridge)$",
        "description": "EDPM bridge type",
    },
    "enum_subscription": {
        "pattern": r"(?i)^(activation_key|username_password)$",
        "description": "Subscription method",
    },
    "enum_catalog_source": {
        "pattern": (
            r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$"
        ),
        "description": "CatalogSource / Operator source name",
    },
    "enum_network_purpose": {
        "pattern": (
            r"(?i)^(Control plane|Internal API|Storage|Storage management|"
            r"Tenant|External( / floating IP)?|Octavia|Designate|Designateext)$"
        ),
        "description": "Network purpose",
    },
    "enum_nad_type": {
        "pattern": r"(?i)^(macvlan|bridge|ipvlan)$",
        "description": "NAD type",
    },
    "enum_dp_role": {
        "pattern": r"(?i)^(compute|networker|compute-networker)$",
        "description": "Data plane node role",
    },
    "enum_cpu_pinning": {
        "pattern": r"(?i)^(enabled|disabled)$",
        "description": "CPU pinning",
    },
    "enum_numa": {
        "pattern": r"(?i)^(default)$",
        "description": "NUMA topology",
    },
    "bmc_address": {
        "pattern": (
            r"^(ipmi|redfish|redfish-virtualmedia|idrac|ilo5?)://"
            r".+$"
        ),
        "description": "BMC / Redfish address URI",
    },
    "device_path": {
        "pattern": r"^/dev/[A-Za-z0-9/_\-]+$",
        "description": "Linux device path (e.g. /dev/sda)",
    },
    "enum_boot_mode": {
        "pattern": r"(?i)^(UEFI|legacy|UEFISecureBoot)$",
        "description": "Boot mode (UEFI, legacy, UEFISecureBoot)",
    },
}


def _param(
    name: str,
    type_name: str,
    *,
    table: str,
    required: bool = True,
    when: str = "always",
    description: str = "",
) -> dict[str, Any]:
    type_meta = CIQ_TYPES[type_name]
    return {
        "name": name,
        "table": table,
        "type": type_name,
        "pattern": type_meta["pattern"],
        "required": required,
        "when": when,
        "description": description or type_meta["description"],
    }


def _field(
    name: str,
    type_name: str,
    *,
    required: bool = True,
    when: str = "always",
    description: str = "",
) -> dict[str, Any]:
    type_meta = CIQ_TYPES[type_name]
    return {
        "name": name,
        "type": type_name,
        "pattern": type_meta["pattern"],
        "required": required,
        "when": when,
        "description": description or type_meta["description"],
    }


# ---------------------------------------------------------------------------
# Parameter schema (merged rhoso_details + supplemental tables)
# when: always | disconnected | activation_key | username_password
#       | pre_provisioned | unprovisioned | edpm_bond | edpm_dpdk
# ---------------------------------------------------------------------------

RHOSO_PARAMETER_SCHEMA: list[dict[str, Any]] = [
    # rhoso_details
    _param("Cluster Name", "cluster_name", table="rhoso_details", required=True),
    _param("Type", "enum_type", table="rhoso_details", required=True),
    _param("Environment", "enum_environment", table="rhoso_details", required=True),
    _param("RHOSO Version", "enum_rhoso_version", table="rhoso_details", required=True),
    _param("RHOCP Version", "enum_rhocp_version", table="rhoso_details", required=True),
    _param(
        "Deployment Mode", "enum_deployment_mode", table="rhoso_details", required=True
    ),
    _param(
        "Multi Environment on Single RHOCP",
        "yes_no",
        table="rhoso_details",
        required=True,
    ),
    _param(
        "OpenStack Namespace", "k8s_name", table="rhoso_details", required=True
    ),
    _param(
        "OpenStack Operators Namespace",
        "k8s_name",
        table="rhoso_details",
        required=True,
    ),
    _param(
        "FIPS Enabled",
        "yes_no",
        table="rhoso_details",
        required=False,
        description="Enable FIPS 140-3 compliance checks and iSCSI CHAP configuration",
    ),
    _param(
        "Description",
        "free_text",
        table="rhoso_details",
        required=False,
    ),
    # rhoso_access
    _param("Kubeconfig Path", "unix_path", table="rhoso_access", required=True),
    _param("RHOCP API URL", "https_url", table="rhoso_access", required=False),
    _param("Pull Secret Path", "unix_path", table="rhoso_access", required=True),
    # rhoso_disconnected (required only when disconnected)
    _param(
        "Mirror Registry URL",
        "registry_host",
        table="rhoso_disconnected",
        required=True,
        when="disconnected",
    ),
    _param(
        "Mirror Registry CA Path",
        "unix_path",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Mirror Pull Secret Path",
        "unix_path",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "ImageDigestMirrorSet Name",
        "k8s_name",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "ImageTagMirrorSet Name",
        "k8s_name",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "ImageContentSourcePolicy Name",
        "k8s_name",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Disable Default CatalogSources",
        "yes_no",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "CatalogSource Name",
        "enum_catalog_source",
        table="rhoso_disconnected",
        required=True,
        when="disconnected",
    ),
    _param(
        "CatalogSource Namespace",
        "k8s_name",
        table="rhoso_disconnected",
        required=True,
        when="disconnected",
    ),
    _param(
        "CatalogSource Image",
        "image_ref",
        table="rhoso_disconnected",
        required=True,
        when="disconnected",
    ),
    _param(
        "Operator Source",
        "enum_catalog_source",
        table="rhoso_disconnected",
        required=True,
        when="disconnected",
    ),
    _param(
        "Operator Source Namespace",
        "k8s_name",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Mirrored Registry OpenStack Path",
        "registry_path",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Data Plane Container Registry",
        "registry_host",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Data Plane YUM Mirror URL",
        "http_url",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    _param(
        "Satellite Capsule URL",
        "https_url",
        table="rhoso_disconnected",
        required=False,
        when="disconnected",
    ),
    # rhoso_storage
    _param("Storage Class", "k8s_name", table="rhoso_storage", required=True),
    _param(
        "Storage Backend",
        "enum_storage_backend",
        table="rhoso_storage",
        required=False,
    ),
    # rhoso_control_plane
    _param(
        "Control Plane CR Name",
        "k8s_name",
        table="rhoso_control_plane",
        required=True,
    ),
    _param(
        "Control Plane FQDN", "fqdn", table="rhoso_control_plane", required=False
    ),
    _param("Public VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("OSP Secret Name", "k8s_name", table="rhoso_control_plane", required=True),
    _param(
        "Management Network Name",
        "dns_label",
        table="rhoso_control_plane",
        required=False,
        description="Optional when Purpose=Control plane is set on a network row",
    ),
    _param(
        "Internal API Network Name",
        "dns_label",
        table="rhoso_control_plane",
        required=False,
        description="Optional when Purpose=Internal API is set on a network row",
    ),
    _param(
        "MetalLB Namespace", "k8s_name", table="rhoso_control_plane", required=True
    ),
    _param(
        "NAD CNI Version", "cni_version", table="rhoso_control_plane", required=True
    ),
    _param("Internal API VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("Cell1 RabbitMQ VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("RabbitMQ VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("Glance Internal VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("Cinder Internal VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("Neutron Internal VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param("Nova Internal VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param(
        "Placement Internal VIP", "ipv4", table="rhoso_control_plane", required=False
    ),
    _param("Datacentre NIC", "iface", table="rhoso_control_plane", required=False),
    _param("Public Interface", "iface", table="rhoso_control_plane", required=False),
    _param(
        "Worker NNCP Interface", "iface", table="rhoso_control_plane", required=True
    ),
    _param(
        "OVN Gateway Placement",
        "enum_ovn_gateway",
        table="rhoso_control_plane",
        required=True,
    ),
    _param(
        "TLS Pod Level Enabled", "yes_no", table="rhoso_control_plane", required=False
    ),
    _param(
        "Operator Channel", "free_text", table="rhoso_control_plane", required=False
    ),
    _param(
        "Operator Install Plan Approval",
        "free_text",
        table="rhoso_control_plane",
        required=False,
    ),
    _param("DNS VIP", "ipv4", table="rhoso_control_plane", required=False),
    _param(
        "DNS Upstream Servers", "free_text", table="rhoso_control_plane", required=False
    ),
    _param(
        "Worker DNS Servers", "free_text", table="rhoso_control_plane", required=False
    ),
    _param(
        "Messaging Bus Cluster",
        "k8s_name",
        table="rhoso_control_plane",
        required=False,
        description="Default RabbitMQ cluster name for messagingBus (e.g. rabbitmq)",
    ),
    _param(
        "Notifications Bus Cluster",
        "k8s_name",
        table="rhoso_control_plane",
        required=False,
        description="Default RabbitMQ cluster name for notificationsBus (e.g. rabbitmq)",
    ),
    # rhoso_services
    _param("Horizon Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Heat Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Telemetry Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Barbican Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Octavia Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Designate Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Ironic Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Manila Enabled", "yes_no", table="rhoso_services", required=False),
    _param("Watcher Enabled", "yes_no", table="rhoso_services", required=False,
           description="Enable Watcher (Optimize) service for resource optimization"),
    _param("Node Health Check Operator Enabled", "yes_no", table="rhoso_services",
           required=False, description="Install Node Health Check Operator for HA failover"),
    _param("Self Node Remediation Operator Enabled", "yes_no", table="rhoso_services",
           required=False, description="Install Self Node Remediation Operator for HA failover"),
    _param("Fence Agents Remediation Operator Enabled", "yes_no", table="rhoso_services",
           required=False, description="Install Fence Agents Remediation Operator for HA failover"),
    # Prerequisite Operator flags (v1.4)
    _param("LSO Enabled", "yes_no", table="rhoso_services", required=False,
           description="Install Local Storage Operator prerequisite"),
    _param("Observability Enabled", "yes_no", table="rhoso_services", required=False,
           description="Install Cluster Observability Operator prerequisite"),
    _param("Trident Enabled", "yes_no", table="rhoso_services", required=False,
           description="Install NetApp Trident CSI storage prerequisite"),
    _param("Glance Backend", "free_text", table="rhoso_services", required=False),
    _param("Glance Replicas", "integer", table="rhoso_services", required=False),
    _param("Nova API Replicas", "integer", table="rhoso_services", required=False),
    _param("Nova Scheduler Replicas", "integer", table="rhoso_services", required=False),
    _param(
        "Nova Conductor Cell0 Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param(
        "Nova Conductor Cell1 Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param("Nova Metadata Enabled", "yes_no", table="rhoso_services", required=False),
    _param(
        "Nova Cell1 Metadata Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param(
        "Nova Cell1 noVNC Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param("Neutron Replicas", "integer", table="rhoso_services", required=False),
    _param("Keystone Replicas", "integer", table="rhoso_services", required=False),
    _param("Cinder API Replicas", "integer", table="rhoso_services", required=False),
    _param(
        "Cinder Scheduler Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param("Barbican API Replicas", "integer", table="rhoso_services", required=False),
    _param(
        "Barbican Worker Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param("Placement Replicas", "integer", table="rhoso_services", required=False),
    _param("Horizon Replicas", "integer", table="rhoso_services", required=False),
    _param("Heat API Replicas", "integer", table="rhoso_services", required=False),
    _param("Heat Engine Replicas", "integer", table="rhoso_services", required=False),
    _param("Memcached Replicas", "integer", table="rhoso_services", required=False),
    _param("Galera Replicas", "integer", table="rhoso_services", required=False),
    _param("Galera Cell1 Replicas", "integer", table="rhoso_services", required=False),
    _param("RabbitMQ Replicas", "integer", table="rhoso_services", required=False),
    _param(
        "RabbitMQ Cell1 Replicas", "integer",
        table="rhoso_services", required=False,
    ),
    _param("DNS Replicas", "integer", table="rhoso_services", required=False),
    _param("OVN NB Replicas", "integer", table="rhoso_services", required=False),
    _param("OVN SB Replicas", "integer", table="rhoso_services", required=False),
    # rhoso_observability (JIO: D0.5_ObservabilityOperator/ — Cluster Observability Operator)
    _param(
        "Cluster Observability Enabled", "yes_no", table="rhoso_observability",
        required=False, description="Enable Cluster Observability Operator for monitoring",
    ),
    _param(
        "Observability Operator Channel", "free_text", table="rhoso_observability",
        required=False, description="OLM channel for Cluster Observability Operator",
    ),
    _param(
        "Observability Install Plan Approval", "free_text", table="rhoso_observability",
        required=False, description="Install plan approval mode (Automatic or Manual)",
    ),
    _param(
        "Observability Monitoring Stack Enabled", "yes_no", table="rhoso_observability",
        required=False, description="Enable MonitoringStack CR for cluster metrics",
    ),
    _param(
        "Observability Monitoring Stack Name", "k8s_name", table="rhoso_observability",
        required=False, description="Name of the MonitoringStack CR instance",
    ),
    # rhoso_pv_sizing
    _param(
        "Galera Storage Request", "free_text", table="rhoso_pv_sizing", required=False
    ),
    _param(
        "Galera Cell1 Storage Request", "free_text",
        table="rhoso_pv_sizing", required=False,
    ),
    _param(
        "OVN NB Storage Request", "free_text", table="rhoso_pv_sizing", required=False
    ),
    _param(
        "OVN SB Storage Request", "free_text", table="rhoso_pv_sizing", required=False
    ),
    _param(
        "Telemetry Storage Request", "free_text",
        table="rhoso_pv_sizing", required=False,
    ),
    _param(
        "Telemetry Storage Class", "free_text",
        table="rhoso_pv_sizing", required=False,
    ),
    _param(
        "Telemetry Retention", "free_text", table="rhoso_pv_sizing", required=False
    ),
    _param(
        "Telemetry Scrape Interval", "free_text",
        table="rhoso_pv_sizing", required=False,
    ),
    _param(
        "RabbitMQ CPU Limit", "free_text", table="rhoso_pv_sizing", required=False
    ),
    _param(
        "RabbitMQ Memory Limit", "free_text", table="rhoso_pv_sizing", required=False
    ),
    # rhoso_cinder_backend
    _param(
        "Cinder Default Volume Type", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder Volume Backend Name", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder Volume Driver", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder Storage Protocol", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder NetApp Server Hostname", "host_or_ip",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder NetApp Vserver", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder Volume Secret Name", "k8s_name",
        table="rhoso_cinder_backend", required=False,
    ),
    _param(
        "Cinder Volume Network Attachments", "free_text",
        table="rhoso_cinder_backend", required=False,
    ),
    # rhoso_neutron_config
    _param(
        "Neutron Global Physnet MTU", "integer",
        table="rhoso_neutron_config", required=False,
    ),
    _param(
        "Neutron Physical Network MTUs", "free_text",
        table="rhoso_neutron_config", required=False,
    ),
    _param(
        "Neutron API Timeout", "integer", table="rhoso_neutron_config", required=False
    ),
    _param(
        "OVN Emit Need To Frag", "yes_no", table="rhoso_neutron_config", required=False
    ),
    _param(
        "MAC Binding Age Threshold",
        "integer",
        table="rhoso_neutron_config",
        required=False,
        description="OVN MAC_Binding age threshold — set to 0 for RHOSO 18.0 known issue (default 300)",
    ),
    # rhoso_ceph_storage (Plan PDF: Storage features & topologies, Install PDF: Ceph integration)
    _param(
        "Ceph External", "yes_no", table="rhoso_ceph_storage", required=False,
        description="Use external Red Hat Ceph Storage cluster",
    ),
    _param(
        "Ceph Cluster Name", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph cluster name (e.g. ceph)",
    ),
    _param(
        "Ceph FSID", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph cluster FSID (UUID from ceph fsid)",
    ),
    _param(
        "Ceph Mon Host", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph monitor hosts (comma-separated IPs)",
    ),
    _param(
        "Ceph Client Name", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph client auth user (e.g. openstack)",
    ),
    _param(
        "Ceph Client Key Path", "unix_path_or_empty", table="rhoso_ceph_storage",
        required=False, description="Path to Ceph client keyring file",
    ),
    _param(
        "Ceph Pool Volumes", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph RBD pool for Block Storage (cinder) volumes",
    ),
    _param(
        "Ceph Pool Images", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph RBD pool for Image service (glance) images",
    ),
    _param(
        "Ceph Pool VMs", "free_text", table="rhoso_ceph_storage", required=False,
        description="Ceph RBD pool for Compute (nova) ephemeral disks",
    ),
    _param(
        "Ceph RGW Enabled", "yes_no", table="rhoso_ceph_storage", required=False,
        description="Enable Ceph RADOS Gateway for Object Storage integration",
    ),
    _param(
        "Ceph RGW Endpoint", "http_url", table="rhoso_ceph_storage", required=False,
        description="Ceph RGW endpoint URL (e.g. https://rgw.example.com:8080)",
    ),
    _param(
        "Ceph RGW TLS Enabled", "yes_no", table="rhoso_ceph_storage", required=False,
        description="Enable TLS for Ceph RGW endpoint",
    ),
    # rhoso_trident_storage (JIO: D1.3_NetApp/Trident-configuration.txt, TridentBackendConfig, TridentOrchestrator)
    _param(
        "Trident Enabled", "yes_no", table="rhoso_trident_storage", required=False,
        description="Enable NetApp Trident CSI storage provisioner",
    ),
    _param(
        "Trident Image Registry", "registry_host", table="rhoso_trident_storage",
        required=False, description="Container registry for Trident images",
    ),
    _param(
        "Trident Image", "image_ref", table="rhoso_trident_storage", required=False,
        description="Trident controller container image reference",
    ),
    _param(
        "Trident Autosupport Image", "image_ref", table="rhoso_trident_storage",
        required=False, description="Trident autosupport telemetry image reference",
    ),
    _param(
        "Trident Backend Name", "free_text", table="rhoso_trident_storage",
        required=False, description="TridentBackendConfig backend name",
    ),
    _param(
        "Trident Storage Driver Name", "free_text", table="rhoso_trident_storage",
        required=False, description="Trident storage driver (e.g. ontap-san, ontap-nas)",
    ),
    _param(
        "Trident Management LIF", "host_or_ip", table="rhoso_trident_storage",
        required=False, description="NetApp ONTAP management LIF IP/hostname",
    ),
    _param(
        "Trident Data LIF", "host_or_ip", table="rhoso_trident_storage",
        required=False, description="NetApp ONTAP data LIF IP/hostname for iSCSI/NFS",
    ),
    _param(
        "Trident SVM", "free_text", table="rhoso_trident_storage", required=False,
        description="NetApp ONTAP Storage Virtual Machine (Vserver) name",
    ),
    _param(
        "Trident Secret Name", "k8s_name", table="rhoso_trident_storage",
        required=False, description="Kubernetes Secret with ONTAP credentials for Trident",
    ),
    _param(
        "Trident Storage Class Name", "k8s_name", table="rhoso_trident_storage",
        required=False, description="StorageClass name provisioned by Trident",
    ),
    _param(
        "Trident Volume Binding Mode", "free_text", table="rhoso_trident_storage",
        required=False, description="Volume binding mode (Immediate or WaitForFirstConsumer)",
    ),
    # rhoso_lso_storage (JIO: D0.6_LSO/ — LocalVolumeDiscovery, LocalVolumeSet, Subscription)
    _param(
        "LSO Enabled", "yes_no", table="rhoso_lso_storage", required=False,
        description="Enable Local Storage Operator for local disk provisioning",
    ),
    _param(
        "LSO Storage Class Name", "k8s_name", table="rhoso_lso_storage",
        required=False, description="StorageClass name created by LSO",
    ),
    _param(
        "LSO Device Types", "free_text", table="rhoso_lso_storage", required=False,
        description="Device types to discover (e.g. disk, part)",
    ),
    _param(
        "LSO Device Mechanical Properties", "free_text", table="rhoso_lso_storage",
        required=False, description="Mechanical properties filter (e.g. NonRotational, Rotational)",
    ),
    _param(
        "LSO Min Device Size", "free_text", table="rhoso_lso_storage", required=False,
        description="Minimum device size for discovery (e.g. 100Gi)",
    ),
    _param(
        "LSO Volume Mode", "free_text", table="rhoso_lso_storage", required=False,
        description="PV volume mode (Block or Filesystem)",
    ),
    _param(
        "LSO Node Selector Label", "free_text", table="rhoso_lso_storage",
        required=False, description="Node selector label for LSO volume discovery/set",
    ),
    # rhoso_multipath (JIO: D1.3_NetApp/multi-path-config.conf — iSCSI/FC multipath)
    _param(
        "Multipath Enabled", "yes_no", table="rhoso_multipath", required=False,
        description="Enable multipath configuration for iSCSI/FC storage",
    ),
    _param(
        "Multipath Config Secret Name", "k8s_name", table="rhoso_multipath",
        required=False, description="Kubernetes Secret holding multipath.conf content",
    ),
    _param(
        "Multipath User Friendly Names", "yes_no", table="rhoso_multipath",
        required=False, description="Use user-friendly names in multipath.conf (yes/no)",
    ),
    _param(
        "Multipath Find Multipaths", "yes_no", table="rhoso_multipath",
        required=False, description="Auto-detect multipaths in multipath.conf (yes/no)",
    ),
    # rhoso_edpm_network_config
    _param(
        "Physical Bridge Name",
        "iface",
        table="rhoso_edpm_network_config",
        required=True,
    ),
    _param(
        "EDPM Network Config Topology",
        "enum_edpm_topology",
        table="rhoso_edpm_network_config",
        required=True,
    ),
    _param(
        "EDPM Network Config Nmstate",
        "yes_no",
        table="rhoso_edpm_network_config",
        required=True,
    ),
    _param(
        "EDPM Network Config Update",
        "yes_no",
        table="rhoso_edpm_network_config",
        required=True,
    ),
    _param(
        "EDPM Bridge Type",
        "enum_edpm_bridge",
        table="rhoso_edpm_network_config",
        required=True,
    ),
    _param(
        "EDPM NIC1 Name", "iface", table="rhoso_edpm_network_config", required=True
    ),
    _param(
        "EDPM NIC2 Name",
        "iface",
        table="rhoso_edpm_network_config",
        required=True,
        when="edpm_bond",
    ),
    _param(
        "EDPM Bond Name",
        "iface",
        table="rhoso_edpm_network_config",
        required=True,
        when="edpm_bond",
    ),
    _param(
        "EDPM Bonding Options",
        "bonding_options",
        table="rhoso_edpm_network_config",
        required=False,
        when="edpm_bond",
    ),
    _param(
        "EDPM Use DHCP", "yes_no", table="rhoso_edpm_network_config", required=True
    ),
    _param(
        "EDPM Use DHCPv6", "yes_no", table="rhoso_edpm_network_config", required=True
    ),
    _param(
        "EDPM DPDK MTU",
        "mtu",
        table="rhoso_edpm_network_config",
        required=True,
        when="edpm_dpdk",
    ),
    _param(
        "EDPM DPDK RX Queue",
        "integer",
        table="rhoso_edpm_network_config",
        required=False,
        when="edpm_dpdk",
    ),
    _param(
        "EDPM DPDK OVS Extra",
        "ovs_extra",
        table="rhoso_edpm_network_config",
        required=False,
        when="edpm_dpdk",
    ),
    _param(
        "NTP Servers", "ntp_list", table="rhoso_edpm_network_config", required=False
    ),
    _param(
        "Registry Secret Name",
        "k8s_name",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM OVN Bridge Mappings",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM Tuned Profile",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM Kernel Args",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM CPU Dedicated Set",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM Reserved Host Memory MB",
        "integer",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM Initial CPU Allocation Ratio",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM SSHD Allowed Ranges",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    _param(
        "EDPM Bootstrap Command",
        "free_text",
        table="rhoso_edpm_network_config",
        required=False,
    ),
    # rhoso_data_plane
    _param(
        "Data Plane NodeSet Name",
        "k8s_name",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Data Plane Deployment Name",
        "k8s_name",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Data Plane Provisioning Mode",
        "enum_dp_mode",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Data Plane SSH User", "username", table="rhoso_data_plane", required=True
    ),
    _param(
        "Data Plane SSH Private Key Path",
        "unix_path",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Data Plane Ansible EE Image",
        "image_ref",
        table="rhoso_data_plane",
        required=False,
    ),
    _param(
        "Ansible SSH Secret Name",
        "k8s_name",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Nova Migration Secret Name",
        "k8s_name",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Subscription Secret Name",
        "k8s_name",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Libvirt Secret Name", "k8s_name", table="rhoso_data_plane", required=True
    ),
    _param(
        "Subscription Method",
        "enum_subscription",
        table="rhoso_data_plane",
        required=True,
    ),
    _param(
        "Red Hat Organization ID",
        "org_id",
        table="rhoso_data_plane",
        required=True,
        when="activation_key",
    ),
    _param(
        "Red Hat Activation Key",
        "activation_key",
        table="rhoso_data_plane",
        required=True,
        when="activation_key",
    ),
    _param(
        "Red Hat Username",
        "username",
        table="rhoso_data_plane",
        required=True,
        when="username_password",
    ),
]


# ---------------------------------------------------------------------------
# Network row schema (rhoso_networks is a list of networks)
# ---------------------------------------------------------------------------

RHOSO_NETWORK_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Network Name", "dns_label", required=True),
    _field("CIDR", "cidr", required=True),
    _field("VLAN", "vlan", required=False),
    _field("Gateway", "ipv4", required=False),
    _field("MTU", "mtu", required=True),
    _field("Purpose", "enum_network_purpose", required=True),
    _field("DNS Domain", "dns_domain", required=True),
    _field("Subnet Name", "dns_label", required=True),
    _field("Allocation Start", "ipv4", required=True),
    _field("Allocation End", "ipv4", required=True),
    _field("Whereabouts Start", "ipv4", required=True),
    _field("Whereabouts End", "ipv4", required=True),
    _field("MetalLB Start", "ipv4", required=False),
    _field("MetalLB End", "ipv4", required=False),
    _field("NAD Master Interface", "iface", required=True),
    _field("NAD Type", "enum_nad_type", required=True),
]


# ---------------------------------------------------------------------------
# Data plane node row schema (rhoso_data_plane_nodes is a list)
# ---------------------------------------------------------------------------

RHOSO_NODE_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Node Name", "dns_label", required=True),
    _field("Ansible Host", "host_or_ip", required=True, when="pre_provisioned"),
    _field("Role", "enum_dp_role", required=True),
    _field("Management IP", "ipv4", required=True, when="pre_provisioned"),
    _field("NIC1 MAC", "mac", required=False),
    _field("NIC2 MAC", "mac", required=False),
    _field("NUMA Topology", "enum_numa", required=False),
    _field("CPU Pinning", "enum_cpu_pinning", required=False),
    _field("BMC Address", "bmc_address", required=True, when="unprovisioned"),
    _field("Boot MAC Address", "mac", required=True, when="unprovisioned"),
    _field("BMH Namespace", "k8s_name", required=False, when="unprovisioned"),
    _field("Root Device Hint", "device_path", required=False, when="unprovisioned"),
    _field("Boot Mode", "enum_boot_mode", required=False, when="unprovisioned"),
    _field("Provisioning NIC", "iface", required=False, when="unprovisioned"),
    _field("Provisioning VLAN", "vlan", required=False, when="unprovisioned"),
    _field("Provisioning IP", "ipv4", required=False, when="unprovisioned"),
]


SCHEMA_VERSION = "1.4"


def get_validation_schema() -> dict[str, Any]:
    """Return JSON-serializable schema for Ansible validation tasks."""
    return {
        "schema_version": SCHEMA_VERSION,
        "types": CIQ_TYPES,
        "parameters": RHOSO_PARAMETER_SCHEMA,
        "network_fields": RHOSO_NETWORK_FIELD_SCHEMA,
        "node_fields": RHOSO_NODE_FIELD_SCHEMA,
        "rules": {
            "networks_min_count": 1,
            "nodes_min_count_pre_provisioned": 1,
            "disconnected_modes": ["disconnected", "airgapped", "offline"],
        },
    }
