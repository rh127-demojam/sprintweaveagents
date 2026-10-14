#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CPAT container lifecycle script (Podman)
#
# Usage:
#   ./bringup.sh build     Build the container image
#   ./bringup.sh start     Start container (build if image missing)
#   ./bringup.sh stop      Stop and remove container
#   ./bringup.sh restart   Stop, rebuild, and start
#   ./bringup.sh logs      Tail container logs
#   ./bringup.sh shell     Open a shell inside the running container
#   ./bringup.sh export    Save container image as .tar for transfer
#   ./bringup.sh           (default: start)
#
# Environment variables:
#   CPAT_VERSION       App/image version YY.M.W (default: 25.10.1)
#   CPAT_IMAGE         Image tag (default: cpat:$CPAT_VERSION)
#   CPAT_CONTAINER     Container name (default: cpat)
#   CPAT_PORT          Host port (default: 8080)
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="cpat"
# Dynamic YY.M.W versioning: 2-digit year, month (no leading zero), week of month
_YY=$(date +%y)
_M=$(date +%-m)
_DAY=$(date +%-d)
_W=$(( (_DAY - 1) / 7 + 1 ))
VERSION="${CPAT_VERSION:-${_YY}.${_M}.${_W}}"
CONTAINER_NAME="${CPAT_CONTAINER:-cpat}"
HOST_PORT="${CPAT_PORT:-8080}"
FULL_IMAGE="${CPAT_IMAGE:-${IMAGE_NAME}:${VERSION}}"

if ! command -v podman >/dev/null 2>&1; then
  echo "Error: podman is not installed or not in PATH." >&2
  echo "Install Podman, then re-run this script." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

stop_container() {
  if podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Stopping container '$CONTAINER_NAME'..."
    podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    podman rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "Container removed."
  else
    echo "No existing container named '$CONTAINER_NAME'."
  fi
}

cleanup_build_images() {
  echo "Cleaning up intermediate images (keeping: $FULL_IMAGE)..."
  podman image prune -f >/dev/null 2>&1 || true

  local keep="${FULL_IMAGE#localhost/}"
  local ref short
  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    [ "$ref" = "<none>:<none>" ] && continue
    short="${ref#localhost/}"
    if [ "$short" = "$keep" ] || [ "$ref" = "$FULL_IMAGE" ]; then
      continue
    fi
    echo "  Removing $ref"
    podman rmi -f "$ref" >/dev/null 2>&1 || true
  done < <(podman images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -E "(^|/)${IMAGE_NAME}:" || true)

  podman image prune -f >/dev/null 2>&1 || true
  echo "Image cleanup complete."
}

build_image() {
  echo "Building image '$FULL_IMAGE' (VERSION=$VERSION) with podman..."
  MSYS2_ARG_CONV_EXCL='*' MSYS_NO_PATHCONV=1 podman build \
    --build-arg CACHEBUST="$(date +%s)" \
    --build-arg "CPAT_VERSION=$VERSION" \
    -t "$FULL_IMAGE" .
  echo "Image build complete."
  cleanup_build_images
}

start_container() {
  if podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Container '$CONTAINER_NAME' already exists. Use 'restart' or 'stop' first." >&2
    exit 1
  fi

  if ! podman image exists "$FULL_IMAGE" 2>/dev/null; then
    build_image
  fi

  echo "Starting container '$CONTAINER_NAME' on port ${HOST_PORT}..."
  MSYS2_ARG_CONV_EXCL='*' MSYS_NO_PATHCONV=1 podman run -d \
    --name "$CONTAINER_NAME" \
    -p "${HOST_PORT}:80" \
    -e CPAT_DATA_DIR=/cpat-data \
    -e "CPAT_VERSION=$VERSION" \
    "$FULL_IMAGE"

  echo
  echo "CPAT is running (podman)."
  echo "  URL:       http://localhost:${HOST_PORT}"
  echo "  Login:     admin / admin"
  echo "  Version:   v${VERSION} (YY.M.W) — RHOSO 18.0 + OCP 4.17-4.20"
  echo "  Container: $CONTAINER_NAME"
  echo "  Image:     $FULL_IMAGE"
  echo
  echo "View logs:   ./bringup.sh logs"
  echo "Shell:       ./bringup.sh shell"
  echo "Stop:        ./bringup.sh stop"
  echo
  echo "If the UI looks outdated after an upgrade, hard-refresh the browser"
  echo "(Ctrl+Shift+R or Cmd+Shift+R). Sidebar should show Version ${VERSION}."
}

show_logs() {
  if ! podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Container '$CONTAINER_NAME' is not running." >&2
    exit 1
  fi
  podman logs -f "$CONTAINER_NAME"
}

open_shell() {
  if ! podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Container '$CONTAINER_NAME' is not running." >&2
    exit 1
  fi
  podman exec -it "$CONTAINER_NAME" /bin/bash
}

export_image() {
  if ! podman image exists "$FULL_IMAGE" 2>/dev/null; then
    echo "Image '$FULL_IMAGE' not found. Building first..."
    build_image
  fi

  local tar_file="${IMAGE_NAME}-${VERSION}.tar"
  echo "Exporting image '$FULL_IMAGE' to ${tar_file}..."
  podman save "$FULL_IMAGE" -o "$tar_file"
  local size
  size=$(du -h "$tar_file" | cut -f1)
  echo
  echo "Export complete."
  echo "  File:   $(pwd)/${tar_file}"
  echo "  Size:   ${size}"
  echo "  Image:  $FULL_IMAGE"
  echo
  echo "Transfer to bastion:"
  echo "  scp -P 2222 ${tar_file} cloud-user@<gateway-ip>:~/"
  echo
  echo "Load on bastion:"
  echo "  podman load -i ${tar_file}"
}

# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

case "${1:-start}" in
  build)
    build_image
    ;;
  start|"")
    start_container
    ;;
  stop)
    stop_container
    ;;
  restart)
    stop_container
    build_image
    start_container
    ;;
  logs)
    show_logs
    ;;
  shell)
    open_shell
    ;;
  export)
    export_image
    ;;
  -h|--help|help)
    cat <<EOF
CPAT container lifecycle script (Podman)

Usage:
  ./bringup.sh build      Build the container image
  ./bringup.sh start      Start container (build image if missing)
  ./bringup.sh stop       Stop and remove container
  ./bringup.sh restart    Stop, rebuild, and start
  ./bringup.sh logs       Tail container logs
  ./bringup.sh shell      Open a shell in running container
  ./bringup.sh export     Save image as .tar for transfer to bastion

Requires: podman

Environment variables:
  CPAT_VERSION         Version tag YY.M.W (default: 25.10.1)
  CPAT_IMAGE           Full image tag (default: cpat:\$VERSION)
  CPAT_CONTAINER       Container name (default: cpat)
  CPAT_PORT            Host port (default: 8080)

Runtime data (DB, uploads, secrets, logs, artifacts) is stored in the
'cpat-data' Podman volume, mounted at /cpat-data inside the container.
EOF
    ;;
  *)
    echo "Unknown command: $1" >&2
    echo "Run './bringup.sh help' for usage." >&2
    exit 1
    ;;
esac
