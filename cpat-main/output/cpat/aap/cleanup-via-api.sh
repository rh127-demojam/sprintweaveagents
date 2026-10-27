#!/bin/bash
# ---------------------------------------------------------------------------
# Cleanup AAP objects via REST API
# Removes ALL resources created by import-via-api.sh in dependency-safe order.
#
# Usage:
#   export AAP_URL=https://localhost
#   export AAP_USER=admin
#   export AAP_PASS='<password>'
#   bash cleanup-via-api.sh
#
# By default the script runs in DRY-RUN mode.
# To actually delete, pass --confirm:
#   bash cleanup-via-api.sh --confirm
#
# Deletion order (respects dependencies):
#   1. Workflow Templates (and their nodes)
#   2. Job Templates (and their surveys + credential associations)
#   3. Credential Instances (created from custom types only)
#   4. Custom Credential Types
#   5. Project
#   6. Source Control Credential
#   7. Inventory (and its hosts)
# ---------------------------------------------------------------------------

set -euo pipefail

AAP_URL="${AAP_URL:?Set AAP_URL (e.g. https://localhost)}"
AAP_USER="${AAP_USER:-admin}"
AAP_PASS="${AAP_PASS:?Set AAP_PASS}"

DRY_RUN=true
if [ "${1:-}" = "--confirm" ]; then
  DRY_RUN=false
fi

# Auto-detect API base path
detect_api_base() {
  if curl -sk "${AAP_URL}/api/" 2>/dev/null | grep -q '"controller"'; then
    echo "/api/controller/v2"
  else
    echo "/api/v2"
  fi
}

API_BASE=$(detect_api_base)
echo "Detected API base: ${API_BASE}"

api() {
  local method="$1" endpoint="$2"
  shift 2
  curl -sk -X "$method" \
    -u "${AAP_USER}:${AAP_PASS}" \
    -H "Content-Type: application/json" \
    "${AAP_URL}${API_BASE}${endpoint}" \
    "$@"
}

lookup_id() {
  local endpoint="$1" name="$2"
  api GET "${endpoint}?name=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${name}'))")" \
    | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['results'][0]['id'] if r.get('results') else '')" 2>/dev/null
}

delete_resource() {
  local resource_type="$1" name="$2" endpoint="$3"
  local res_id
  res_id=$(lookup_id "$endpoint" "$name")
  if [ -n "$res_id" ]; then
    if $DRY_RUN; then
      echo "  [DRY-RUN] Would delete $resource_type '$name' (ID=$res_id)"
    else
      echo -n "  Deleting $resource_type '$name' (ID=$res_id) ... "
      local http_code
      http_code=$(api DELETE "${endpoint}${res_id}/" -o /dev/null -w "%{http_code}")
      echo "$http_code"
    fi
  else
    echo "  SKIP: $resource_type '$name' not found"
  fi
}

echo "========================================="
if $DRY_RUN; then
  echo "AAP Cleanup — DRY RUN (pass --confirm to delete)"
else
  echo "AAP Cleanup — LIVE DELETE"
fi
echo "Target: ${AAP_URL}"
echo "========================================="

DELETED=0
SKIPPED=0

# -----------------------------------------------------------------------
# 1. WORKFLOW TEMPLATES
# -----------------------------------------------------------------------
echo ""
echo "--- Workflow Templates ---"

WORKFLOW_TEMPLATES=(
  "OCP ABI Full Install"
  "OCP ABI-DC Full Install"
  "OCP Destroy"
  "RHOSO Full Install"
)

for wf in "${WORKFLOW_TEMPLATES[@]}"; do
  delete_resource "Workflow Template" "$wf" /workflow_job_templates/
done

# -----------------------------------------------------------------------
# 2. JOB TEMPLATES
# -----------------------------------------------------------------------
echo ""
echo "--- Job Templates ---"

OCP_JOB_TEMPLATES=(
  "OCP Generate Manifests"
  "OCP Prerequisites"
  "OCP Bastion Preparation"
  "OCP DNS DHCP Validation"
  "OCP NTP Sync"
  "OCP Mirror Registry Install"
  "OCP OC Mirror Execution"
  "OCP IDMS ITMS Configuration"
  "OCP Generate Install Config"
  "OCP Generate Agent Config"
  "OCP Generate NMState Configs"
  "OCP Generate Ignition Configs"
  "OCP Create Agent ISO"
  "OCP Boot Nodes From ISO"
  "OCP Bootstrap Cluster"
  "OCP Wait Install Complete"
  "OCP Approve CSRs"
  "OCP Configure Authentication"
  "OCP Day-2 Operator Installation"
  "OCP MetalLB Configuration"
  "OCP SR-IOV Multus Configuration"
  "OCP Cluster Health Check"
  "OCP Node Readiness Check"
  "OCP Full Install"
  "OCP Uninstall Mirror Registry"
  "OCP Destroy Cluster"
  "OCP Validate"
)

