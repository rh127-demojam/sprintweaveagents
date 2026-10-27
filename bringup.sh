#!/usr/bin/env bash
# ==========================================================================
# SprintWeave Platform — Bastion Node Build & Deploy
# ==========================================================================
#
# Run from the CFP_NEW repo root on a bastion node that has:
#   - podman (or docker)
#   - oc (logged in to the target OpenShift cluster)
#   - Network access to Quay / internal registry
#
# Quick start:
#   export REGISTRY=quay.io/YOUR_ORG           # or internal registry
#   export LLM_API_KEY=sk-...                   # your API key
#   ./bringup.sh deploy                         # full build + push + deploy
#
# ==========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Configurable ────────────────────────────────────────────────
REGISTRY="${REGISTRY:-quay.io/rh_global_services_auto}"
NAMESPACE="${SW_NAMESPACE:-sprintweave}"
IMAGE_BASE="${SW_IMAGE_BASE:-sprintweave-rhoso}"
DOCLING_IMAGE="${REGISTRY}/sprintweave-docling-base:latest"

_YY=$(date +%y)
_M=$(date +%-m 2>/dev/null || date +%m | sed 's/^0//')
_DAY=$(date +%-d 2>/dev/null || date +%d | sed 's/^0//')
_W=$(( (_DAY - 1) / 7 + 1 ))
VERSION="${SW_VERSION:-${_YY}.${_M}.${_W}}"
FULL_IMAGE="${REGISTRY}/${IMAGE_BASE}:${VERSION}"
LATEST_IMAGE="${REGISTRY}/${IMAGE_BASE}:latest"

# ── Runtime detection ───────────────────────────────────────────
if command -v podman >/dev/null 2>&1; then
  RT=podman
elif command -v docker >/dev/null 2>&1; then
  RT=docker
else
  echo "ERROR: neither podman nor docker found on PATH" >&2
  exit 1
fi

# ── Helper: coloured status ─────────────────────────────────────
_info()  { echo -e "\033[1;34m▸ $*\033[0m"; }
_ok()    { echo -e "\033[1;32m✓ $*\033[0m"; }
_warn()  { echo -e "\033[1;33m⚠ $*\033[0m"; }
_err()   { echo -e "\033[1;31m✗ $*\033[0m" >&2; }

# ================================================================
# build_base — Docling heavy base (run once, or when deps change)
# ================================================================
build_base() {
  _info "Building Docling base image (this takes 10–30 min first time)…"
  $RT build \
    -f sprintweave-web/Dockerfile.docling-base \
    -t "$DOCLING_IMAGE" \
    .
  _ok "Docling base ready: $DOCLING_IMAGE"
}

# ================================================================
# build — Thin app image (sprintweave-web + cpat-main)
# ================================================================
build() {
  if ! $RT image exists "$DOCLING_IMAGE" 2>/dev/null; then
    _warn "Docling base not found locally — building it first…"
    build_base
  fi

  _info "Building app image: $FULL_IMAGE"
  _info "  Engine:  sprintweave-web/"
  _info "  Agents:  cpat-main/"

  $RT build \
    -f Dockerfile \
    --build-arg "BASE_IMAGE=$DOCLING_IMAGE" \
    --build-arg "PIPELINES=rhoso,rhoso-delivery,ocp,ocp-delivery" \
    -t "$FULL_IMAGE" \
    -t "$LATEST_IMAGE" \
    .

  _ok "Image ready: $FULL_IMAGE"
}

# ================================================================
# push — Push to Quay / registry
# ================================================================
push() {
  if ! $RT image exists "$FULL_IMAGE" 2>/dev/null; then
    _err "Image $FULL_IMAGE not found. Run './bringup.sh build' first."
    exit 1
  fi
  _info "Pushing $FULL_IMAGE …"
  $RT push "$FULL_IMAGE"
  _info "Pushing $LATEST_IMAGE …"
  $RT push "$LATEST_IMAGE"
  _ok "Pushed to $REGISTRY"
}

