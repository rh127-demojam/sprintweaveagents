#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) CPAT
# GNU General Public License v3.0+

"""Ansible module: return OCP CIQ validation schema (types + regexp patterns)."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ocp_ciq_schema import get_validation_schema


def main():
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)
    module.exit_json(changed=False, schema=get_validation_schema())


if __name__ == "__main__":
    main()
