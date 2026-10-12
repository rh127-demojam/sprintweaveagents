# SprintWeave — New Cluster Setup Guide

**Purpose:** Step-by-step instructions to deploy SprintWeave on a fresh OpenShift cluster.  
**Audience:** Platform engineer, DevOps, or delivery lead setting up for the first time.  
**Time:** ~30 minutes (excluding image build if already on Quay).

Do **not** put API keys in Git, YAML files, ConfigMaps, or this document.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **OpenShift cluster** | 4.14+ (tested on 4.22). Single-node or multi-node. |
| **`oc` CLI** | Matching cluster version. Logged in with project-create permissions. |
| **Quay image** | `quay.io/rh_global_services_auto/sprintweave:latest` (public) or your own org/repo. |
| **LLM endpoint** | OpenAI-compatible URL (`/v1/chat/completions`) with a Bearer key. Examples: MaaS/LiteLLM, Azure OpenAI, vLLM, Ollama with OpenAI adapter. |
| **LLM API key** | Bearer token for the endpoint above. |
| **Bastion or terminal** | SSH to a jump host, or `oc` from your laptop. |
| **Browser** | To open the Streamlit Route after deploy. |

### Optional

| Item | When needed |
|------|-------------|
| **Quay pull secret** | Only if the image repo is private. |
| **Docling** | For PDF/DOCX parsing. Not in the current image (add later). |
| **OAuth / SSO** | To restrict Route access. Not required for a lab. |

---

## Architecture overview

```
Browser
   | HTTPS (OpenShift Route, TLS edge)
   v
sprintweave-ui  (Streamlit, port 8080)
   |  env: SPRINTWEAVE_API_URL=http://sprintweave-api:8000
   |  NO LLM key
   v
sprintweave-api (FastAPI + worker, port 8000)
   |  Secret: LLM_API_KEY
   |  ConfigMap: LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, …
   |  PVC: /data (uploads + outputs)
   |
   +--> POST {LLM_BASE_URL}/chat/completions
   +--> /data/jobs/<job-id>/input/     (uploaded files)
   +--> /data/jobs/<job-id>/output/    (generated markdown)
```

**One container image**, two Deployments:

| Deployment | Command | Port | Has LLM key? | Has PVC? |
|------------|---------|------|---------------|----------|
| `sprintweave-ui` | `streamlit run ui/app.py` | 8080 | No | No |
| `sprintweave-api` | `uvicorn api.main:app` | 8000 | Yes (Secret) | Yes |

**OpenShift objects created:**

| Object | Name |
|--------|------|
| Deployment | `sprintweave-ui`, `sprintweave-api` |
| Service | `sprintweave-ui` (8080), `sprintweave-api` (8000) |
| Route | `sprintweave-ui` (TLS edge) |
| PVC | `sprintweave-data` (2 Gi, RWO) |
| ConfigMap | `sprintweave-config` |
| Secret | `sprintweave-llm` |

---

## Step-by-step setup

### Step 1 — Log in and create project

```bash
oc login https://api.<cluster>:6443
# Enter username and password when prompted

oc new-project sprintweave
oc project sprintweave
```

If the project already exists: `oc project sprintweave`.

---

### Step 2 — Verify the cluster can reach the LLM

```bash
oc run curl-test --image=registry.access.redhat.com/ubi9/ubi-minimal \
  --rm -it --restart=Never -- \
  curl -sS -o /dev/null -w "%{http_code}\n" <LLM_BASE_URL>/models
```

Replace `<LLM_BASE_URL>` with your endpoint (e.g. `https://maas-rhdp.apps.maas.redhatworkshops.io/v1`).

- `200` or `401` = network works (401 means no key, which is expected).
- Timeout / DNS error = fix egress or proxy before continuing.

Do **not** pass the API key in this test.

---

### Step 3 — Create the LLM Secret

```bash
oc create secret generic sprintweave-llm \
  --from-literal=LLM_API_KEY='<your-key>' \
  -n sprintweave
```

Verify:

```bash
oc get secret sprintweave-llm
oc describe secret sprintweave-llm
```

You should see `LLM_API_KEY` in the data keys. Do **not** decode or print the value.

---

### Step 4 — (Private Quay only) Create pull secret

Skip this step if the Quay repo is **public**.

