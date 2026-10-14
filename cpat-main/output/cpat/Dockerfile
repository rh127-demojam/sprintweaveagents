# ---------------------------------------------------------------------------
# CPAT — Cloud Platform Automation Tool
# Multi-stage container image: React UI → Flask API → Ansible → Nginx
# RHOSO CIQ Schema v1.4 — 19 templates, 24 tasks, 18 CIQ tables, ~210 defaults
# OCP CIQ Schema v1.0 — 12 templates, 27 tasks, 18 CIQ tables, ~170 defaults
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

# Pin image version at build time (YY.M.W). Override with --build-arg CPAT_VERSION=...
# UI displays this as vYY.M.W.
ARG CPAT_VERSION=
LABEL org.opencontainers.image.title="CPAT" \
      org.opencontainers.image.description="Cloud Platform Automation Tool — RHOSO 18.0 + OCP 4.17–4.20" \
      org.opencontainers.image.version="${CPAT_VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CPAT_SECRET_KEY=cpat-change-me-in-production \
    CPAT_ROOT=/app \
    CPAT_DATA_DIR=/cpat-data \
    CPAT_VERSION=${CPAT_VERSION} \
    ANSIBLE_CONFIG=/app/ansible.cfg

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       nginx \
       ansible-core \
       openssh-client \
       curl \
       ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

# OCP binaries — downloaded at build time from mirror.openshift.com.
# Override OCP_VERSION at build time: --build-arg OCP_VERSION=4.19
# To use pre-downloaded binaries instead, place them in binaries/ dir.
ARG OCP_VERSION=4.20
ARG OCP_CHANNEL=stable

COPY binaries/ /tmp/ocp-bin/
RUN set -e ; \
    # --- OCP binaries: openshift-install, oc, kubectl --- \
    if [ -f /tmp/ocp-bin/openshift-install ]; then \
      echo "=== Using pre-placed extracted binaries ===" ; \
      for f in openshift-install oc kubectl; do \
        [ -f "/tmp/ocp-bin/$f" ] && install -m 0755 "/tmp/ocp-bin/$f" /usr/local/bin/ ; \
      done ; \
    elif [ -f /tmp/ocp-bin/openshift-install-linux.tar.gz ]; then \
      echo "=== Using pre-placed tarballs from binaries/ directory ===" ; \
      echo "Extracting oc + kubectl from openshift-client-linux.tar.gz..." ; \
      tar xzf /tmp/ocp-bin/openshift-client-linux.tar.gz -C /usr/local/bin/ oc kubectl 2>/dev/null || true ; \
      echo "Extracting openshift-install from openshift-install-linux.tar.gz..." ; \
      tar xzf /tmp/ocp-bin/openshift-install-linux.tar.gz -C /usr/local/bin/ openshift-install ; \
      chmod +x /usr/local/bin/openshift-install /usr/local/bin/oc /usr/local/bin/kubectl ; \
    else \
      MIRROR="https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp" ; \
      echo "=== Downloading OCP ${OCP_VERSION} binaries ===" ; \
      for CHANNEL in ${OCP_CHANNEL}-${OCP_VERSION} latest-${OCP_VERSION} candidate-${OCP_VERSION}; do \
        URL="${MIRROR}/${CHANNEL}/openshift-client-linux.tar.gz" ; \
        echo "Trying channel ${CHANNEL} ..." ; \
        if curl -kfL --connect-timeout 15 --max-time 120 -o /tmp/openshift-client.tar.gz "$URL"; then \
          echo "Found binaries in channel: ${CHANNEL}" ; \
          FOUND_CHANNEL="${CHANNEL}" ; \
          break ; \
        fi ; \
        echo "Channel ${CHANNEL} not available, trying next..." ; \
      done ; \
      if [ -z "${FOUND_CHANNEL:-}" ]; then \
        echo "ERROR: Could not download OCP binaries from any channel for OCP ${OCP_VERSION}" ; \
        echo "Place tarballs in binaries/ directory and rebuild." ; \
        exit 1 ; \
      fi ; \
      BASE="${MIRROR}/${FOUND_CHANNEL}" ; \
      echo "Extracting oc + kubectl..." ; \
      tar xzf /tmp/openshift-client.tar.gz -C /usr/local/bin/ oc kubectl ; \
      echo "Downloading openshift-install (~395 MB — this takes a few minutes)..." ; \
      curl -kfL --connect-timeout 15 --max-time 900 -o /tmp/openshift-install.tar.gz "${BASE}/openshift-install-linux.tar.gz" ; \
      echo "Extracting openshift-install..." ; \
      tar xzf /tmp/openshift-install.tar.gz -C /usr/local/bin/ openshift-install ; \
      chmod +x /usr/local/bin/openshift-install /usr/local/bin/oc /usr/local/bin/kubectl ; \
      rm -f /tmp/openshift-install.tar.gz /tmp/openshift-client.tar.gz ; \
    fi ; \
    echo "=== OCP binaries installed ===" ; \
    openshift-install version ; \
    oc version --client ; \
    # --- Preserve mirror artifacts for bastion deployment --- \
    mkdir -p /app/mirror-artifacts ; \
    for f in mirror-registry-amd64.tar.gz oc-mirror-rhel9-linux-amd64.tar.gz oc-mirror-rhel9-linux-amd64.tar; do \
      [ -f "/tmp/ocp-bin/$f" ] && mv "/tmp/ocp-bin/$f" /app/mirror-artifacts/ \
        && echo "Bundled mirror artifact: $f" ; \
    done ; \
    rm -rf /tmp/ocp-bin

WORKDIR /app

# Nokia internal PyPI — avoids SSL errors behind corporate proxy
RUN printf '[global]\ntrusted-host = repo.cci.nokia.net\nindex-url = https://repo.cci.nokia.net/api/pypi/python/simple\nproxy =\n' > /etc/pip.conf

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application layers — order matters for Docker layer caching
COPY backend/ /app/
COPY ansible/ /app/ansible/
COPY ansible.cfg /app/ansible.cfg
COPY --from=frontend-build /build/dist /app/static
COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/entrypoint.sh /entrypoint.sh

RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /cpat-data

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
