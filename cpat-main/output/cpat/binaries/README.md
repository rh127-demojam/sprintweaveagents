# OCP Binaries

**Default behaviour:** The Dockerfile automatically downloads OCP binaries from
`mirror.openshift.com` during `./bringup.sh build`. No action needed here.

**Override version:**
```bash
podman build --build-arg OCP_VERSION=4.19 -t cpat:25.10.1 .
```

## All supported binaries

Place files directly in this `binaries/` directory (do NOT extract tarballs):

| File to place in `binaries/` | Purpose | Required? |
|-------------------------------|---------|-----------|
| `openshift-install-linux.tar.gz` | OCP installer (agent ISO, bootstrap, install-complete) | Optional — auto-downloaded if build machine has internet |
| `openshift-client-linux.tar.gz` | OpenShift CLI (`oc`, `kubectl`) | Optional — auto-downloaded if build machine has internet |
| `mirror-registry-amd64.tar.gz` | Install local Quay mirror registry on bastion | **Required** — copied to bastion at runtime |
| `oc-mirror-rhel9-linux-amd64.tar.gz` | Mirror OCP images to disconnected registry | **Required** — copied to bastion at runtime |

Download from [console.redhat.com/openshift/downloads](https://console.redhat.com/openshift/downloads):
- **OpenShift for x86_64 → Install** → `openshift-install-linux.tar.gz`, `openshift-client-linux.tar.gz`
- **OpenShift mirror plugin** → `oc-mirror-rhel9-linux-amd64.tar.gz` (or `.tar`)
- **Mirror Registry for Red Hat OpenShift** → `mirror-registry-amd64.tar.gz`

### Example directory listing

```
binaries/
  ├── openshift-install-linux.tar.gz       (~395 MB, optional)
  ├── openshift-client-linux.tar.gz        (~60 MB, optional)
  ├── mirror-registry-amd64.tar.gz         (~707 MB, required)
  ├── oc-mirror-rhel9-linux-amd64.tar.gz   (~300 MB, required)
  └── README.md
```

## How it works

1. **Build time** (`podman build`):
   - OCP binaries: extracts `openshift-install`, `oc`, `kubectl` from tarballs → `/usr/local/bin/`
   - If tarballs not present, downloads from mirror.openshift.com
   - Mirror artifacts: moved as-is to `/app/mirror-artifacts/` inside the container

2. **Deploy time** (Ansible playbooks):
   - Playbooks check bastion for the tarballs at `~/ocp-install/`
   - If not found on bastion, copies from `/app/mirror-artifacts/` in the CPAT container
   - Extracts and installs binaries on the bastion

## Verification

After container start:
```bash
./bringup.sh shell
openshift-install version
oc version --client
ls -lh /app/mirror-artifacts/
```
