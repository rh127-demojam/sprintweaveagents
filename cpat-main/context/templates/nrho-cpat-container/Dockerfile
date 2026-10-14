# ---------------------------------------------------------------------------
# CPAT — Cloud Platform Automation Tool
# Golden Dockerfile template — NEVER LLM-generated.
# Multi-stage: React UI → Flask API → Ansible → Nginx
# OpenShift-safe: non-root UID, port 8080, /tmp nginx dirs
# ---------------------------------------------------------------------------

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

ARG CACHEBUST=1
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime (Flask + Gunicorn + Nginx + Ansible)
FROM python:3.12-slim

ARG CPAT_VERSION=
LABEL org.opencontainers.image.title="CPAT" \
      org.opencontainers.image.description="Cloud Platform Automation Tool — RHOSO + OCP" \
      org.opencontainers.image.version="${CPAT_VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CPAT_SECRET_KEY=cpat-change-me-at-runtime \
    CPAT_ROOT=/app \
    CPAT_DATA_DIR=/cpat-data \
    CPAT_VERSION=${CPAT_VERSION} \
    ANSIBLE_CONFIG=/app/ansible.cfg

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       nginx \
       ansible-core \
       openssh-client \
       sshpass \
       curl \
       iputils-ping \
       ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

# OCP binaries — downloaded at build time from mirror.openshift.com.
# Override at build: --build-arg OCP_VERSION=4.19
# Pre-place binaries in binaries/ to skip download.
ARG OCP_VERSION=4.20
ARG OCP_CHANNEL=stable

COPY binaries/ /tmp/ocp-bin/
RUN set -e ; \
    if [ -f /tmp/ocp-bin/openshift-install ]; then \
      echo "=== Using pre-placed extracted binaries ===" ; \
      for f in openshift-install oc kubectl; do \
        [ -f "/tmp/ocp-bin/$f" ] && install -m 0755 "/tmp/ocp-bin/$f" /usr/local/bin/ ; \
      done ; \
    elif [ -f /tmp/ocp-bin/openshift-install-linux.tar.gz ]; then \
      echo "=== Using pre-placed tarballs ===" ; \
      tar xzf /tmp/ocp-bin/openshift-client-linux.tar.gz -C /usr/local/bin/ oc kubectl 2>/dev/null || true ; \
      tar xzf /tmp/ocp-bin/openshift-install-linux.tar.gz -C /usr/local/bin/ openshift-install ; \
      chmod +x /usr/local/bin/openshift-install /usr/local/bin/oc /usr/local/bin/kubectl ; \
    else \
      MIRROR="https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp" ; \
      echo "=== Downloading OCP ${OCP_VERSION} binaries ===" ; \
      for CHANNEL in ${OCP_CHANNEL}-${OCP_VERSION} latest-${OCP_VERSION} candidate-${OCP_VERSION}; do \
        URL="${MIRROR}/${CHANNEL}/openshift-client-linux.tar.gz" ; \
        if curl -kfL --connect-timeout 15 --max-time 120 -o /tmp/openshift-client.tar.gz "$URL"; then \
          FOUND_CHANNEL="${CHANNEL}" ; break ; \
        fi ; \
      done ; \
      if [ -z "${FOUND_CHANNEL:-}" ]; then \
        echo "WARN: Could not download OCP binaries — place tarballs in binaries/" ; \
      else \
        BASE="${MIRROR}/${FOUND_CHANNEL}" ; \
        tar xzf /tmp/openshift-client.tar.gz -C /usr/local/bin/ oc kubectl ; \
        curl -kfL --connect-timeout 15 --max-time 900 -o /tmp/openshift-install.tar.gz "${BASE}/openshift-install-linux.tar.gz" ; \
        tar xzf /tmp/openshift-install.tar.gz -C /usr/local/bin/ openshift-install ; \
        chmod +x /usr/local/bin/openshift-install /usr/local/bin/oc /usr/local/bin/kubectl ; \
        rm -f /tmp/openshift-install.tar.gz /tmp/openshift-client.tar.gz ; \
      fi ; \
    fi ; \
    mkdir -p /app/mirror-artifacts ; \
    for f in mirror-registry-amd64.tar.gz oc-mirror-rhel9-linux-amd64.tar.gz; do \
      [ -f "/tmp/ocp-bin/$f" ] && mv "/tmp/ocp-bin/$f" /app/mirror-artifacts/ ; \
    done ; \
    rm -rf /tmp/ocp-bin

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt .
ENV PIP_TRUSTED_HOST="pypi.org pypi.python.org files.pythonhosted.org"
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# Application layers — order matters for Docker layer caching
COPY backend/ /app/
COPY ansible/ /app/ansible/
COPY ansible.cfg /app/ansible.cfg
COPY --from=frontend-build /build/dist /app/static
COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/entrypoint.sh /entrypoint.sh

# ── OpenShift-safe permissions ──
# OpenShift runs as random non-root UID (e.g. 1000890000).
# All runtime-writable dirs MUST be world-writable.
RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /cpat-data \
       /tmp/nginx_client_body /tmp/nginx_proxy \
       /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi \
       /tmp/nginx_logs /var/lib/nginx/body \
       /var/lib/nginx/proxy /var/lib/nginx/fastcgi \
       /var/lib/nginx/uwsgi /var/lib/nginx/scgi \
       /var/log/nginx /run \
    && chmod -R 777 /cpat-data /tmp /var/lib/nginx /var/log/nginx /run \
       2>/dev/null || true

# Non-privileged port (OpenShift blocks < 1024 for non-root)
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
