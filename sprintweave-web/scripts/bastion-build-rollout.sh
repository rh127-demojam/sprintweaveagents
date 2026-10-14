#!/usr/bin/env bash
# Build SprintWeave image on bastion, push to Quay, rollout OpenShift.
#
# Prerequisites:
#   - Logged into OpenShift: oc whoami
#   - Logged into Quay:      podman login quay.io
#   - Tarball extracted under BUILD_DIR (default ~/sprintweave-build)
#
# Usage on bastion:
#   mkdir -p ~/sprintweave-build
#   tar -xzf ~/sprintweave-bastion.tgz -C ~/sprintweave-build
#   bash ~/sprintweave-build/sprintweave-web/scripts/bastion-build-rollout.sh
#
# Env overrides:
#   IMAGE=quay.io/rh_global_services_auto/sprintweave-rhoso:latest
#   BASE_IMAGE=quay.io/rh_global_services_auto/sprintweave-docling-base:latest
#   NAMESPACE=sprintweave
#   PIPELINES=lab-requirements,rhoso
#   SKIP_PUSH=1          # build only
#   SKIP_ROLLOUT=1       # build+push only
#   EXTRACT_TGZ=1        # also extract ~/sprintweave-bastion.tgz first
#
set -euo pipefail

BUILD_DIR="${BUILD_DIR:-${HOME}/sprintweave-build}"
TGZ="${TGZ:-${HOME}/sprintweave-bastion.tgz}"
IMAGE="${IMAGE:-quay.io/rh_global_services_auto/sprintweave-rhoso:latest}"
BASE_IMAGE="${BASE_IMAGE:-quay.io/rh_global_services_auto/sprintweave-docling-base:latest}"
NAMESPACE="${NAMESPACE:-sprintweave}"
PIPELINES="${PIPELINES:-lab-requirements,rhoso}"
SKIP_PUSH="${SKIP_PUSH:-0}"
SKIP_ROLLOUT="${SKIP_ROLLOUT:-0}"
EXTRACT_TGZ="${EXTRACT_TGZ:-0}"

echo "==> Config"
echo "    BUILD_DIR=${BUILD_DIR}"
echo "    IMAGE=${IMAGE}"
echo "    BASE_IMAGE=${BASE_IMAGE}"
echo "    NAMESPACE=${NAMESPACE}"
echo "    PIPELINES=${PIPELINES}"

if [[ "${EXTRACT_TGZ}" == "1" ]]; then
  if [[ ! -f "${TGZ}" ]]; then
    echo "ERROR: tarball not found: ${TGZ}" >&2
    exit 1
  fi
  echo "==> Extracting ${TGZ} → ${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
  tar -xzf "${TGZ}" -C "${BUILD_DIR}"
fi

if [[ ! -f "${BUILD_DIR}/sprintweave-web/Dockerfile.bundle" ]]; then
  echo "ERROR: ${BUILD_DIR}/sprintweave-web/Dockerfile.bundle missing." >&2
  echo "       Extract tarball first:" >&2
  echo "         mkdir -p ${BUILD_DIR} && tar -xzf ${TGZ} -C ${BUILD_DIR}" >&2
  exit 1
fi

# Resolve agent tree (nested cpat-main/cpat-main vs flat cpat-main)
AGENTS_SRC="cpat-main"
if [[ -d "${BUILD_DIR}/cpat-main/cpat-main/.cursor/rules" ]]; then
  AGENTS_SRC="cpat-main/cpat-main"
  echo "    AGENTS_SRC=${AGENTS_SRC} (nested layout)"
elif [[ -d "${BUILD_DIR}/cpat-main/.cursor/rules" ]]; then
  AGENTS_SRC="cpat-main"
  echo "    AGENTS_SRC=${AGENTS_SRC}"
elif [[ -d "${BUILD_DIR}/sprintweave-agents/.cursor/rules" ]]; then
  AGENTS_SRC="sprintweave-agents"
  echo "    AGENTS_SRC=${AGENTS_SRC}"
else
  echo "WARN: no agent rules found under cpat-main — build may lack RHOSO agents"
fi

echo "==> OpenShift login check"
if ! oc whoami >/dev/null 2>&1; then
  echo "ERROR: not logged in to OpenShift. Run: oc login ..." >&2
  exit 1
fi
echo "    user=$(oc whoami)  project=$(oc project -q 2>/dev/null || echo '?')"

echo "==> podman build"
cd "${BUILD_DIR}"
podman build \
  -f sprintweave-web/Dockerfile.bundle \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  --build-arg "AGENTS_SRC=${AGENTS_SRC}" \
  --build-arg "PIPELINES=${PIPELINES}" \
  -t "${IMAGE}" \
  .

if [[ "${SKIP_PUSH}" != "1" ]]; then
  echo "==> podman push ${IMAGE}"
  podman push "${IMAGE}"
else
  echo "==> SKIP_PUSH=1 — not pushing"
fi

if [[ "${SKIP_ROLLOUT}" != "1" ]]; then
  echo "==> oc rollout restart (api + ui) in ${NAMESPACE}"
  oc project "${NAMESPACE}" >/dev/null

  # --- CPAT Install from UI: SA + RBAC (idempotent, runs every deploy) ---
  RBAC_YAML="${BUILD_DIR}/sprintweave-web/deploy/openshift/cpat-deploy-rbac.yaml"
  if [[ -f "${RBAC_YAML}" ]]; then
    echo "==> applying CPAT deploy RBAC (SA + Role + RoleBinding)"
    oc apply -f "${RBAC_YAML}" -n "${NAMESPACE}"
    # Ensure the API deployment uses the SA (no-op if already set)
    oc set serviceaccount deployment/sprintweave-api sprintweave-api -n "${NAMESPACE}" 2>/dev/null || true
  else
    echo "==> WARN: ${RBAC_YAML} not found — CPAT Install from UI may not work"
  fi

  oc rollout restart deployment/sprintweave-api deployment/sprintweave-ui -n "${NAMESPACE}"
  echo "==> waiting for API rollout"
  oc rollout status deployment/sprintweave-api -n "${NAMESPACE}" --timeout=300s
  oc rollout status deployment/sprintweave-ui -n "${NAMESPACE}" --timeout=180s || true

  echo "==> verify new code in API pod"
  oc exec deployment/sprintweave-api -n "${NAMESPACE}" -- \
    grep -E "resume_job_from_stage|/resume|skip_and_continue|/skip|_stamp_log" \
    /app/sprintweave-web/api/main.py /app/sprintweave-web/api/worker.py || true

  echo "==> verify oc in API pod"
  oc exec deployment/sprintweave-api -n "${NAMESPACE}" -- \
    oc version --client 2>/dev/null || echo "    WARN: oc not in API image — rebuild with Dockerfile.bundle"

  echo "==> env (single-shot / steps)"
  oc exec deployment/sprintweave-api -n "${NAMESPACE}" -- \
    printenv | grep -E "SINGLE_SHOT|MAX_STEPS|TEXT_MAX|TIMEOUT|RETRIES|COMPACT" || true

  echo "==> pods"
  oc get pods -n "${NAMESPACE}" -l 'app in (sprintweave-api,sprintweave-ui)'
else
  echo "==> SKIP_ROLLOUT=1 — not restarting deployments"
fi

echo "==> DONE"
echo "    Image: ${IMAGE}"
echo "    Namespace: ${NAMESPACE}"
