# -*- coding: utf-8 -*-
"""RHOSO CIQ schema — backend re-export shim.

Attempts to import from the Ansible module_utils canonical copy first.
Falls back to the CIQ generators copy, then to an inline v1.4 schema.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

_SCHEMA_MODULE = None


def _try_import(module_path: str):
    """Attempt to import a schema module by dotted path."""
    try:
        return importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError):
        return None


def _resolve_schema_module():
    """Resolve the CIQ schema module from known locations."""
    global _SCHEMA_MODULE
    if _SCHEMA_MODULE is not None:
        return _SCHEMA_MODULE

    import os

    # 1. Try Ansible module_utils (container: /app/ansible/module_utils)
    ansible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "ansible", "module_utils"),
        "/app/ansible/module_utils",
    ]
    for p in ansible_paths:
        abs_p = os.path.abspath(p)
        if os.path.isdir(abs_p) and abs_p not in sys.path:
            sys.path.insert(0, abs_p)

    mod = _try_import("rhoso_ciq_schema")
    if mod and hasattr(mod, "SCHEMA_VERSION") and mod.SCHEMA_VERSION >= "1.4":
        _SCHEMA_MODULE = mod
        return mod

    # 2. Try ciq-generators copy (development layout)
    gen_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "ciq-generators")
    )
    if os.path.isdir(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
        mod = _try_import("rhoso_ciq_schema")
        if mod and hasattr(mod, "SCHEMA_VERSION") and mod.SCHEMA_VERSION >= "1.4":
            _SCHEMA_MODULE = mod
            return mod

    return None


_mod = _resolve_schema_module()

if _mod is not None:
    # Re-export everything from the resolved module
    CIQ_TYPES = _mod.CIQ_TYPES
    RHOSO_PARAMETER_SCHEMA = _mod.RHOSO_PARAMETER_SCHEMA
    RHOSO_NETWORK_FIELD_SCHEMA = _mod.RHOSO_NETWORK_FIELD_SCHEMA
    RHOSO_NODE_FIELD_SCHEMA = _mod.RHOSO_NODE_FIELD_SCHEMA
    SCHEMA_VERSION = _mod.SCHEMA_VERSION
    get_validation_schema = _mod.get_validation_schema
else:
    # Inline fallback — schema v1.4 constants
    SCHEMA_VERSION = "1.4"

    CIQ_TYPES: dict[str, dict[str, str]] = {
        "dns_label": {"pattern": r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$", "description": "DNS label"},
        "k8s_name": {"pattern": r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$", "description": "Kubernetes name"},
        "yes_no": {"pattern": r"(?i)^(yes|no|true|false|1|0)$", "description": "Boolean yes/no"},
        "free_text": {"pattern": r"^[\s\S]{0,2048}$", "description": "Free-form text"},
        "integer": {"pattern": r"^[0-9]+$", "description": "Non-negative integer"},
        "ipv4": {"pattern": r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", "description": "IPv4"},
    }

    RHOSO_PARAMETER_SCHEMA: list[dict[str, Any]] = []
    RHOSO_NETWORK_FIELD_SCHEMA: list[dict[str, Any]] = []
    RHOSO_NODE_FIELD_SCHEMA: list[dict[str, Any]] = []

    def get_validation_schema() -> dict[str, Any]:
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


# Schema v1.4 tables (18 total: 3 core + 15 supplemental)
RHOSO_CIQ_TABLES = (
    "rhoso_details",
    "rhoso_access",
    "rhoso_disconnected",
    "rhoso_storage",
    "rhoso_ceph_storage",
    "rhoso_trident_storage",
    "rhoso_lso_storage",
    "rhoso_control_plane",
    "rhoso_services",
    "rhoso_observability",
    "rhoso_pv_sizing",
    "rhoso_cinder_backend",
    "rhoso_neutron_config",
    "rhoso_edpm_network_config",
    "rhoso_data_plane",
    "rhoso_multipath",
    "rhoso_networks",
    "rhoso_data_plane_nodes",
)
