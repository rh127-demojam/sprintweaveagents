# Two Quay repositories
#
#   quay.io/YOUR_ORG/sprintweave        ← workspace sprintweave-agents
#   quay.io/YOUR_ORG/sprintweave-rhoso  ← ZIP (cpat-main), still mounted as /.../sprintweave-agents

Both images include **sprintweave-web**. Agent files in the container are always at
`/opt/app-root/src/sprintweave-agents`.

## Build (from CFP_NEW)

```bash
cd /path/to/CFP_NEW
ls sprintweave-web sprintweave-agents cpat-main
ORG=YOUR_ORG

# 0) Docling base (once) — see Dockerfile.docling-base
podman build -f sprintweave-web/Dockerfile.docling-base \
  -t quay.io/${ORG}/sprintweave-docling-base:latest .
podman push quay.io/${ORG}/sprintweave-docling-base:latest

# 1) Full agents + all pipelines (thin layer on base)
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=sprintweave-agents \
  --build-arg PIPELINES=all \
  -t quay.io/${ORG}/sprintweave:latest .

# 2) RHOSO / CPAT ZIP + Lab Requirements + RHOSO pipelines
podman build -f sprintweave-web/Dockerfile.bundle \
  --build-arg BASE_IMAGE=quay.io/${ORG}/sprintweave-docling-base:latest \
  --build-arg AGENTS_SRC=cpat-main \
  --build-arg PIPELINES=lab-requirements,rhoso \
  -t quay.io/${ORG}/sprintweave-rhoso:latest .
```

`PIPELINES` is optional (`all` = every pipeline in `ui/pipelines.py`).  
Ids: `standard`, `lab-requirements`, `rhoso`, `nrho`, `nrho-delivery`, `governance`.

You can also override at deploy time without rebuild via ConfigMap/env:
`SPRINTWEAVE_PIPELINES=lab-requirements,rhoso` (set on **both** UI and API pods).

Need **cpat-main** on disk for image 2. Keep **sprintweave-agents** for image 1.

## Push

```bash
podman login quay.io
podman push quay.io/YOUR_ORG/sprintweave:latest
podman push quay.io/YOUR_ORG/sprintweave-rhoso:latest
```

Create both repositories on Quay if they do not exist.

## Deploy

Replace `YOUR_ORG` in the YAML, then:

```bash
# Full SprintWeave
oc new-project sprintweave
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='YOUR_KEY' -n sprintweave
oc apply -f sprintweave-web/deploy/openshift/quay-deploy.yaml

# RHOSO/CPAT ZIP variant (separate project so both can run)
oc new-project sprintweave-rhoso
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='YOUR_KEY' -n sprintweave-rhoso
oc apply -f sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml
```

Private Quay: pull secret in **each** project (`oc secrets link default quay-pull --for=pull`).

Use **sprintweave** for Standard/NRHO. Use **sprintweave-rhoso** for RHOSO/CPAT (`output/cpat` in that image). Lab Requirements works on both (RHOSO DA).

RHOSO DA/RDE now use a **Cursor-like tool-calling agent** (Docling + openpyxl + file tools). See [CURSOR-LIKE-RHOSO.md](CURSOR-LIKE-RHOSO.md) for build size, ConfigMap knobs, and smoke tests.
