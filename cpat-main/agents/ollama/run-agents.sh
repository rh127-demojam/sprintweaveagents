#!/usr/bin/env bash
# ============================================================
# SprintWeave Agent Pipeline — Ollama / Local GPU (Build & Run)
# ============================================================
#
# Usage:
#   ./run-agents.sh build                     # Build container image
#   ./run-agents.sh run                       # Full pipeline (container + GPU)
#   ./run-agents.sh run --pipeline rda        # RDA only
#   ./run-agents.sh local                     # Run locally (Ollama must be running)
#   ./run-agents.sh local --pipeline rda      # Run locally, RDA only
#   ./run-agents.sh local --model qwen2.5-coder:7b  # Different model
#
# No API key required. Ollama runs models locally on your GPU.
#
# Prerequisites:
#   1. Install Ollama: https://ollama.com/download
#   2. Pull a model: ollama pull qwen2.5-coder:14b
#   3. pip install openai pyyaml
# ============================================================

set -euo pipefail

IMAGE_NAME="cpat-agents-ollama"
IMAGE_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CPAT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

red()   { printf "\033[0;31m%s\033[0m\n" "$*"; }
green() { printf "\033[0;32m%s\033[0m\n" "$*"; }
blue()  { printf "\033[0;34m%s\033[0m\n" "$*"; }

cmd_build() {
    blue "Building ${IMAGE_NAME}:${IMAGE_TAG}..."
    docker build -f "${SCRIPT_DIR}/Dockerfile" -t "${IMAGE_NAME}:${IMAGE_TAG}" "${CPAT_ROOT}"
    green "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
}

cmd_run() {
    blue "Running CPAT Agent Pipeline (Ollama, containerized)..."
    docker run --rm --gpus all \
        -e CPAT_MODEL="${CPAT_MODEL:-qwen2.5-coder:14b}" \
        -v "${CPAT_ROOT}/output:/workspace/output" \
        "${IMAGE_NAME}:${IMAGE_TAG}" \
        "$@"
    green "Pipeline complete. Output at: ${CPAT_ROOT}/output/"
}

cmd_local() {
    blue "Running CPAT Agent Pipeline (Ollama, local)..."
    if ! python3 -c "import openai" 2>/dev/null; then
        blue "Installing dependencies..."
        pip install openai pyyaml
    fi
    cd "${CPAT_ROOT}"
    python3 "${SCRIPT_DIR}/run_pipeline.py" "$@"
}

case "${1:-help}" in
    build)  shift; cmd_build "$@" ;;
    run)    shift; cmd_run "$@" ;;
    local)  shift; cmd_local "$@" ;;
    help|--help|-h) head -20 "$0" | tail -17 ;;
    *)      red "Unknown command: $1"; echo "Usage: $0 {build|run|local|help}"; exit 1 ;;
esac