```bash
oc create secret docker-registry quay-pull \
  --docker-server=quay.io \
  --docker-username='<quay-user>' \
  --docker-password='<quay-token>' \
  --docker-email='unused@example.com' \
  -n sprintweave

oc secrets link default quay-pull --for=pull -n sprintweave
```

---

### Step 5 — Get the deploy YAML

Copy `quay-deploy.yaml` to the bastion (from the repo or a teammate).

Edit **two** lines — replace `YOUR_ORG` with the actual Quay path:

```yaml
# In the API Deployment:
image: quay.io/rh_global_services_auto/sprintweave:latest

# In the UI Deployment:
image: quay.io/rh_global_services_auto/sprintweave:latest
```

Also review the **ConfigMap** section in the YAML and set your LLM values:

```yaml
data:
  LLM_PROVIDER: "openai"
  LLM_BASE_URL: "<your-llm-endpoint>/v1"
  LLM_MODEL: "<model-id>"
  LLM_MAX_TOKENS: "1024"
  LLM_TIMEOUT: "180"
```

Common configurations:

| Provider | LLM_PROVIDER | LLM_BASE_URL | LLM_MODEL |
|----------|-------------|--------------|-----------|
| MaaS/LiteLLM | `openai` | `https://maas-rhdp.apps.maas.redhatworkshops.io/v1` | `claude-opus-4-6` or `llama-scout-17b` |
| Azure OpenAI | `openai` | `https://<resource>.openai.azure.com/openai/deployments/<dep>` | `gpt-4` |
| Anthropic direct | `anthropic` | `https://api.anthropic.com` | `claude-opus-4-6` |
| Ollama (in-cluster) | `openai` | `http://ollama:11434/v1` | `llama3` |

---

### Step 6 — Apply

```bash
oc apply -f quay-deploy.yaml
```

This creates: PVC, ConfigMap, Deployments, Services, Route.

---

### Step 7 — Wait for pods

```bash
oc get pods -w
```

Wait until both show **1/1 Running**:

```
sprintweave-api-xxxxx-yyyyy   1/1   Running   0   30s
sprintweave-ui-xxxxx-yyyyy    1/1   Running   0   25s
```

Press Ctrl+C to stop watching.

**Troubleshooting:**

| Pod status | Check | Common cause |
|------------|-------|--------------|
| `ImagePullBackOff` | `oc describe pod -l app=sprintweave-api \| tail -30` | Wrong image name, private Quay without pull secret |
| `CrashLoopBackOff` | `oc logs deploy/sprintweave-api --tail=30` | Missing Secret, wrong key name, Python error |
| `Pending` | `oc describe pod -l app=sprintweave-api` | PVC cannot bind, insufficient resources |
| `0/1 Running` long time | `oc describe pod -l app=sprintweave-api` | Health probe failing, slow start |

---

### Step 8 — Get the URL

```bash
oc get route sprintweave-ui -o jsonpath='https://{.spec.host}{"\n"}'
```

Open that URL in a browser.

---

### Step 9 — Verify

1. **Sidebar** shows **API connected** ✅ (not "Demo mode").
2. Go to **Home** → click **Lab Requirements** (1 stage, cheapest test).
3. Upload `lab-smoke.txt` (a small text file with a few lines about lab sizing).
4. Click **Run pipeline**.
5. Watch the **Job** page: stage should go ⏳ → ✅.
6. On success, download the markdown artifact.

If the job **fails** with `401 Unauthorized`:
- Wrong LLM key in Secret, or
- `LLM_PROVIDER` does not match the endpoint (e.g. `anthropic` key against a LiteLLM URL).

Check:

```bash
oc logs deploy/sprintweave-api --tail=30
oc get configmap sprintweave-config -o yaml
```

---

### Step 10 — Verify files on disk

```bash
oc rsh deploy/sprintweave-api
ls -R /data/jobs
cat /data/jobs/<job-id>/input/lab-smoke.txt
ls /data/jobs/<job-id>/output/
exit
```

---

### Step 11 — Verify agents are bundled

```bash
oc rsh deploy/sprintweave-api
ls /app/sprintweave-agents/.cursor/rules/ | head
ls /app/sprintweave-agents/context/templates/ | head
exit
```

---

## Post-setup operations