# ================================================================
# push_base — Push Docling base to Quay (rare)
# ================================================================
push_base() {
  _info "Pushing Docling base: $DOCLING_IMAGE"
  $RT push "$DOCLING_IMAGE"
  _ok "Docling base pushed"
}

# ================================================================
# ocp_setup — Create namespace, secret, RBAC on OpenShift
# ================================================================
ocp_setup() {
  if ! command -v oc >/dev/null 2>&1; then
    _err "oc not found on PATH. Install the OpenShift client first."
    exit 1
  fi

  _info "Setting up OpenShift project: $NAMESPACE"

  # Create project (ignore if exists)
  oc new-project "$NAMESPACE" 2>/dev/null \
    || oc project "$NAMESPACE"

  # LLM API key secret
  if [ -z "${LLM_API_KEY:-}" ]; then
    _warn "LLM_API_KEY not set — skipping secret creation."
    _warn "Create it manually:  oc create secret generic sprintweave-llm --from-literal=LLM_API_KEY=sk-..."
  else
    oc create secret generic sprintweave-llm \
      --from-literal="LLM_API_KEY=${LLM_API_KEY}" \
      -n "$NAMESPACE" --dry-run=client -o yaml | oc apply -f -
    _ok "Secret sprintweave-llm created/updated"
  fi

  # Quay pull secret (if provided)
  if [ -n "${QUAY_PULL_SECRET:-}" ] && [ -f "$QUAY_PULL_SECRET" ]; then
    oc create secret docker-registry quay-pull \
      --from-file=.dockerconfigjson="$QUAY_PULL_SECRET" \
      -n "$NAMESPACE" --dry-run=client -o yaml | oc apply -f -
    oc secrets link default quay-pull --for=pull -n "$NAMESPACE" 2>/dev/null || true
    _ok "Quay pull secret linked"
  fi
}

