#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CPAT container lifecycle script — Golden template, NEVER LLM-generated.
# Works with both Podman and Docker. Port 8080 by default.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="cpat"
_YY=$(date +%y)
_M=$(date +%-m 2>/dev/null || date +%m | sed 's/^0//')
_DAY=$(date +%-d 2>/dev/null || date +%d | sed 's/^0//')
_W=$(( (_DAY - 1) / 7 + 1 ))
VERSION="${CPAT_VERSION:-${_YY}.${_M}.${_W}}"
CONTAINER_NAME="${CPAT_CONTAINER:-cpat}"
HOST_PORT="${CPAT_PORT:-8080}"
FULL_IMAGE="${CPAT_IMAGE:-${IMAGE_NAME}:${VERSION}}"
NETWORK_MODE="${CPAT_NETWORK:-}"

if command -v podman >/dev/null 2>&1; then
  RUNTIME=podman
elif command -v docker >/dev/null 2>&1; then
  RUNTIME=docker
else
  echo "Error: neither podman nor docker found." >&2
  exit 1
fi

stop_container() {
  if "$RUNTIME" container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Stopping container '$CONTAINER_NAME'..."
    "$RUNTIME" stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    "$RUNTIME" rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "Container removed."
  else
    echo "No existing container named '$CONTAINER_NAME'."
  fi
}

build_image() {
  echo "Building image '$FULL_IMAGE' (VERSION=$VERSION)..."
  MSYS2_ARG_CONV_EXCL='*' MSYS_NO_PATHCONV=1 "$RUNTIME" build \
    --build-arg CACHEBUST="$(date +%s)" \
    --build-arg "CPAT_VERSION=$VERSION" \
    -t "$FULL_IMAGE" .
  echo "Image build complete."
}

start_container() {
  if "$RUNTIME" container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "Container '$CONTAINER_NAME' already exists. Use 'restart' or 'stop' first." >&2
    exit 1
  fi
  if ! "$RUNTIME" image exists "$FULL_IMAGE" 2>/dev/null; then
    build_image
  fi

  echo "Starting container '$CONTAINER_NAME' on port ${HOST_PORT}..."
  RUN_ARGS=(run -d --name "$CONTAINER_NAME")
  if [[ "${NETWORK_MODE}" == "host" ]]; then
    RUN_ARGS+=(--network host -e "CPAT_LISTEN_PORT=${HOST_PORT}")
  else
    RUN_ARGS+=(-p "${HOST_PORT}:8080")
  fi
  RUN_ARGS+=(-e CPAT_DATA_DIR=/cpat-data -e "CPAT_VERSION=$VERSION")
  MSYS2_ARG_CONV_EXCL='*' MSYS_NO_PATHCONV=1 "$RUNTIME" "${RUN_ARGS[@]}" "$FULL_IMAGE"

  echo
  echo "CPAT is running ($RUNTIME)."
  echo "  URL:       http://localhost:${HOST_PORT}"
  echo "  Login:     admin / admin"
  echo "  Version:   v${VERSION}"
  echo "  Container: $CONTAINER_NAME"
  echo "  Image:     $FULL_IMAGE"
  echo
  echo "View logs:   $RUNTIME logs -f $CONTAINER_NAME"
  echo "Shell:       $RUNTIME exec -it $CONTAINER_NAME /bin/bash"
  echo "Stop:        ./bringup.sh stop"
}

export_image() {
  if ! "$RUNTIME" image exists "$FULL_IMAGE" 2>/dev/null; then
    build_image
  fi
  local tar_file="${IMAGE_NAME}-${VERSION}.tar"
  echo "Exporting image '$FULL_IMAGE' to ${tar_file}..."
  "$RUNTIME" save "$FULL_IMAGE" -o "$tar_file"
  echo "Export complete: $(pwd)/${tar_file}"
}

case "${1:-start}" in
  build)       build_image ;;
  start|"")    start_container ;;
  stop)        stop_container ;;
  restart)     stop_container; build_image; start_container ;;
  logs)        "$RUNTIME" logs -f "$CONTAINER_NAME" ;;
  shell)       "$RUNTIME" exec -it "$CONTAINER_NAME" /bin/bash ;;
  export)      export_image ;;
  -h|--help|help)
    cat <<EOF
CPAT container lifecycle script

Usage:
  ./bringup.sh build      Build container image
  ./bringup.sh start      Start container (build if missing)
  ./bringup.sh stop       Stop and remove container
  ./bringup.sh restart    Stop, rebuild, and start
  ./bringup.sh logs       Tail container logs
  ./bringup.sh shell      Open shell in running container
  ./bringup.sh export     Save image as .tar for transfer

Environment:
  CPAT_VERSION     Version tag YY.M.W (default: auto)
  CPAT_IMAGE       Full image tag (default: cpat:\$VERSION)
  CPAT_CONTAINER   Container name (default: cpat)
  CPAT_PORT        Host port (default: 8080)
  CPAT_NETWORK     Set to 'host' for bastion host-network mode
EOF
    ;;
  *) echo "Unknown command: $1" >&2; exit 1 ;;
esac
