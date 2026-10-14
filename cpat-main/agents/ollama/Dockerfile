# SprintWeave Agent Pipeline — Local GPU Container (Ollama)
#
# Self-contained container with Ollama + model + agent runner.
# No external API keys required. Everything runs locally.
#
# Build from CPAT root (downloads ~10GB for model on first run):
#   docker build -f agents/ollama/Dockerfile -t cpat-agents-ollama .
#
# Run:
#   docker run --rm --gpus all -v ./output:/workspace/output cpat-agents-ollama
#   docker run --rm --gpus all -v ./output:/workspace/output cpat-agents-ollama --pipeline rda
#
# CPU-only (slower):
#   docker run --rm -v ./output:/workspace/output cpat-agents-ollama --model qwen2.5-coder:7b

FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python deps
RUN pip install --no-cache-dir openai pyyaml

WORKDIR /workspace

# Copy agent definitions (the "brain")
COPY .cursor/rules/ .cursor/rules/
COPY context/ context/
COPY tools/ tools/
COPY output/pipeline-reports/ output/pipeline-reports/
COPY output/ciq-generators/ output/ciq-generators/

# Copy pipeline runner
COPY agents/ollama/run_pipeline.py agents/ollama/run_pipeline.py

# Startup script: launch Ollama, pull model, run pipeline
COPY <<'EOF' /entrypoint.sh
#!/bin/bash
set -e

MODEL="${CPAT_MODEL:-qwen2.5-coder:14b}"
echo "Starting Ollama server..."
ollama serve &
sleep 3

echo "Pulling model: $MODEL (this may take a while on first run)..."
ollama pull "$MODEL"
echo "Model ready."

echo "Starting CPAT Agent Pipeline..."
python agents/ollama/run_pipeline.py \
    --model "$MODEL" \
    --api-base http://localhost:11434/v1 \
    "$@"
EOF
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--pipeline", "rhoso-delivery"]