# ================================================================
# ocp_deploy — Apply manifests and roll out
# ================================================================
ocp_deploy() {
  if ! command -v oc >/dev/null 2>&1; then
    _err "oc not found on PATH."
    exit 1
  fi

  local manifest="sprintweave-web/deploy/openshift/quay-deploy-rhoso.yaml"
  if [ ! -f "$manifest" ]; then
    _err "Manifest not found: $manifest"
    exit 1
  fi

  _info "Applying manifests to $NAMESPACE …"
  # Substitute the image reference in-flight
  sed "s|quay.io/YOUR_ORG/sprintweave-rhoso:latest|${LATEST_IMAGE}|g" \
    "$manifest" | oc apply -n "$NAMESPACE" -f -

  _info "Rolling out API …"
  oc rollout restart deployment/sprintweave-api -n "$NAMESPACE" 2>/dev/null || true
  oc rollout status deployment/sprintweave-api -n "$NAMESPACE" --timeout=300s

  _info "Rolling out UI …"
  oc rollout restart deployment/sprintweave-ui -n "$NAMESPACE" 2>/dev/null || true
  oc rollout status deployment/sprintweave-ui -n "$NAMESPACE" --timeout=120s

  local route_host
  route_host=$(oc get route sprintweave-ui -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

  echo
  _ok "SprintWeave deployed on OpenShift!"
  echo
  echo "  Namespace:  $NAMESPACE"
  echo "  Image:      $LATEST_IMAGE"
  echo "  Version:    $VERSION"
  if [ -n "$route_host" ]; then
    echo "  URL:        https://$route_host"
  fi
  echo
  echo "  API logs:   oc logs -f deployment/sprintweave-api -n $NAMESPACE"
  echo "  UI logs:    oc logs -f deployment/sprintweave-ui  -n $NAMESPACE"
  echo "  Pods:       oc get pods -n $NAMESPACE"
  echo
}

# ================================================================
# deploy — Full pipeline: build → push → setup → deploy
# ================================================================
deploy() {
  build
  push
  ocp_setup
  ocp_deploy
}

# ================================================================
# status — Show current deploy state
# ================================================================
status() {
  if ! command -v oc >/dev/null 2>&1; then
    _err "oc not found"
    exit 1
  fi
  echo
  _info "Pods in $NAMESPACE:"
  oc get pods -n "$NAMESPACE" -o wide 2>/dev/null || _warn "cannot list pods"
  echo
  _info "Routes:"
  oc get routes -n "$NAMESPACE" 2>/dev/null || _warn "no routes"
  echo
  _info "Deployments:"
  oc get deployments -n "$NAMESPACE" 2>/dev/null || true
  echo
  _info "PVC:"
  oc get pvc -n "$NAMESPACE" 2>/dev/null || true
  echo
}

# ================================================================
# logs — Tail API logs
# ================================================================
logs() {
  oc logs -f deployment/sprintweave-api -n "$NAMESPACE"
}

# ================================================================
# export — Save image as tarball for air-gapped transfer
# ================================================================
export_image() {
  if ! $RT image exists "$FULL_IMAGE" 2>/dev/null; then
    _err "Image $FULL_IMAGE not found. Build it first."
    exit 1
  fi
  local tar_file="${IMAGE_BASE}-${VERSION}.tar"
  _info "Saving $FULL_IMAGE → $tar_file"
  $RT save "$FULL_IMAGE" -o "$tar_file"
  local size
  size=$(du -h "$tar_file" | cut -f1)
  _ok "Export complete: $tar_file ($size)"
  echo
  echo "Transfer to bastion:  scp $tar_file cloud-user@<bastion>:~/"
  echo "Load on bastion:      podman load -i $tar_file"
}

# ================================================================
# Command dispatch
# ================================================================
case "${1:-help}" in
  build)       build ;;
  build-base)  build_base ;;
  push)        push ;;
  push-base)   push_base ;;
  setup)       ocp_setup ;;
  apply)       ocp_deploy ;;
  deploy)      deploy ;;
  status)      status ;;
  logs)        logs ;;
  export)      export_image ;;
  -h|--help|help)
    cat <<EOF

SprintWeave Platform — Bastion Bringup
=======================================

Usage: ./bringup.sh <command>

Build commands:
  build-base     Build Docling base image (slow, run once)
  build          Build thin app image (sprintweave-web + cpat-main)
  push-base      Push Docling base image to registry
  push           Push app image to registry
  export         Save app image as .tar for air-gapped transfer

OpenShift commands:
  setup          Create namespace, LLM secret, pull secret
  apply          Apply manifests + rollout (image must be in registry)
  deploy         Full pipeline: build → push → setup → apply
  status         Show pods, routes, deployments, PVCs
  logs           Tail API pod logs

Environment:
  REGISTRY         Container registry (default: quay.io/rh_global_services_auto)
  SW_NAMESPACE     OpenShift namespace (default: sprintweave)
  SW_VERSION       Image version tag (default: YY.M.W auto)
  SW_IMAGE_BASE    Image name (default: sprintweave-rhoso)
  LLM_API_KEY      LLM API key (used by 'setup' to create secret)
  QUAY_PULL_SECRET Path to .dockerconfigjson for Quay pull (optional)

Examples:
  # First time — full setup:
  export REGISTRY=quay.io/myorg LLM_API_KEY=sk-abc123
  ./bringup.sh deploy

  # Code change — rebuild + redeploy:
  ./bringup.sh build && ./bringup.sh push && ./bringup.sh apply

  # Air-gapped — build locally, transfer tar:
  ./bringup.sh build
  ./bringup.sh export
  scp sprintweave-rhoso-*.tar cloud-user@bastion:~/
  # On bastion: podman load -i sprintweave-rhoso-*.tar

EOF
    ;;
  *) _err "Unknown command: $1"; echo "Run './bringup.sh help' for usage."; exit 1 ;;
esac
