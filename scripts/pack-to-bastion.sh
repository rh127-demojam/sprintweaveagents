#!/usr/bin/env bash
# Pack sources and SCP to RHDP bastion (run from WSL at CFP_NEW root or from this script).
#
# Usage:
#   bash sprintweave-web/scripts/pack-to-bastion.sh
#   BASTION_PORT=32158 bash sprintweave-web/scripts/pack-to-bastion.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${WEB_DIR}/.." && pwd)"

BASTION_HOST="${BASTION_HOST:-lab-user@ssh.ocpv06.rhdp.net}"
BASTION_PORT="${BASTION_PORT:-32158}"
TGZ="${TGZ:-/tmp/sprintweave-bastion.tgz}"

echo "==> Packing from ${ROOT_DIR}"
cd "${ROOT_DIR}"

INCLUDES=(sprintweave-web)
[[ -d cpat-main ]] && INCLUDES+=(cpat-main)
[[ -d sprintweave-agents ]] && INCLUDES+=(sprintweave-agents)

tar -czf "${TGZ}" "${INCLUDES[@]}"
ls -lh "${TGZ}"

echo "==> SCP → ${BASTION_HOST} port ${BASTION_PORT}"
scp -P "${BASTION_PORT}" "${TGZ}" "${BASTION_HOST}:~/"

echo "==> Done. SSH to bastion and run:"
echo "    bash -s <<'EOF'"
echo "    # or copy script from tarball after extract"
echo "    EOF"
echo ""
echo "    ssh -p ${BASTION_PORT} ${BASTION_HOST}"
echo "    mkdir -p ~/sprintweave-build && tar -xzf ~/sprintweave-bastion.tgz -C ~/sprintweave-build"
echo "    bash ~/sprintweave-build/sprintweave-web/scripts/bastion-build-rollout.sh"
