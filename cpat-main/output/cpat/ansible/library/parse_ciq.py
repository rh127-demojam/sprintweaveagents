#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) CPAT
# GNU General Public License v3.0+

"""Ansible module: parse_ciq — parse CIQ XLSX (RHOSO + OCP) and return cluster registration data."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ciq_parser import CiqParseError, parse_ciq_xlsx


def _entry_to_dict(entry) -> dict:
    return {
        "cluster_name": entry.cluster_name,
        "cluster_type": entry.cluster_type,
        "cluster_type_label": entry.cluster_type_label,
        "type_raw_value": entry.type_raw_value,
        "parameters": entry.parameters,
        "row_tables": entry.row_tables,
        # Backward-compatible keys
        "nodes": entry.nodes,
        "networks": entry.networks,
        "bmc_hosts": entry.bmc_hosts,
        "nmstate_interfaces": entry.nmstate_interfaces,
        "compute_nodes": entry.compute_nodes,
        "dns_records": entry.dns_records,
        "source_table": entry.source_table,
        "source_sheet": entry.source_sheet,
    }


def main():
    module = AnsibleModule(
        argument_spec={
            "path": {"required": True, "type": "str"},
            "cluster_type": {"required": False, "type": "str", "default": ""},
        },
        supports_check_mode=True,
    )

    path = module.params["path"]
    cluster_type_filter = (module.params.get("cluster_type") or "").strip().lower()

    try:
        batch = parse_ciq_xlsx(path)
    except CiqParseError as exc:
        module.fail_json(msg=str(exc))

    if cluster_type_filter:
        entry = batch.get_by_type(cluster_type_filter)
        if not entry:
            module.fail_json(
                msg=(
                    f"No registration found for cluster type '{cluster_type_filter}' "
                    f"in CIQ file."
                )
            )
        module.exit_json(changed=False, **_entry_to_dict(entry))

    module.exit_json(
        changed=False,
        clusters=[_entry_to_dict(c) for c in batch.clusters],
        table_parameters=batch.table_parameters,
        cluster_count=len(batch.clusters),
    )


if __name__ == "__main__":
    main()
