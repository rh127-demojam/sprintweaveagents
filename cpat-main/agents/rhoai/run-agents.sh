#!/usr/bin/env bash
# ============================================================
# SprintWeave Agent Pipeline — Red Hat OpenShift AI (RHOAI)
# ============================================================
#
# Runs SprintWeave agents against a vLLM model server on RHOAI.
# Uses the same OpenAI-compatible pipeline runner as the Ollama
# runner, but targets a remote RHOAI/vLLM inference endpoint.
#
# Usage:
#   ./run-agents.sh run                                  # Full pipeline
#   ./run-agents.sh run --pipeline rda                   # RDA only
#   ./run-agents.sh run --model meta-llama/...           # Override model
#   ./run-agents.sh discover                             # Detect endpoint from oc
#   ./run-agents.sh test                                 # Test connection
#
# Environment:
#   RHOAI_API_BASE   (required) — vLLM route URL, e.g. https://granite-vllm-llama-serve.apps.cluster.example.com/v1
#   RHOAI_API_KEY    (optional) — Bearer token (defaults to `oc whoami -t`)
#   RHOAI_MODEL      (optional) — Model name (default: ibm-granite/granite-3.2-8b-instruct)
#
# Prerequisites:
#   1. RHOAI environment provisioned (e.g. Llama Stack on OpenShift from RHDP)
#   2. pip install openai pyyaml
#   3. oc CLI logged into the cluster (for auto-discovery)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CPAT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PIPELINE_RUNNER="${CPAT_ROOT}/agents/ollama/run_pipeline.py"

DEFAULT_MODEL="granite32-8b"

red()   { printf "\033[0;31m%s\033[0m\n" "$*" >&2; }
green() { printf "\033[0;32m%s\033[0m\n" "$*" >&2; }
blue()  { printf "\033[0;34m%s\033[0m\n" "$*" >&2; }
yellow(){ printf "\033[0;33m%s\033[0m\n" "$*" >&2; }

# Resolve python command — test it actually runs (Windows Store stubs report
# "Python was not found" and exit non-zero even though command -v succeeds).
PYTHON=""
for _py in python3 python py; do
    if command -v "$_py" &>/dev/null && "$_py" -c "import sys" &>/dev/null; then
        PYTHON="$_py"
        break
    fi
done

# ── Auto-discover vLLM route from OCP cluster ───────────────

discover_endpoint() {
    if [ -n "${RHOAI_API_BASE:-}" ]; then
        echo "${RHOAI_API_BASE}"
        return
    fi

    blue "Auto-discovering vLLM endpoint from OCP cluster..."

    if ! command -v oc &>/dev/null; then
        red "ERROR: 'oc' CLI not found. Set RHOAI_API_BASE manually or install oc."
        exit 1
    fi

    # KServe/RHOAI InferenceService routes land in istio-system;
    # also check the serving namespace and common RHOAI namespaces.
    local namespaces=("istio-system" "llama-serve" "llama-stack" "rhoai" "redhat-ods-applications" "knative-serving-ingress")
    local route=""

    for ns in "${namespaces[@]}"; do
        # List all route hosts, one per line, then filter for vLLM / model names.
        # Prefer routes whose *name* contains vllm/granite/model (most specific).
        route=$(oc get routes -n "$ns" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.host}{"\n"}{end}' 2>/dev/null \
            | grep -iE 'vllm|granite|model-server' \
            | grep -ivE 'predictor|istio-ingressgateway' \
            | head -1 | awk '{print $2}' || true)
        if [ -n "$route" ]; then
            break
        fi
    done

    if [ -z "$route" ]; then
        red "ERROR: Could not auto-discover vLLM route."
        echo "" >&2
        echo "  Manual steps:" >&2
        echo "    1. oc get routes -A | grep -iE 'vllm|granite|model'" >&2
        echo "    2. export RHOAI_API_BASE=https://<route-host>/v1" >&2
        echo "    3. Re-run this script" >&2
        exit 1
    fi

    local endpoint="https://${route}/v1"
    green "Discovered: ${endpoint}"
    echo "${endpoint}"
}

# ── Resolve API key ─────────────────────────────────────────