RHOSO_JOB_TEMPLATES=(
  "RHOSO Generate Manifests"
  "RHOSO Pre-requisites"
  "RHOSO Verify Required CRDs"
  "RHOSO Prerequisite Operator Installation"
  "RHOSO Disconnected Environment Preparation"
  "RHOSO Generate OSP Secret"
  "RHOSO Generate Data Plane Secrets"
  "RHOSO Generate Ceph Secret"
  "RHOSO Persistent Storage Configuration"
  "RHOSO Trident Storage Configuration"
  "RHOSO Generate Storage CRs"
  "RHOSO OpenStack Operator Installation"
  "RHOSO RHOCP Preparation"
  "RHOSO Control Plane Deployment"
  "RHOSO Control Plane Customization"
  "RHOSO Network Preparation"
  "RHOSO Data Plane Deployment"
  "RHOSO Post-Deployment Validation"
  "RHOSO Observability Configuration"
  "RHOSO Register"
)

echo "  --- OCP ---"
for jt in "${OCP_JOB_TEMPLATES[@]}"; do
  delete_resource "Job Template" "$jt" /job_templates/
done

echo "  --- RHOSO ---"
for jt in "${RHOSO_JOB_TEMPLATES[@]}"; do
  delete_resource "Job Template" "$jt" /job_templates/
done

# -----------------------------------------------------------------------
# 3. CREDENTIAL INSTANCES (created from custom types)
# -----------------------------------------------------------------------
echo ""
echo "--- Credential Instances (custom types) ---"

CUSTOM_CRED_TYPES=("Bastion SSH" "BMC Credentials" "Pull Secret")

for ct_name in "${CUSTOM_CRED_TYPES[@]}"; do
  ct_id=$(lookup_id /credential_types/ "$ct_name")
  if [ -n "$ct_id" ]; then
    cred_ids=$(api GET "/credentials/?credential_type=${ct_id}&page_size=200" \
      | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('results', []):
    print(r['id'], r['name'])
" 2>/dev/null)

    if [ -n "$cred_ids" ]; then
      while IFS=' ' read -r cid cname; do
        if $DRY_RUN; then
          echo "  [DRY-RUN] Would delete Credential '$cname' (ID=$cid, type='$ct_name')"
        else
          echo -n "  Deleting Credential '$cname' (ID=$cid, type='$ct_name') ... "
          http_code=$(api DELETE "/credentials/${cid}/" -o /dev/null -w "%{http_code}")
          echo "$http_code"
        fi
      done <<< "$cred_ids"
    else
      echo "  No credentials of type '$ct_name'"
    fi
  else
    echo "  SKIP: Credential type '$ct_name' not found"
  fi
done

# -----------------------------------------------------------------------
# 4. CUSTOM CREDENTIAL TYPES
# -----------------------------------------------------------------------
echo ""
echo "--- Custom Credential Types ---"

for ct in "${CUSTOM_CRED_TYPES[@]}"; do
  delete_resource "Credential Type" "$ct" /credential_types/
done

# -----------------------------------------------------------------------
# 5. PROJECT
# -----------------------------------------------------------------------
echo ""
echo "--- Project ---"
delete_resource "Project" "Cloud Platform Automation" /projects/

# -----------------------------------------------------------------------
# 6. SOURCE CONTROL CREDENTIAL
# -----------------------------------------------------------------------
echo ""
echo "--- Source Control Credential ---"

# Find credentials of kind=scm created by the import script
SCM_CREDS=$(api GET "/credentials/?kind=scm&page_size=200" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('results', []):
    if r.get('managed') != True:
        print(r['id'], r['name'])
" 2>/dev/null)

if [ -n "$SCM_CREDS" ]; then
  while IFS=' ' read -r cid cname; do
    if $DRY_RUN; then
      echo "  [DRY-RUN] Would delete Source Control Credential '$cname' (ID=$cid)"
    else
      echo -n "  Deleting Source Control Credential '$cname' (ID=$cid) ... "
      http_code=$(api DELETE "/credentials/${cid}/" -o /dev/null -w "%{http_code}")
      echo "$http_code"
    fi
  done <<< "$SCM_CREDS"
else
  echo "  No Source Control credentials found"
fi

# -----------------------------------------------------------------------
# 7. INVENTORY
# -----------------------------------------------------------------------
echo ""
echo "--- Inventory ---"
delete_resource "Inventory" "Automation Localhost" /inventories/

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
echo ""
echo "========================================="
if $DRY_RUN; then
  echo "DRY RUN complete — no resources were deleted."
  echo ""
  echo "To perform the actual cleanup, run:"
  echo "  bash cleanup-via-api.sh --confirm"
else
  echo "Cleanup complete!"
  echo ""
  echo "Deleted:"
  echo "  Workflow Templates:     ${#WORKFLOW_TEMPLATES[@]}"
  echo "  Job Templates:          $((${#OCP_JOB_TEMPLATES[@]} + ${#RHOSO_JOB_TEMPLATES[@]}))"
  echo "  Credential Types:       ${#CUSTOM_CRED_TYPES[@]} (+ instances)"
  echo "  Source Control Creds:   (any found)"
  echo "  Project:                1"
  echo "  Inventory:              1"
fi
echo "========================================="
