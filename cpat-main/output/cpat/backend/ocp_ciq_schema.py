# -*- coding: utf-8 -*-
"""OCP CIQ field types and regexp patterns (CPAT backend copy).

Master source: output/ciq-generators/ocp_ciq_schema.py
This file MUST stay in sync with the master. The only difference is:
  - CIQ_TYPES is imported from rhoso_ciq_schema (shared CPAT type library)
    then extended with OCP-specific types
  - _param()/_field() helpers include consumed_by kwarg

Schema: 129 parameters across 18 tables (14 param + 4 row).
OCP versions: 4.17, 4.18, 4.19, 4.20
Install methods: ABI, IPI-BM, UPI-BM, ABI-DC, SNO
"""

from __future__ import annotations

from typing import Any

from rhoso_ciq_schema import CIQ_TYPES


# ---------------------------------------------------------------------------
# OCP-specific types (extend the shared CIQ_TYPES)
# Type NAMES must match the standalone schema exactly.
# ---------------------------------------------------------------------------

CIQ_TYPES["ipv4_or_ipv6"] = {
    "pattern": (
        r"^("
        r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
        r"|"
        r"([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
        r"|"
        r"([0-9a-fA-F]{1,4}:){1,7}:"
        r"|"
        r"::"
        r")$"
    ),
    "description": "IPv4 or IPv6 address",
}
CIQ_TYPES["cidr_v4_or_v6"] = {
    "pattern": (
        r"^("
        r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/([0-9]|[12][0-9]|3[0-2])"
        r"|"
        r"[0-9a-fA-F:]+/([0-9]|[1-9][0-9]|1[01][0-9]|12[0-8])"
        r")$"
    ),
    "description": "IPv4 or IPv6 CIDR",
}
CIQ_TYPES["secret_text"] = {
    "pattern": r"^[\s\S]{1,4096}$",
    "description": "Secret / password (never store plaintext — use path references)",
}
CIQ_TYPES["port"] = {
    "pattern": r"^([1-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$",
    "description": "TCP/UDP port (1-65535)",
}
CIQ_TYPES["pem_cert"] = {
    "pattern": r"^[\s\S]*-----BEGIN CERTIFICATE-----[\s\S]*-----END CERTIFICATE-----[\s\S]*$",
    "description": "PEM-encoded X.509 certificate",
}
CIQ_TYPES["enum_ocp_version"] = {
    "pattern": r"^4\.(1[7-9]|[2-9][0-9])$",
    "description": "OCP version 4.17+",
}
CIQ_TYPES["enum_install_method"] = {
    "pattern": r"(?i)^(ABI|IPI-BM|UPI-BM|ABI-DC|SNO)$",
    "description": "OCP install method: ABI, IPI-BM, UPI-BM, ABI-DC, SNO",
}
CIQ_TYPES["enum_platform"] = {
    "pattern": r"(?i)^(baremetal|vsphere|none|external)$",
    "description": "OCP platform type",
}
CIQ_TYPES["enum_network_type"] = {
    "pattern": r"(?i)^(OVNKubernetes|OpenShiftSDN)$",
    "description": "OCP network plugin (OVNKubernetes recommended)",
}
CIQ_TYPES["enum_architecture"] = {
    "pattern": r"(?i)^(amd64|arm64|ppc64le|s390x|multi)$",
    "description": "CPU architecture",
}
CIQ_TYPES["enum_hyperthreading"] = {
    "pattern": r"(?i)^(Enabled|Disabled)$",
    "description": "Hyperthreading state",
}
CIQ_TYPES["enum_publish"] = {
    "pattern": r"(?i)^(External|Internal)$",
    "description": "API/Routes publish mode",
}
CIQ_TYPES["enum_credentials_mode"] = {
    "pattern": r"(?i)^(Mint|Passthrough|Manual|)$",
    "description": "Cloud Credential Operator mode",
}
CIQ_TYPES["enum_cpu_partitioning"] = {
    "pattern": r"(?i)^(None|AllNodes)$",
    "description": "CPU partitioning mode",
}
CIQ_TYPES["enum_provisioning_network"] = {
    "pattern": r"(?i)^(Managed|Disabled)$",
    "description": "Provisioning network mode (IPI)",
}
CIQ_TYPES["enum_host_role"] = {
    "pattern": r"(?i)^(master|worker)$",
    "description": "OCP host role",
}
CIQ_TYPES["enum_iface_type"] = {
    "pattern": r"(?i)^(ethernet|bond|vlan|bridge|ovs-bridge)$",
    "description": "NMState interface type",
}
CIQ_TYPES["enum_iface_state"] = {
    "pattern": r"(?i)^(up|down|absent)$",
    "description": "NMState interface state",
}
CIQ_TYPES["enum_bond_mode"] = {
    "pattern": (
        r"(?i)^(balance-rr|active-backup|balance-xor|broadcast|"
        r"802\.3ad|balance-tlb|balance-alb|[0-6])$"
    ),
    "description": "Linux bond mode",
}
CIQ_TYPES["enum_lb_type"] = {
    "pattern": r"(?i)^(HAProxy|MetalLB|F5|external|none)$",
    "description": "Load balancer type",
}
CIQ_TYPES["enum_dns_record_type"] = {
    "pattern": r"(?i)^(A|AAAA|CNAME|PTR|SRV)$",
    "description": "DNS record type",
}
CIQ_TYPES["enum_dns_purpose"] = {
    "pattern": (
        r"(?i)^(api|api-int|apps-wildcard|master|worker|etcd|bootstrap)$"
    ),
    "description": "DNS record purpose",
}
CIQ_TYPES["enum_storage_class_driver"] = {
    "pattern": r"(?i)^(NFS|ODF|LSO|Trident|ebs|vsphere|hostpath|none)$",
    "description": "Storage class driver",
}
CIQ_TYPES["enum_install_plan_approval"] = {
    "pattern": r"(?i)^(Automatic|Manual)$",
    "description": "OLM install plan approval",
}
CIQ_TYPES["enum_endpoint_publishing"] = {
    "pattern": r"(?i)^(LoadBalancerService|HostNetwork|NodePortService|Private)$",
    "description": "Ingress endpoint publishing strategy",
}
CIQ_TYPES["enum_wildcard_policy"] = {
    "pattern": r"(?i)^(WildcardsAllowed|WildcardsDisallowed)$",
    "description": "Ingress wildcard policy",
}
CIQ_TYPES["enum_ip_family"] = {
    "pattern": r"(?i)^(IPv4|IPv6|DualStack)$",
    "description": "IP address family",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _param(
    name: str,
    type_name: str,
    *,
    table: str,
    required: bool = True,
    when: str = "always",
    description: str = "",
    consumed_by: str = "",
) -> dict[str, Any]:
    type_meta = CIQ_TYPES[type_name]
    entry: dict[str, Any] = {
        "name": name,
        "table": table,
        "type": type_name,
        "pattern": type_meta["pattern"],
        "required": required,
        "when": when,
        "description": description or type_meta["description"],
    }
    if consumed_by:
        entry["consumed_by"] = consumed_by
    return entry


def _field(
    name: str,
    type_name: str,
    *,
    required: bool = True,
    when: str = "always",
    description: str = "",
    consumed_by: str = "",
) -> dict[str, Any]:
    type_meta = CIQ_TYPES[type_name]
    entry: dict[str, Any] = {
        "name": name,
        "type": type_name,
        "pattern": type_meta["pattern"],
        "required": required,
        "when": when,
        "description": description or type_meta["description"],
    }
    if consumed_by:
        entry["consumed_by"] = consumed_by
    return entry


# ---------------------------------------------------------------------------
# Parameter schema — 14 param tables, 129 parameters
# Table keys and parameter order MUST match the standalone schema.
# when: always | disconnected | abi | abi_dc | ipi_bm | upi_bm | sno
#       | platform_none | dual_stack
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.2"

OCP_PARAMETER_SCHEMA: list[dict[str, Any]] = [
    # ── ocp_cluster_details (15 params) ──
    _param("Type", "free_text", table="ocp_cluster_details", required=True,
           description="Must be 'OCP' — identifies this CIQ as an OCP registration"),
    _param("Cluster Name", "cluster_name", table="ocp_cluster_details", required=True,
           description="OCP cluster name — becomes <name>.<baseDomain> in DNS"),
    _param("Base Domain", "dns_domain", table="ocp_cluster_details", required=True,
           description="Base domain for the cluster (e.g. example.com)"),
    _param("OCP Version", "enum_ocp_version", table="ocp_cluster_details", required=True,
           description="OCP version to install (4.17, 4.18, 4.19, 4.20)"),
    _param("Install Method", "enum_install_method", table="ocp_cluster_details", required=True,
           description="Installation method: ABI, IPI-BM, UPI-BM, ABI-DC, SNO"),
    _param("Platform", "enum_platform", table="ocp_cluster_details", required=True,
           description="Platform type: baremetal, vsphere, none, external"),
    _param("Deployment Mode", "enum_deployment_mode", table="ocp_cluster_details", required=True,
           description="Connected or disconnected deployment"),
    _param("Architecture", "enum_architecture", table="ocp_cluster_details", required=True,
           description="CPU architecture: amd64, arm64, ppc64le, s390x, multi"),
    _param("Control Plane Replicas", "integer", table="ocp_cluster_details", required=True,
           description="Number of control plane nodes (3 for HA, 1 for SNO)"),
    _param("Compute Replicas", "integer", table="ocp_cluster_details", required=True,
           description="Number of compute/worker nodes (0 for SNO/compact)"),
    _param("Hyperthreading", "enum_hyperthreading", table="ocp_cluster_details", required=False,
           description="Enable/disable simultaneous multithreading (default: Enabled)"),
    _param("FIPS Mode", "yes_no", table="ocp_cluster_details", required=False,
           description="Enable FIPS 140-2/140-3 cryptographic compliance"),
    _param("Publish", "enum_publish", table="ocp_cluster_details", required=False,
           description="Publish mode for user-facing endpoints (default: External)"),
    _param("CPU Partitioning Mode", "enum_cpu_partitioning", table="ocp_cluster_details", required=False,
           description="Workload partitioning mode (None or AllNodes)"),
    _param("Feature Set", "free_text", table="ocp_cluster_details", required=False,
           description="Feature set to enable (e.g. TechPreviewNoUpgrade)"),

    # ── ocp_access (4 params) ──
    _param("Pull Secret Path", "unix_path", table="ocp_access", required=True,
           description="Path to pull-secret.json from Red Hat OpenShift Cluster Manager"),
    _param("SSH Public Key Path", "unix_path", table="ocp_access", required=True,
           description="Path to SSH public key for cluster node access"),
    _param("Kubeconfig Path", "unix_path_or_empty", table="ocp_access", required=False,
           description="Path to kubeconfig (generated post-install)"),
    _param("Credentials Mode", "enum_credentials_mode", table="ocp_access", required=False,
           description="Cloud Credential Operator mode (Mint, Passthrough, Manual)"),

    # ── ocp_networking (12 params) ──
    _param("Network Type", "enum_network_type", table="ocp_networking", required=True,
           description="Cluster network plugin (OVNKubernetes is the only supported value)"),
    _param("Cluster Network CIDR", "cidr_v4_or_v6", table="ocp_networking", required=True,
           description="IP address block for pods (default: 10.128.0.0/14)"),
    _param("Cluster Network Host Prefix", "integer", table="ocp_networking", required=True,
           description="Subnet prefix per node (default: 23 for IPv4, 64 for IPv6)"),
    _param("Service Network CIDR", "cidr_v4_or_v6", table="ocp_networking", required=True,
           description="IP address block for services (default: 172.30.0.0/16)"),
    _param("Machine Network CIDR", "cidr_v4_or_v6", table="ocp_networking", required=True,
           description="IP address block for machines (default: 10.0.0.0/16)"),
    _param("Cluster Network CIDR IPv6", "cidr_v4_or_v6", table="ocp_networking", required=False,
           when="dual_stack",
           description="IPv6 cluster network CIDR for dual-stack (e.g. fd01::/48)"),
    _param("Service Network CIDR IPv6", "cidr_v4_or_v6", table="ocp_networking", required=False,
           when="dual_stack",
           description="IPv6 service network CIDR for dual-stack (e.g. fd02::/112)"),
    _param("Machine Network CIDR IPv6", "cidr_v4_or_v6", table="ocp_networking", required=False,
           when="dual_stack",
           description="IPv6 machine network CIDR for dual-stack"),
    _param("IP Families", "enum_ip_family", table="ocp_networking", required=False,
           description="IP address family: IPv4, IPv6, or DualStack"),
    _param("Network MTU", "mtu", table="ocp_networking", required=False,
           description="Cluster-wide MTU (optional, platform default used if omitted)"),
    _param("Additional Trust Bundle", "free_text", table="ocp_networking", required=False,
           when="disconnected",
           description="PEM-encoded X.509 CA bundle added to nodes' trusted store"),
    _param("Additional Trust Bundle Path", "unix_path_or_empty", table="ocp_networking", required=False,
           when="disconnected",
           description="Path to CA bundle file (alternative to inline content)"),

    # ── ocp_proxy (5 params) ──
    _param("HTTP Proxy", "http_url", table="ocp_proxy", required=False,
           description="HTTP proxy URL for cluster egress traffic"),
    _param("HTTPS Proxy", "https_url", table="ocp_proxy", required=False,
           description="HTTPS proxy URL for cluster egress traffic"),
    _param("No Proxy", "free_text", table="ocp_proxy", required=False,
           description="Comma-separated list of domains/CIDRs to exclude from proxy"),
    _param("Proxy CA Bundle Path", "unix_path_or_empty", table="ocp_proxy", required=False,
           description="Path to proxy CA certificate"),
    _param("Proxy Enabled", "yes_no", table="ocp_proxy", required=False,
           description="Whether proxy is configured for this cluster"),

    # ── ocp_platform_baremetal (12 params) ──
    _param("API VIP", "ipv4_or_ipv6", table="ocp_platform_baremetal", required=True,
           when="ipi_bm",
           description="Virtual IP for Kubernetes API (platform.baremetal.apiVIP)"),
    _param("Ingress VIP", "ipv4_or_ipv6", table="ocp_platform_baremetal", required=True,
           when="ipi_bm",
           description="Virtual IP for Ingress / *.apps (platform.baremetal.ingressVIP)"),
    _param("Provisioning Network", "enum_provisioning_network", table="ocp_platform_baremetal", required=True,
           when="ipi_bm",
           description="Provisioning network mode: Managed or Disabled"),
    _param("Provisioning Network CIDR", "cidr", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="CIDR for provisioning subnet (when Managed)"),
    _param("Provisioning MAC Address", "mac", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="MAC of NIC connected to provisioning network"),
    _param("Provisioning Network Interface", "iface", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="NIC name connected to provisioning network"),
    _param("Provisioning DHCP Range", "free_text", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="IP range for provisioning DHCP (e.g. 172.22.0.10,172.22.0.254)"),
    _param("Cluster Provisioning IP", "ipv4_or_ipv6", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="IP within cluster where provisioning services run"),
    _param("Bootstrap OS Image URL", "http_url", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="URL for bootstrap RHCOS image"),
    _param("Cluster OS Image URL", "http_url", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="URL for cluster RHCOS image"),
    _param("External Bridge", "iface", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="External network bridge name"),
    _param("Libvirt URI", "free_text", table="ocp_platform_baremetal", required=False,
           when="ipi_bm",
           description="Libvirt connection URI for virtual BM provisioning"),

    # ── ocp_agent_config (10 params) ──
    _param("Rendezvous IP", "ipv4_or_ipv6", table="ocp_agent_config", required=True,
           when="abi",
           description="IP of the rendezvous host (runs assisted-service during bootstrap)"),
    _param("Boot Artifacts Base URL", "http_url", table="ocp_agent_config", required=False,
           when="abi",
           description="URL of PXE asset server (for iPXE script generation)"),
    _param("Additional NTP Sources", "ntp_list", table="ocp_agent_config", required=False,
           when="abi",
           description="Comma-separated NTP sources to add to all cluster hosts"),
    _param("Agent Additional Trust Bundle Path", "unix_path_or_empty", table="ocp_agent_config", required=False,
           when="abi_dc",
           description="Path to CA bundle for mirror registry used by agent"),
    _param("Agent HTTP Proxy", "http_url", table="ocp_agent_config", required=False,
           when="abi",
           description="HTTP proxy for agent-based installer discovery"),
    _param("Agent HTTPS Proxy", "https_url", table="ocp_agent_config", required=False,
           when="abi",
           description="HTTPS proxy for agent-based installer discovery"),
    _param("Agent No Proxy", "free_text", table="ocp_agent_config", required=False,
           when="abi",
           description="Proxy exclusions for agent-based installer"),
    _param("Control Plane Agent Count", "integer", table="ocp_agent_config", required=False,
           when="abi",
           description="Number of control plane agents expected (auto-detected if omitted)"),
    _param("Worker Agent Count", "integer", table="ocp_agent_config", required=False,
           when="abi",
           description="Number of worker agents expected (auto-detected if omitted)"),
    _param("Bootstrap In Place", "yes_no", table="ocp_agent_config", required=False,
           when="sno",
           description="Enable bootstrap-in-place for SNO installations"),

    # ── ocp_disconnected (14 params) ──
    _param("Mirror Registry URL", "registry_host", table="ocp_disconnected", required=True,
           when="disconnected",
           description="Local mirror registry URL (host:port)"),
    _param("Mirror Registry CA Path", "unix_path", table="ocp_disconnected", required=True,
           when="disconnected",
           description="Path to mirror registry CA certificate file"),
    _param("Image Content Source - Source 1", "image_ref", table="ocp_disconnected", required=True,
           when="disconnected",
           description="Source registry for OCP release images (e.g. quay.io/openshift-release-dev/ocp-release)"),
    _param("Image Content Source - Mirror 1", "registry_host", table="ocp_disconnected", required=True,
           when="disconnected",
           description="Mirror location for source 1"),
    _param("Image Content Source - Source 2", "image_ref", table="ocp_disconnected", required=False,
           when="disconnected",
           description="Source registry for OCP art-dev images"),
    _param("Image Content Source - Mirror 2", "registry_host", table="ocp_disconnected", required=False,
           when="disconnected",
           description="Mirror location for source 2"),
    _param("IDMS Name", "dns_label", table="ocp_disconnected", required=False,
           when="disconnected",
           description="ImageDigestMirrorSet name (OCP 4.17+, replaces ICSP)"),
    _param("ITMS Name", "dns_label", table="ocp_disconnected", required=False,
           when="disconnected",
           description="ImageTagMirrorSet name"),
    _param("CatalogSource Name", "dns_label", table="ocp_disconnected", required=False,
           when="disconnected",
           description="CatalogSource name for disconnected operator hub"),
    _param("CatalogSource Image", "image_ref", table="ocp_disconnected", required=False,
           when="disconnected",
           description="CatalogSource index image in mirror registry"),
    _param("Disable Default CatalogSources", "yes_no", table="ocp_disconnected", required=False,
           when="disconnected",
           description="Disable default OperatorHub catalog sources"),
    _param("OC Mirror Workspace", "unix_path_or_empty", table="ocp_disconnected", required=False,
           when="disconnected",
           description="oc-mirror workspace directory path"),
    _param("Operator Index Image", "image_ref", table="ocp_disconnected", required=False,
           when="disconnected",
           description="Operator index image to mirror (e.g. registry.redhat.io/redhat/redhat-operator-index:v4.17)"),
    _param("Registry Credentials Path", "unix_path_or_empty", table="ocp_disconnected", required=False,
           when="disconnected",
           description="Path to registry auth credentials for mirror"),

    # ── ocp_mirror_registry (8 params) ──
    _param("Quay Hostname", "host_or_ip", table="ocp_mirror_registry", required=True,
           when="disconnected",
           description="FQDN of the Quay mirror-registry host"),
    _param("Quay Root Directory", "unix_path", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Root directory for Quay data (default: /opt/quay)"),
    _param("Quay Version", "free_text", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Quay mirror-registry version (e.g. v3.12.10)"),
    _param("Quay Init Password", "secret_text", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Initial admin password for mirror-registry (path reference preferred)"),
    _param("Quay TLS Cert Path", "unix_path_or_empty", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Path to TLS certificate for Quay mirror-registry"),
    _param("Quay TLS Key Path", "unix_path_or_empty", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Path to TLS private key for Quay mirror-registry"),
    _param("Quay Storage Backend", "free_text", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Storage backend type (local filesystem, NFS, etc.)"),
    _param("Quay Storage Path", "unix_path_or_empty", table="ocp_mirror_registry", required=False,
           when="disconnected",
           description="Path to storage directory for Quay data"),

    # ── ocp_bastion (9 params) ──
    _param("Bastion Hostname", "host_or_ip", table="ocp_bastion", required=False,
           description="FQDN of the bastion/helper host"),
    _param("Bastion IP", "ipv4", table="ocp_bastion", required=False,
           description="IP address of the bastion host"),
    _param("Bastion SSH User", "username", table="ocp_bastion", required=False,
           description="SSH username for bastion access (default: root)"),
    _param("Bastion OS", "free_text", table="ocp_bastion", required=False,
           description="Operating system (e.g. RHEL 9.4)"),
    _param("Bastion RHEL Version", "free_text", table="ocp_bastion", required=False,
           description="RHEL version installed on bastion"),
    _param("Bastion Disk Layout", "free_text", table="ocp_bastion", required=False,
           description="Disk/LVM layout description"),
    _param("Registry Mirror Enabled", "yes_no", table="ocp_bastion", required=False,
           description="Whether bastion hosts the mirror registry"),
    _param("DHCP TFTP Server", "yes_no", table="ocp_bastion", required=False,
           when="upi_bm",
           description="Whether bastion serves DHCP/TFTP for PXE boot"),
    _param("Bastion NTP Server", "host_or_ip", table="ocp_bastion", required=False,
           description="NTP server address for bastion host"),
    _param("Bastion Interface", "free_text", table="ocp_bastion", required=False,
           description="Network interface on bastion for VIP assignment (default: enp1s0)"),
    _param("ISO HTTP Port", "port", table="ocp_bastion", required=False,
           description="Port for temporary HTTP server to serve agent ISO to nodes (default: 8089)"),

    # ── ocp_load_balancer (8 params) ──
    _param("Load Balancer Type", "enum_lb_type", table="ocp_load_balancer", required=True,
           when="platform_none",
           description="LB type: HAProxy, MetalLB, F5, external"),
    _param("API Server Port", "port", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Kubernetes API port (default: 6443)"),
    _param("Machine Config Server Port", "port", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Machine config server port (default: 22623)"),
    _param("Ingress HTTPS Port", "port", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Ingress HTTPS port (default: 443)"),
    _param("Ingress HTTP Port", "port", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Ingress HTTP port (default: 80)"),
    _param("LB Backend Servers", "free_text", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Comma-separated backend server list (hostname:port)"),
    _param("LB Config Path", "unix_path_or_empty", table="ocp_load_balancer", required=False,
           when="platform_none",
           description="Path to load balancer config file (e.g. /etc/haproxy/haproxy.cfg)"),
    _param("API VIP (platform none)", "ipv4_or_ipv6", table="ocp_load_balancer", required=True,
           when="platform_none",
           description="Virtual IP for Kubernetes API when platform=none"),

    # ── ocp_certificates (6 params) ──
    _param("API Certificate Path", "unix_path_or_empty", table="ocp_certificates", required=False,
           description="Path to custom API server certificate"),
    _param("Ingress Wildcard Cert Path", "unix_path_or_empty", table="ocp_certificates", required=False,
           description="Path to wildcard certificate for *.apps.<cluster>.<domain>"),
    _param("CA Bundle Path", "unix_path_or_empty", table="ocp_certificates", required=False,
           description="Path to CA bundle for custom certificates"),
    _param("Lets Encrypt Enabled", "yes_no", table="ocp_certificates", required=False,
           description="Use Let's Encrypt for automatic certificate management"),
    _param("Custom CA Enabled", "yes_no", table="ocp_certificates", required=False,
           description="Whether a custom CA is used for cluster certificates"),
    _param("Certificate Validity Days", "integer", table="ocp_certificates", required=False,
           description="Certificate validity period in days"),

    # ── ocp_storage (8 params) ──
    _param("Default Storage Class", "free_text", table="ocp_storage", required=False,
           description="Default StorageClass name for the cluster"),
    _param("CSI Driver", "enum_storage_class_driver", table="ocp_storage", required=False,
           description="CSI storage driver: NFS, ODF, LSO, Trident, etc."),
    _param("NFS Server", "host_or_ip", table="ocp_storage", required=False,
           description="NFS server hostname or IP for NFS-based storage"),
    _param("NFS Path", "unix_path_or_empty", table="ocp_storage", required=False,
           description="NFS export path"),
    _param("LSO Enabled", "yes_no", table="ocp_storage", required=False,
           description="Enable Local Storage Operator"),
    _param("LSO Device Paths", "free_text", table="ocp_storage", required=False,
           description="Comma-separated device paths for LSO (e.g. /dev/vda,/dev/vdb)"),
    _param("ODF Enabled", "yes_no", table="ocp_storage", required=False,
           description="Enable OpenShift Data Foundation"),
    _param("ODF Storage Class", "free_text", table="ocp_storage", required=False,
           description="ODF StorageClass name"),

    # ── ocp_day2_operators (12 params) ──
    _param("NMState Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install Kubernetes NMState Operator for host network management"),
    _param("MetalLB Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install MetalLB Operator for bare-metal load balancing"),
    _param("SR-IOV Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install SR-IOV Network Operator for hardware-accelerated networking"),
    _param("Multus Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Enable Multus CNI for secondary network interfaces"),
    _param("LSO Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install Local Storage Operator"),
    _param("ODF Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install OpenShift Data Foundation Operator"),
    _param("Cert Manager Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install cert-manager Operator"),
    _param("Cluster Logging Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install Cluster Logging Operator (EFK/Loki)"),
    _param("Monitoring Stack Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Enable monitoring stack customization"),
    _param("GitOps Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install OpenShift GitOps Operator (ArgoCD)"),
    _param("MCE Operator Enabled", "yes_no", table="ocp_day2_operators", required=False,
           description="Install multicluster engine for Kubernetes Operator"),
    _param("Operator Install Plan Approval", "enum_install_plan_approval", table="ocp_day2_operators", required=False,
           description="Default install plan approval mode for all operators"),

    # ── ocp_ingress (6 params) ──
    _param("Ingress Controller Replicas", "integer", table="ocp_ingress", required=False,
           description="Number of Ingress Controller replicas"),
    _param("Ingress Default Certificate Path", "unix_path_or_empty", table="ocp_ingress", required=False,
           description="Path to default Ingress Controller certificate"),
    _param("Wildcard Policy", "enum_wildcard_policy", table="ocp_ingress", required=False,
           description="Wildcard policy: WildcardsAllowed or WildcardsDisallowed"),
    _param("Route Admission Policy", "free_text", table="ocp_ingress", required=False,
           description="Route admission policy configuration"),
    _param("Endpoint Publishing Strategy", "enum_endpoint_publishing", table="ocp_ingress", required=False,
           description="Ingress endpoint publishing: LoadBalancerService, HostNetwork, etc."),
    _param("Ingress Node Selector", "free_text", table="ocp_ingress", required=False,
           description="Node selector for Ingress Controller pods"),
]


# ---------------------------------------------------------------------------
# Row table schemas (identical to standalone)
# ---------------------------------------------------------------------------

OCP_BMC_HOST_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Hostname", "dns_label", required=True, description="Host FQDN or short name"),
    _field("Role", "enum_host_role", required=True, description="Host role: master or worker"),
    _field("BMC Address", "bmc_address", required=True, when="ipi_bm", description="BMC/Redfish address URI"),
    _field("BMC Username", "username", required=True, when="ipi_bm", description="BMC login username"),
    _field("BMC Password Reference", "free_text", required=True, when="ipi_bm", description="Reference to BMC password (vault path or env var — never plaintext)"),
    _field("Boot MAC Address", "mac", required=False, description="MAC address of boot NIC — auto-discovered via Redfish when reachable, or fill manually"),
    _field("Boot Mode", "enum_boot_mode", required=False, description="Boot mode: UEFI, legacy, UEFISecureBoot"),
    _field("Root Device Hint", "free_text", required=False, description="Root device hint (deviceName: /dev/sda, or wwn, serialNumber, etc.)"),
    _field("Root Device Name", "device_path", required=False, description="Device path for OS installation (e.g. /dev/sda)"),
    _field("Disable Certificate Verification", "yes_no", required=False, when="ipi_bm", description="Disable TLS certificate verification for BMC (self-signed certs)"),
    _field("Network Config", "free_text", required=False, description="Per-host NMState network config reference"),
    _field("CPU Count", "integer", required=False, description="Number of vCPUs (for capacity planning)"),
    _field("Memory GB", "integer", required=False, description="RAM in GB (for capacity planning)"),
    _field("Disk Size GB", "integer", required=False, description="Primary disk size in GB (for capacity planning)"),
]

OCP_NMSTATE_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Hostname", "dns_label", required=True, description="Hostname this interface config applies to"),
    _field("Interface Name", "iface", required=True, description="Network interface name (e.g. eno1, bond0, bond0.300)"),
    _field("Type", "enum_iface_type", required=True, description="Interface type: ethernet, bond, vlan, bridge"),
    _field("State", "enum_iface_state", required=True, description="Interface state: up, down, absent"),
    _field("IPv4 Address", "ipv4_or_ipv6", required=False, description="Static IP address for this interface"),
    _field("Prefix Length", "integer", required=False, description="Subnet prefix length (e.g. 23, 24)"),
    _field("Gateway", "ipv4_or_ipv6", required=False, description="Default gateway for this interface"),
    _field("VLAN ID", "vlan", required=False, when="vlan", description="VLAN ID (when type=vlan)"),
    _field("Bond Mode", "enum_bond_mode", required=False, when="bond", description="Bond mode (e.g. active-backup, 802.3ad)"),
    _field("Bond Members", "free_text", required=False, when="bond", description="Comma-separated bond member interface names"),
    _field("DNS Servers", "free_text", required=False, description="Comma-separated DNS server IPs"),
    _field("MTU", "mtu", required=False, description="Interface MTU"),
]

OCP_COMPUTE_NODE_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Hostname", "dns_label", required=True, description="Node hostname"),
    _field("Role", "enum_host_role", required=True, description="Node role: master or worker"),
    _field("CPU Count", "integer", required=False, description="Number of CPU cores"),
    _field("Memory GB", "integer", required=False, description="RAM in GB"),
    _field("Disk Count", "integer", required=False, description="Number of disks"),
    _field("Management IP", "ipv4", required=False, description="Management network IP"),
    _field("BMC Address", "bmc_address", required=False, description="BMC/IPMI/Redfish address"),
    _field("Boot MAC", "mac", required=False, description="Boot NIC MAC address"),
    _field("NIC1 MAC", "mac", required=False, description="Primary NIC MAC address"),
    _field("NIC2 MAC", "mac", required=False, description="Secondary NIC MAC address"),
    _field("IPMI Username", "username", required=False, description="IPMI/BMC username"),
    _field("Install Disk", "device_path", required=False, description="Disk device for OS installation"),
    _field("Labels", "free_text", required=False, description="Kubernetes node labels (key=value,key=value)"),
    _field("Disk Size GB", "integer", required=False, description="Primary disk size in GB"),
]

OCP_DNS_RECORD_FIELD_SCHEMA: list[dict[str, Any]] = [
    _field("Record Type", "enum_dns_record_type", required=True, description="DNS record type: A, AAAA, CNAME, PTR, SRV"),
    _field("Hostname", "free_text", required=True, description="DNS record name (e.g. api.ocp4.example.com)"),
    _field("IP or Target", "free_text", required=True, description="IP address or CNAME target"),
    _field("TTL", "integer", required=False, description="Time to live in seconds"),
    _field("Zone", "dns_domain", required=False, description="DNS zone (e.g. example.com or 168.192.in-addr.arpa)"),
    _field("Purpose", "enum_dns_purpose", required=True, description="Record purpose: api, api-int, apps-wildcard, master, worker, etcd, bootstrap"),
    _field("Cluster Name", "cluster_name", required=False, description="Cluster name for record construction"),
    _field("Notes", "free_text", required=False, description="Additional notes or comments"),
]


# ---------------------------------------------------------------------------
# Table manifest
# ---------------------------------------------------------------------------

OCP_CIQ_TABLES = (
    "ocp_cluster_details",
    "ocp_access",
    "ocp_networking",
    "ocp_proxy",
    "ocp_platform_baremetal",
    "ocp_agent_config",
    "ocp_disconnected",
    "ocp_mirror_registry",
    "ocp_bastion",
    "ocp_load_balancer",
    "ocp_certificates",
    "ocp_storage",
    "ocp_day2_operators",
    "ocp_ingress",
)

OCP_ROW_TABLES = (
    "ocp_bmc_hosts",
    "ocp_nmstate_interfaces",
    "ocp_compute_nodes",
    "ocp_dns_records",
)


def get_table_params(table_name: str) -> list[dict[str, Any]]:
    return [p for p in OCP_PARAMETER_SCHEMA if p["table"] == table_name]


def get_table_count() -> int:
    return len(OCP_CIQ_TABLES) + len(OCP_ROW_TABLES)


def get_param_count() -> int:
    return len(OCP_PARAMETER_SCHEMA) + sum(
        len(s) for s in [OCP_BMC_HOST_FIELD_SCHEMA, OCP_NMSTATE_FIELD_SCHEMA,
                         OCP_COMPUTE_NODE_FIELD_SCHEMA, OCP_DNS_RECORD_FIELD_SCHEMA]
    )


def get_validation_schema() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "types": CIQ_TYPES,
        "parameters": OCP_PARAMETER_SCHEMA,
        "bmc_host_fields": OCP_BMC_HOST_FIELD_SCHEMA,
        "nmstate_fields": OCP_NMSTATE_FIELD_SCHEMA,
        "compute_node_fields": OCP_COMPUTE_NODE_FIELD_SCHEMA,
        "dns_record_fields": OCP_DNS_RECORD_FIELD_SCHEMA,
        "tables": OCP_CIQ_TABLES,
        "row_tables": OCP_ROW_TABLES,
        "rules": {
            "install_methods": ["ABI", "IPI-BM", "UPI-BM", "ABI-DC", "SNO"],
            "platforms": ["baremetal", "vsphere", "none", "external"],
            "disconnected_modes": ["disconnected"],
            "abi_methods": ["ABI", "ABI-DC"],
            "ipi_methods": ["IPI-BM"],
            "upi_methods": ["UPI-BM"],
            "sno_methods": ["SNO"],
            "min_control_plane_ha": 3,
            "min_control_plane_sno": 1,
            "min_workers_ha": 2,
            "bmc_hosts_min_count_abi": 1,
            "nmstate_min_count_abi": 1,
            "dns_records_min_count": 3,
        },
    }


if __name__ == "__main__":
    schema = get_validation_schema()
    print(f"OCP CIQ Schema v{SCHEMA_VERSION}")
    print(f"  Tables: {get_table_count()} ({len(OCP_CIQ_TABLES)} parameter + {len(OCP_ROW_TABLES)} row)")
    print(f"  Parameters: {get_param_count()}")
    print(f"  CIQ Types: {len(CIQ_TYPES)}")
    print(f"  Install methods: {', '.join(schema['rules']['install_methods'])}")
