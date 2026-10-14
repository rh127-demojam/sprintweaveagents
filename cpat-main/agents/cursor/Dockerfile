# CPAT Agent Pipeline Runner — Cursor SDK
#
# Runs RHOSO + OCP agents via Cursor SDK inside a container.
# The container carries the full project context (agent rules, templates,
# pipeline definitions) so agents have everything they need.
#
# Build (from CPAT_ROOT):
#   docker build -f agents/cursor/Dockerfile -t cpat-agents-cursor .
#
# Run (full RHOSO delivery):
#   docker run --rm -e CURSOR_API_KEY="cursor_..." cpat-agents-cursor
#
# Run (OCP delivery):
#   docker run --rm -e CURSOR_API_KEY="cursor_..." cpat-agents-cursor --pipeline ocp-delivery
#
# Run (full RHOSO + OCP — 14 stages):
#   docker run --rm -e CURSOR_API_KEY="cursor_..." cpat-agents-cursor --pipeline full-delivery
#
# Run (RDA only):
#   docker run --rm -e CURSOR_API_KEY="cursor_..." cpat-agents-cursor --pipeline rda
#
# Run (single stage):
#   docker run --rm -e CURSOR_API_KEY="cursor_..." cpat-agents-cursor --stage RDE-1
#
# Extract generated output:
#   docker run --rm -e CURSOR_API_KEY="cursor_..." -v ./output:/workspace/output cpat-agents-cursor

FROM python:3.12-slim

LABEL maintainer="Global Customization Team"
LABEL description="CPAT Agent Pipeline Runner — RHOSO + OCP via Cursor SDK"

WORKDIR /workspace

# Install Cursor SDK
RUN pip install --no-cache-dir cursor-sdk

# Copy agent definitions and context (the "brain" of the agents)
# Paths are relative to the build context (CPAT_ROOT), not the Dockerfile.
# Build with: docker build -f agents/cursor/Dockerfile -t cpat-agents-cursor .
COPY .cursor/rules/ .cursor/rules/
COPY context/ context/
COPY tools/ tools/

# Copy existing output as reference for ENHANCE mode (optional)
COPY output/pipeline-reports/ output/pipeline-reports/
COPY output/ciq-generators/ output/ciq-generators/

# Copy pipeline runner
COPY agents/cursor/run_pipeline.py .

# Default: run full delivery pipeline
ENTRYPOINT ["python", "run_pipeline.py"]
CMD ["--pipeline", "rhoso-delivery"]
