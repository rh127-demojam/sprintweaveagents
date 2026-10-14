# SprintWeave + CPAT  —  standalone two-folder build
#
# Build context: CFP_NEW/  (the repo root)
#
#   podman build \
#     --build-arg BASE_IMAGE=quay.io/YOUR_ORG/sprintweave-docling-base:latest \
#     --build-arg PIPELINES=lab-requirements,rhoso \
#     -t quay.io/YOUR_ORG/sprintweave-cpat:latest .
#
# Only two source folders are needed:
#   sprintweave-web/   — runtime engine (API, UI, LLM, prompts)
#   cpat-main/         — agent rules, skills, pipeline config, context
#
# sprintweave-agents/ is NOT required.  cpat-main is self-contained.

ARG BASE_IMAGE=quay.io/rh_global_services_auto/sprintweave-docling-base:latest
FROM ${BASE_IMAGE}

ARG PIPELINES=all

USER root

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    SPRINTWEAVE_DATA_DIR=/data \
    SPRINTWEAVE_PROMPTS=/app/sprintweave-web/prompts \
    SPRINTWEAVE_AGENTS_DIR=/app/sprintweave-agents \
    SPRINTWEAVE_PIPELINES=${PIPELINES} \
    SPRINTWEAVE_USE_DOCLING=true \
    PIP_TRUSTED_HOST="pypi.org pypi.python.org files.pythonhosted.org" \
    HF_HOME=/opt/docling-cache \
    TRANSFORMERS_CACHE=/opt/docling-cache \
    DOCLING_CACHE_DIR=/opt/docling-cache

# Ensure appuser exists when BASE_IMAGE is plain python:3.12-slim
RUN if ! id appuser >/dev/null 2>&1; then \
      groupadd -g 1001 appuser && useradd -m -u 1001 -g 1001 -s /bin/bash appuser; \
    fi \
    && mkdir -p /app /data/jobs /opt/docling-cache /tmp/docling-cache \
    && chmod -R a+rwx /opt/docling-cache /tmp/docling-cache \
    && chown -R appuser:appuser /app /data /opt/docling-cache \
    && (chmod -R a+rX /usr/local/lib/python*/site-packages/rapidocr 2>/dev/null || true) \
    && (chown -R appuser:appuser /usr/local/lib/python*/site-packages/rapidocr 2>/dev/null || true)

WORKDIR /app

COPY sprintweave-web/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r /tmp/requirements.txt

# OpenShift client for in-cluster CPAT deploy (BuildConfig + Route)
RUN curl -fsSL -o /tmp/openshift-client-linux.tar.gz \
      https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz \
    && tar -xzf /tmp/openshift-client-linux.tar.gz -C /usr/local/bin oc kubectl \
    && rm -f /tmp/openshift-client-linux.tar.gz \
    && chmod 755 /usr/local/bin/oc /usr/local/bin/kubectl \
    && oc version --client

# ── Engine ──────────────────────────────────────────────────────
COPY sprintweave-web/ ./sprintweave-web/

# ── Agents (cpat-main is the single self-contained agents tree) ─
# Mapped into the standard /app/sprintweave-agents/ path so
# worker.py finds rules, skills, context, pipelines.yaml.
COPY cpat-main/ ./sprintweave-agents/

RUN chown -R appuser:appuser /app /data

USER 1001

WORKDIR /app/sprintweave-web
ENV PYTHONPATH=/app/sprintweave-web:/app

EXPOSE 8080 8000

CMD ["streamlit", "run", "ui/app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
