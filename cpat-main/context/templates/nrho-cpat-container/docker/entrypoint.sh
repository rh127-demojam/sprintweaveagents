#!/bin/sh
# ---------------------------------------------------------------------------
# CPAT container entrypoint — Golden template, NEVER LLM-generated.
# Starts gunicorn (Flask API) on 127.0.0.1:5000 and nginx on port 8080.
# OpenShift-safe: no chmod on mount roots, nginx uses /tmp dirs.
# ---------------------------------------------------------------------------
set -e

export CPAT_DATA_DIR="${CPAT_DATA_DIR:-/cpat-data}"

# Create runtime dirs (NOT chmod on the mount root — OpenShift rejects it)
mkdir -p "$CPAT_DATA_DIR/uploads" \
         "$CPAT_DATA_DIR/secrets" \
         "$CPAT_DATA_DIR/logs/registrations" \
         "$CPAT_DATA_DIR/logs/installations" \
         "$CPAT_DATA_DIR/artifacts" \
         /tmp/nginx_client_body /tmp/nginx_proxy \
         /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi \
         /tmp/nginx_logs

# Configure nginx to use /tmp for temp/pid/log files (non-root safe)
sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf 2>/dev/null || true
sed -i 's|error_log .*|error_log /tmp/nginx_logs/error.log warn;|' /etc/nginx/nginx.conf 2>/dev/null || true
sed -i 's|access_log .*|access_log /tmp/nginx_logs/access.log;|' /etc/nginx/nginx.conf 2>/dev/null || true

# Dynamic listen port (default 8080, overridable for host-network bastions)
LISTEN_PORT="${CPAT_LISTEN_PORT:-8080}"
if ! printf '%s' "${LISTEN_PORT}" | grep -Eq '^[0-9]+$'; then
  echo "CPAT_LISTEN_PORT must be numeric, got: ${LISTEN_PORT}" >&2
  exit 1
fi
sed -i "s/listen [0-9]\+;/listen ${LISTEN_PORT};/" /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Start gunicorn (Flask) on 127.0.0.1:5000
# --timeout 7200: OCP tasks stream Ansible output for up to ~60 min.
gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --preload \
    --timeout 7200 \
    --graceful-timeout 30 \
    --chdir /app \
    app:app &

# Start nginx in foreground (reverse proxy on port 8080)
exec nginx -g 'daemon off;'
