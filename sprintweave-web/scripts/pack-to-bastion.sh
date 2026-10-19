#!/usr/bin/env bash
# Pack sources and SCP to RHDP bastion (run from WSL at CFP_NEW root or from this script).
#
# Usage:
#   bash sprintweave-web/scripts/pack-to-bastion.sh
#   BASTION_PORT=2222 bash sprintweave-web/scripts/pack-to-bastion.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${WEB_DIR}/.." && pwd)"

BASTION_HOST="${BASTION_HOST:-lab-user@ssh.ocpv06.rhdp.net}"
BASTION_PORT="${BASTION_PORT:-2222}"
REMOTE_DIR="${REMOTE_DIR:-~/CFP_NEW}"
TGZ="${TGZ:-/tmp/sprintweave-bastion.tgz}"
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15)

echo "==> Packing from ${ROOT_DIR}"
cd "${ROOT_DIR}"

# Core folders
INCLUDES=(sprintweave-web cpat-main)

# Root build files
[[ -f Dockerfile ]]  && INCLUDES+=(Dockerfile)
[[ -f bringup.sh ]]  && INCLUDES+=(bringup.sh)
[[ -f REVIEW.md ]]   && INCLUDES+=(REVIEW.md)

# Exclude heavy/unnecessary files
tar -czf "${TGZ}" \
  --exclude='*.zip' \
  --exclude='*.tar' \
  --exclude='*.tar.gz' \
  --exclude='*.rtf' \
  --exclude='*.docx' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='node_modules' \
  "${INCLUDES[@]}"

ls -lh "${TGZ}"

echo "==> SCP → ${BASTION_HOST} port ${BASTION_PORT}"
scp "${SSH_OPTS[@]}" -P "${BASTION_PORT}" "${TGZ}" "${BASTION_HOST}:~/"

echo "==> Extracting on bastion…"
ssh "${SSH_OPTS[@]}" -p "${BASTION_PORT}" "${BASTION_HOST}" \
  "mkdir -p ${REMOTE_DIR} && cd ${REMOTE_DIR} && tar -xzf ~/sprintweave-bastion.tgz && chmod +x bringup.sh 2>/dev/null || true"

echo ""
echo "==> Done! On bastion run:"
echo ""
echo "    ssh -p ${BASTION_PORT} ${BASTION_HOST}"
echo "    cd ${REMOTE_DIR}"
echo "    export REGISTRY=quay.io/rh_global_services_auto"
echo "    export LLM_API_KEY=sk-your-key"
echo "    ./bringup.sh deploy"
