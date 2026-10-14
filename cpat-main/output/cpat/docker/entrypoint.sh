#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# CPAT container entrypoint
# Starts gunicorn (Flask API) on 127.0.0.1:5000 and nginx on port 80.
# Nginx reverse-proxies /api/ to gunicorn; serves React SPA from /app/static.
# ---------------------------------------------------------------------------

export CPAT_DATA_DIR="${CPAT_DATA_DIR:-/cpat-data}"
mkdir -p "$CPAT_DATA_DIR"

# One-time migrate if an older MSYS-mangled tree exists and /cpat-data is empty.
_legacy=""
for _candidate in \
  "/app/C:/Program Files/Git/cpat-data" \
  /app/C:/Program\ Files/Git/cpat-data
do
  if [ -d "$_candidate" ]; then
    _legacy="$_candidate"
    break
  fi
done

if [ -n "$_legacy" ] && [ ! -f /cpat-data/cpat.db ]; then
  echo "Migrating runtime data from MSYS path to /cpat-data..."
  cp -a "$_legacy"/. /cpat-data/ 2>/dev/null || true
fi

# Start gunicorn (Flask) on 127.0.0.1:5000
# --preload: runs app init (DB create) once in master before forking workers
# --timeout 7200: OCP tasks (mirror-registry install, oc-mirror) stream Ansible
#   output for up to ~60 min. Sync workers must finish within --timeout or the
#   arbiter kills them. 2 hours is generous for the longest possible task.
# --graceful-timeout 30: after SIGTERM, allow 30s for a clean shutdown.
gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --preload \
    --timeout 7200 \
    --graceful-timeout 30 \
    --chdir /app \
    app:app &

# Start nginx in foreground (reverse proxy on port 80)
exec nginx -g 'daemon off;'