### Update the LLM model or endpoint

```bash
oc patch configmap sprintweave-config --type merge -p '{
  "data": {
    "LLM_MODEL": "new-model-id",
    "LLM_BASE_URL": "https://new-endpoint/v1"
  }
}'
oc rollout restart deployment/sprintweave-api
```

### Rotate the LLM key

```bash
oc delete secret sprintweave-llm
oc create secret generic sprintweave-llm \
  --from-literal=LLM_API_KEY='<new-key>' \
  -n sprintweave
oc rollout restart deployment/sprintweave-api
```

### Update the image (after a new build + push to Quay)

```bash
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui -n sprintweave
oc get pods -w
```

No `oc delete` or `oc apply` needed for image updates if the tag is `:latest`.

### View logs

```bash
oc logs -f deploy/sprintweave-api
oc logs -f deploy/sprintweave-ui
```

### Scale (if needed)

```bash
oc scale deployment/sprintweave-ui --replicas=2
```

Keep API at **1 replica** (PVC is RWO; job state is in-memory).

---

## Building the image (for maintainers)

Only needed if you modify `sprintweave-web/` or `sprintweave-agents/`.

### Prerequisites

- Docker or Podman on a machine that can reach Docker Hub and Quay.
- Both `sprintweave-web/` and `sprintweave-agents/` in the same parent directory (`CFP_NEW`).

### Build

```bash
cd /path/to/CFP_NEW

# Full agents (workspace):
docker build -f sprintweave-web/Dockerfile.bundle \
  --build-arg AGENTS_SRC=sprintweave-agents \
  -t quay.io/rh_global_services_auto/sprintweave:latest .

# RHOSO-only (ZIP/cpat-main):
docker build -f sprintweave-web/Dockerfile.bundle \
  --build-arg AGENTS_SRC=cpat-main \
  -t quay.io/rh_global_services_auto/sprintweave-rhoso:latest .
```

### Push

```bash
docker login quay.io
docker push quay.io/rh_global_services_auto/sprintweave:latest
```

### Corporate proxy issues

If `docker build` fails with TLS errors:
- Build on **WSL** (bypasses Windows corp proxy) or the **bastion** (inside Red Hat network).
- Use `--tls-verify=false` with Podman (lab only, not production).

---

## Known issues and constraints

| Issue | Workaround |
|-------|-----------|
| **`fsGroup: 0` rejected by SCC** | Do not set pod-level `fsGroup: 0`. Omit it or use the project's allocated GID. |
| **DeploymentConfig deprecated** | We use `Deployment` (apps/v1), not DeploymentConfig. |
| **PVC is RWO** | Only one API pod can mount it. Keep API replicas at 1. |
| **MaaS keys expire** (often 7 days) | Rotate Secret and restart API. |
| **PDF/DOCX uploaded but seen as binary** | Docling not installed yet. Use `.txt`/`.md` for now. |
| **Large agent rule files increase tokens** | `SPRINTWEAVE_AGENT_PROMPT_MAX` (env, default 24000 chars) truncates. |

---

## Files reference

| File | Purpose |
|------|---------|
| `sprintweave-web/Dockerfile.bundle` | Container image definition |
| `sprintweave-web/deploy/openshift/quay-deploy.yaml` | Full cluster manifests (Deployment, Service, Route, PVC, ConfigMap) |
| `sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml` | Same for RHOSO-only image in a separate project |
| `sprintweave-web/samples/lab-smoke.txt` | Tiny test file for smoke runs |
| `sprintweave-web/docs/TEAM-GUIDE.md` | Architecture + roadmap for the team |
| `sprintweave-web/docs/QUAY.md` | Image build + push instructions |

---

## Quick reference card

```bash
# Login
oc login https://api.<cluster>:6443

# Create project
oc new-project sprintweave

# Create LLM secret
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='…'

# Deploy
oc apply -f quay-deploy.yaml

# Check
oc get pods
oc get route sprintweave-ui

# Logs
oc logs -f deploy/sprintweave-api

# Files on disk
oc rsh deploy/sprintweave-api -- ls -R /data/jobs

# Rotate key
oc delete secret sprintweave-llm
oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY='…'
oc rollout restart deployment/sprintweave-api

# Update image
oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui
```