resolve_api_key() {
    if [ -n "${RHOAI_API_KEY:-}" ]; then
        echo "${RHOAI_API_KEY}"
        return
    fi

    # Try oc token
    if command -v oc &>/dev/null; then
        local token
        token=$(oc whoami -t 2>/dev/null || true)
        if [ -n "$token" ]; then
            echo "$token"
            return
        fi
    fi

    # vLLM often works without auth in cluster-internal setups
    echo "none"
}

# ── Commands ────────────────────────────────────────────────

cmd_discover() {
    local endpoint
    endpoint=$(discover_endpoint)
    echo ""
    green "vLLM Endpoint: ${endpoint}"
    echo ""
    echo "Set it permanently:"
    echo "  export RHOAI_API_BASE=\"${endpoint}\""
}

cmd_test() {
    local endpoint
    endpoint=$(discover_endpoint)
    local api_key
    api_key=$(resolve_api_key)
    local model="${RHOAI_MODEL:-${DEFAULT_MODEL}}"

    blue "Testing connection to RHOAI..."
    echo "  Endpoint: ${endpoint}"
    echo "  Model:    ${model}"
    echo ""

    # Test /v1/models
    blue "Listing available models..."
    local response
    if [ "$api_key" = "none" ]; then
        response=$(curl -sk "${endpoint}/models" 2>&1) || true
    else
        response=$(curl -sk -H "Authorization: Bearer ${api_key}" "${endpoint}/models" 2>&1) || true
    fi

    parse_models='import sys,json; data=json.load(sys.stdin); print("Available models:"); [print("  - " + m["id"]) for m in data["data"]]'
    if [ -n "$PYTHON" ] && echo "$response" | $PYTHON -c "$parse_models" 2>/dev/null; then
        green "Connection successful!"
    elif echo "$response" | grep -q '"object":"list"'; then
        green "Connection successful (raw model data in response)"
    else
        red "Could not reach ${endpoint}/models"
        echo "Response: ${response}"
        exit 1
    fi

    # Test a simple completion
    blue "Testing inference (simple completion)..."
    local test_payload='{"model":"'"${model}"'","messages":[{"role":"user","content":"Say hello in one word."}],"max_tokens":10}'
    local test_response
    if [ "$api_key" = "none" ]; then
        test_response=$(curl -sk -X POST "${endpoint}/chat/completions" -H "Content-Type: application/json" -d "$test_payload" 2>&1) || true
    else
        test_response=$(curl -sk -X POST "${endpoint}/chat/completions" -H "Content-Type: application/json" -H "Authorization: Bearer ${api_key}" -d "$test_payload" 2>&1) || true
    fi

    parse_reply='import sys,json; r=json.load(sys.stdin); print("  Model responded: " + r["choices"][0]["message"]["content"])'
    if [ -n "$PYTHON" ] && echo "$test_response" | $PYTHON -c "$parse_reply" 2>/dev/null; then
        green "Inference working! Ready for SprintWeave pipeline."
    elif echo "$test_response" | grep -q '"choices"'; then
        green "Inference working! (response received)"
    else
        yellow "WARNING: Inference test returned unexpected response."
        echo "  Response: ${test_response:0:500}"
    fi
}

cmd_run() {
    local endpoint
    endpoint=$(discover_endpoint)
    local api_key
    api_key=$(resolve_api_key)
    local model="${RHOAI_MODEL:-${DEFAULT_MODEL}}"

    blue "Running SprintWeave Agent Pipeline (RHOAI)..."
    echo "  Endpoint: ${endpoint}"
    echo "  Model:    ${model}"
    echo ""

    # Check Python deps
    if [ -z "$PYTHON" ]; then
        red "ERROR: Python not found. Install python3 or python."
        exit 1
    fi
    if ! $PYTHON -c "import openai" 2>/dev/null; then
        blue "Installing dependencies..."
        pip install openai pyyaml
    fi

    cd "${CPAT_ROOT}"
    PYTHONIOENCODING=utf-8 $PYTHON "${PIPELINE_RUNNER}" \
        --api-base "${endpoint}" \
        --api-key "${api_key}" \
        --model "${model}" \
        "$@"
}

# ── Entrypoint ──────────────────────────────────────────────

case "${1:-help}" in
    run)       shift; cmd_run "$@" ;;
    discover)  cmd_discover ;;
    test)      cmd_test ;;
    help|--help|-h)
        head -27 "$0" | tail -24
        ;;
    *)
        red "Unknown command: $1"
        echo "Usage: $0 {run|discover|test|help}"
        exit 1
        ;;
esac
