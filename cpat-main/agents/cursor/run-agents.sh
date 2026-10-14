#!/usr/bin/env bash
# ============================================================
# SprintWeave Agent Pipeline — Cursor SDK (Build & Run)
# ============================================================
#
# Usage:
#   ./run-agents.sh build                           # Build container image
#   ./run-agents.sh run                             # Full RHOSO delivery pipeline
#   ./run-agents.sh run --pipeline rda              # RHOSO DA only
#   ./run-agents.sh run --pipeline ocp-delivery     # Full OCP delivery pipeline
#   ./run-agents.sh run --pipeline full-delivery    # RHOSO + OCP (14 stages)
#   ./run-agents.sh run --stage RDE-1               # Single stage
#   ./run-agents.sh local                           # Run locally (no container)
#   ./run-agents.sh local --pipeline oda            # Run locally, OCP DA only
#
# Environment:
#   CURSOR_API_KEY   (required) — Cursor API key
#   CPAT_AGENT_MODEL (optional) — Model override (default: composer-2.5)
# ============================================================

set -euo pipefail

IMAGE_NAME="cpat-agents-cursor"
IMAGE_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CPAT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

red()   { printf "\033[0;31m%s\033[0m\n" "$*"; }
green() { printf "\033[0;32m%s\033[0m\n" "$*"; }
blue()  { printf "\033[0;34m%s\033[0m\n" "$*"; }

check_api_key() {
    if [ -z "${CURSOR_API_KEY:-}" ]; then
        red "ERROR: CURSOR_API_KEY is not set."
        echo "  Get your key at: https://cursor.com/dashboard/integrations"
        echo "  export CURSOR_API_KEY=\"cursor_...\""
        exit 1
    fi
}

cmd_build() {
    blue "Building ${IMAGE_NAME}:${IMAGE_TAG}..."
    docker build -f "${SCRIPT_DIR}/Dockerfile" -t "${IMAGE_NAME}:${IMAGE_TAG}" "${CPAT_ROOT}"
    green "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
}

cmd_run() {
    check_api_key
    blue "Running CPAT Agent Pipeline (Cursor SDK, containerized)..."
    docker run --rm \
        -e CURSOR_API_KEY="${CURSOR_API_KEY}" \
        -e CPAT_AGENT_MODEL="${CPAT_AGENT_MODEL:-composer-2.5}" \
        -v "${CPAT_ROOT}/output:/workspace/output" \
        "${IMAGE_NAME}:${IMAGE_TAG}" \
        "$@"
    green "Pipeline complete. Output at: ${CPAT_ROOT}/output/"
}

cmd_local() {
    check_api_key
    blue "Running CPAT Agent Pipeline (Cursor SDK, local)..."
    if ! python3 -c "import cursor_sdk" 2>/dev/null; then
        blue "Installing cursor-sdk..."
        pip install cursor-sdk
    fi
    cd "${CPAT_ROOT}"
    python3 "${SCRIPT_DIR}/run_pipeline.py" "$@"
}

case "${1:-help}" in
    build)  shift; cmd_build "$@" ;;
    run)    shift; cmd_run "$@" ;;
    local)  shift; cmd_local "$@" ;;
    help|--help|-h) head -17 "$0" | tail -14 ;;
    *)      red "Unknown command: $1"; echo "Usage: $0 {build|run|local|help}"; exit 1 ;;
esac
