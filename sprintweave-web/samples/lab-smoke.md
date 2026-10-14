# Lab note (SprintWeave smoke test)

Environment: compact OpenShift 4.22 workshop, single control-plane node.

Need:
- 3 worker-equivalent vCPUs for a small control plane
- 16 GiB RAM
- 100 GiB disk for OS + registry
- One VLAN for machine network (192.168.1.0/24)
- DNS for api and apps routes

Out of scope: production HA, disconnected install.
