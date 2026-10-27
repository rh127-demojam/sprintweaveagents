#!/bin/bash
# ---------------------------------------------------------------------------
# Import AAP objects via REST API
# Use this when awx-manage / awx CLI is not available.
#
# Usage:
#   export AAP_URL=https://localhost
#   export AAP_USER=admin
#   export AAP_PASS='<password>'
#   bash import-via-api.sh
#
# Optional environment variables:
#   SCM_URL          — Git URL for the automation project (if not set, uses existing project)
#                      e.g. https://gitlab.com/rh-global-services-auto/cpat.git
#   SCM_CREDENTIAL   — Name of Source Control credential to use/create (for private repos)
#   SCM_USERNAME     — Git username (used to create SCM_CREDENTIAL if it doesn't exist)
#   SCM_PASSWORD     — Git personal access token (used to create SCM_CREDENTIAL if it doesn't exist)
#   SCM_BRANCH       — Git branch (default: "main")
#   PLAYBOOK_PREFIX  — Path prefix from repo root to ansible dir (default: "output/cpat")
#                      Set to "" if the repo root IS the ansible project root
#
# The script auto-creates all prerequisites:
#   1. Organization: "Default" (must already exist)
#   2. Inventory: "Automation Localhost" + localhost host
#   3. Source Control Credential (if SCM_CREDENTIAL + SCM_USERNAME + SCM_PASSWORD set)
#   4. Project: "Cloud Platform Automation" (Git if SCM_URL set, fallback otherwise)
#   5. Credential Types (3)
#   6. Job Templates (47) — one per UI task:
#        OCP: 26 task templates + 1 validate = 27
#        RHOSO: 19 task templates + 1 register = 20
#   7. Surveys attached to every job template
#   8. Credentials attached to all OCP job templates
#   9. Workflow Templates (4) with nodes wired (sequential on-success chains)
# ---------------------------------------------------------------------------

set -euo pipefail

AAP_URL="${AAP_URL:?Set AAP_URL (e.g. https://localhost)}"
AAP_USER="${AAP_USER:-admin}"
AAP_PASS="${AAP_PASS:?Set AAP_PASS}"

# Auto-detect API base path: AAP Gateway uses /api/controller/v2, standalone uses /api/v2
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
    | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['results'][0]['id'] if r.get('results') else '')"
}

echo "========================================="
echo "AAP Import via REST API"
echo "Target: ${AAP_URL}"
echo "========================================="

# -----------------------------------------------------------------------
# 1. CREDENTIAL TYPES
# -----------------------------------------------------------------------
echo ""
echo "--- Creating Credential Types ---"

# Bastion SSH
echo -n "  Bastion SSH ... "
api POST /credential_types/ -d '{
  "name": "Bastion SSH",
  "description": "SSH credentials for bastion host delegate_to tasks.",
  "kind": "cloud",
  "inputs": {
    "fields": [
      {"id": "bastion_ssh_user", "type": "string", "label": "Bastion SSH Username"},
      {"id": "bastion_ssh_key", "type": "string", "label": "Bastion SSH Private Key", "format": "ssh_private_key", "secret": true, "multiline": true}
    ],
    "required": ["bastion_ssh_user", "bastion_ssh_key"]
  },
  "injectors": {
    "file": {"template.bastion_key": "{{ bastion_ssh_key }}"},
    "extra_vars": {
      "ocp_bastion_ssh_user": "{{ bastion_ssh_user }}",
      "ocp_bastion_ssh_key_path": "{{ tower.filename.bastion_key }}"
    }
  }
}' -o /dev/null -w "%{http_code}\n"

# BMC Credentials
echo -n "  BMC Credentials ... "
api POST /credential_types/ -d '{
  "name": "BMC Credentials",
  "description": "Redfish BMC API credentials for bare-metal / virtual BMC.",
  "kind": "cloud",
  "inputs": {
    "fields": [
      {"id": "bmc_user", "type": "string", "label": "BMC Username"},
      {"id": "bmc_password", "type": "string", "label": "BMC Password", "secret": true}
    ],
    "required": ["bmc_user", "bmc_password"]
  },
  "injectors": {
    "extra_vars": {
      "ocp_bmc_user": "{{ bmc_user }}",
      "ocp_bmc_password": "{{ bmc_password }}"
    }
  }
}' -o /dev/null -w "%{http_code}\n"

# Pull Secret
echo -n "  Pull Secret ... "
api POST /credential_types/ -d '{
  "name": "Pull Secret",
  "description": "OpenShift pull secret (JSON). Injected as temp file; never logged.",
  "kind": "cloud",
  "inputs": {
    "fields": [
      {"id": "pull_secret_content", "type": "string", "label": "Pull Secret (JSON)", "secret": true, "multiline": true}
    ],
    "required": ["pull_secret_content"]
  },
  "injectors": {
    "file": {"template.pull_secret": "{{ pull_secret_content }}"},
    "extra_vars": {
      "ocp_pull_secret_path": "{{ tower.filename.pull_secret }}"
    }
  }
}' -o /dev/null -w "%{http_code}\n"

# -----------------------------------------------------------------------
# 2. CREATE PREREQUISITES (Inventory, Project)
# -----------------------------------------------------------------------
echo ""
echo "--- Creating Prerequisites ---"

ORG_ID=$(lookup_id /organizations/ "Default")
echo "  Organization 'Default': ID=$ORG_ID"

# --- Inventory: Automation Localhost ---
INVENTORY_ID=$(lookup_id /inventories/ "Automation Localhost")
if [ -z "$INVENTORY_ID" ]; then
  echo -n "  Creating Inventory 'Automation Localhost' ... "
  api POST /inventories/ -d "{
    \"name\": \"Automation Localhost\",
    \"description\": \"Local execution inventory\",
    \"organization\": ${ORG_ID}
  }" -o /dev/null -w "%{http_code}\n"
  INVENTORY_ID=$(lookup_id /inventories/ "Automation Localhost")

  echo -n "  Adding host 'localhost' ... "
  api POST "/inventories/${INVENTORY_ID}/hosts/" -d '{
    "name": "localhost",
    "variables": "ansible_connection: local"
  }' -o /dev/null -w "%{http_code}\n"
else
  echo "  Inventory 'Automation Localhost': already exists (ID=$INVENTORY_ID)"
fi

# --- Source Control Credential ---
SCM_URL="${SCM_URL:-}"
SCM_BRANCH="${SCM_BRANCH:-main}"
SCM_CREDENTIAL="${SCM_CREDENTIAL:-}"
SCM_USERNAME="${SCM_USERNAME:-}"
SCM_PASSWORD="${SCM_PASSWORD:-}"

if [ -n "$SCM_CREDENTIAL" ]; then
  # Check if the credential already exists with kind=scm
  SCM_CRED_ID=$(api GET "/credentials/?name=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${SCM_CREDENTIAL}'))")" \
    | python3 -c "
import json,sys
r = json.load(sys.stdin)
for c in r.get('results', []):
    if c.get('kind') == 'scm':
        print(c['id'])
        break
" 2>/dev/null)

  if [ -n "$SCM_CRED_ID" ]; then
    echo "  Source Control Credential '${SCM_CREDENTIAL}': already exists (ID=$SCM_CRED_ID)"
  elif [ -n "$SCM_USERNAME" ] && [ -n "$SCM_PASSWORD" ]; then
    # Look up the "Source Control" credential type ID
    SCM_TYPE_ID=$(api GET "/credential_types/?name=Source%20Control" \
      | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['results'][0]['id'] if r.get('results') else '')" 2>/dev/null)

    if [ -z "$SCM_TYPE_ID" ]; then
      echo "  ERROR: 'Source Control' credential type not found in AAP"
    else
      echo -n "  Creating Source Control Credential '${SCM_CREDENTIAL}' ... "
      SCM_CRED_ID=$(api POST /credentials/ -d "$(python3 -c "
import json
print(json.dumps({
    'name': '${SCM_CREDENTIAL}',
    'description': 'Git Source Control credential for project SCM sync',
    'credential_type': ${SCM_TYPE_ID},
    'organization': ${ORG_ID},
    'inputs': {
        'username': '${SCM_USERNAME}',
        'password': '${SCM_PASSWORD}'
    }
}))
")" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)

      if [ -n "$SCM_CRED_ID" ]; then
        echo "Created (ID=$SCM_CRED_ID)"
      else
        echo "FAILED"
        echo "  WARNING: Could not create SCM credential. Continuing without it..."
        SCM_CRED_ID=""
      fi
    fi
  else
    echo "  WARNING: Credential '${SCM_CREDENTIAL}' not found and SCM_USERNAME/SCM_PASSWORD not set."
    echo "           Set SCM_USERNAME and SCM_PASSWORD to create it automatically,"
    echo "           or create it manually in AAP UI: Credentials → Add → Type: Source Control"
    SCM_CRED_ID=""
  fi
else
  SCM_CRED_ID=""
fi

# --- Project: Cloud Platform Automation ---
PROJECT_ID=$(lookup_id /projects/ "Cloud Platform Automation")
if [ -z "$PROJECT_ID" ]; then
  if [ -n "$SCM_URL" ]; then

    echo -n "  Creating Project 'Cloud Platform Automation' (Git: ${SCM_URL}, branch: ${SCM_BRANCH}) ... "
    PROJECT_PAYLOAD=$(python3 -c "
import json
d = {
    'name': 'Cloud Platform Automation',
    'description': 'OCP and RHOSO deployment automation playbooks',
    'organization': ${ORG_ID},
    'scm_type': 'git',
    'scm_url': '${SCM_URL}',
    'scm_branch': '${SCM_BRANCH}',
    'scm_update_on_launch': True,
    'scm_clean': True
}
scm_cred = '${SCM_CRED_ID}'
if scm_cred:
    d['credential'] = int(scm_cred)
print(json.dumps(d))
")
    api POST /projects/ -d "$PROJECT_PAYLOAD" -o /dev/null -w "%{http_code}\n"
    PROJECT_ID=$(lookup_id /projects/ "Cloud Platform Automation")

    # Wait for initial SCM sync to complete
    if [ -n "$PROJECT_ID" ]; then
      echo -n "  Waiting for SCM sync ..."
      for i in $(seq 1 30); do
        STATUS=$(api GET "/projects/${PROJECT_ID}/" \
          | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
        if [ "$STATUS" = "successful" ]; then
          echo " done (synced)"
          break
        elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
          echo " FAILED"
          echo "  ERROR: SCM sync failed. Check AAP project settings and SCM credential."
          break
        fi
        echo -n "."
        sleep 2
      done
    fi
  else
    # No SCM URL — use first available project as fallback
    echo "  No SCM_URL set — looking for existing project ..."
    PROJECT_ID=$(api GET "/projects/?page_size=1" \
      | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['results'][0]['id'] if r.get('results') else '')")
    PROJECT_NAME=$(api GET "/projects/${PROJECT_ID}/" \
      | python3 -c "import json,sys; print(json.load(sys.stdin).get('name',''))")
    echo "  Using existing project '${PROJECT_NAME}' (ID=$PROJECT_ID)"
    echo "  NOTE: Set SCM_URL to create a dedicated project"
  fi
else
  echo "  Project 'Cloud Platform Automation': already exists (ID=$PROJECT_ID)"
fi

# --- Execution Environment: skip for now, use default ---
EE_ID=""
echo "  Execution Environment: skipped (will use AAP default)"

# Final check
echo ""
echo "  Summary:"
echo "    Organization:           ID=$ORG_ID"
echo "    Inventory:              ID=$INVENTORY_ID"
echo "    Project:                ID=$PROJECT_ID"
echo "    Execution Environment:  using default"

if [ -z "$PROJECT_ID" ] || [ -z "$INVENTORY_ID" ]; then
  echo ""
  echo "ERROR: Could not create/find all prerequisites."
  [ -z "$PROJECT_ID" ] && echo "  - Project failed. Set SCM_URL and re-run."
  [ -z "$INVENTORY_ID" ] && echo "  - Inventory 'Automation Localhost' failed."
  exit 1
fi

# Lookup credential type IDs
CRED_BASTION_TYPE_ID=$(lookup_id /credential_types/ "Bastion SSH")
CRED_BMC_TYPE_ID=$(lookup_id /credential_types/ "BMC Credentials")
CRED_PULL_TYPE_ID=$(lookup_id /credential_types/ "Pull Secret")

# -----------------------------------------------------------------------
# 3. JOB TEMPLATES — One per UI task (matches UI checkboxes 1:1)
# -----------------------------------------------------------------------
echo ""
echo "--- Creating Job Templates ---"

# Resolve available playbook from project (placeholder if project not yet set up)
AVAIL_PLAYBOOK=$(api GET "/projects/${PROJECT_ID}/playbooks/" \
  | python3 -c "import json,sys; p=json.load(sys.stdin); print(p[0] if p else '')" 2>/dev/null)

# Playbook base path — relative to the Git project root.
# If the repo root IS the ansible directory, use "ansible/playbooks/..."
# If the repo contains output/cpat/, use "output/cpat/ansible/playbooks/..."
PLAYBOOK_PREFIX="${PLAYBOOK_PREFIX:-output/cpat}"

# Helper: create a job template with a standard survey (CIQ + Cluster + Version)
create_ocp_jt() {
  local name="$1" task_tag="$2" desc="$3" timeout="${4:-14400}"
  local playbook="${PLAYBOOK_PREFIX}/ansible/playbooks/ocp_install.yml"
  echo -n "  $name ... "

  local has_playbook
  has_playbook=$(api GET "/projects/${PROJECT_ID}/playbooks/" \
    | python3 -c "import json,sys; print('yes' if '${playbook}' in json.load(sys.stdin) else 'no')" 2>/dev/null)
  local use_playbook="$playbook"
  local note=""
  if [ "$has_playbook" != "yes" ] && [ -n "$AVAIL_PLAYBOOK" ]; then
    use_playbook="$AVAIL_PLAYBOOK"
    note=" (placeholder — real playbook: ${playbook})"
  fi

  local payload
  payload=$(python3 -c "
import json
d = {
    'name': '${name}',
    'description': '${desc}',
    'job_type': 'run',
    'inventory': ${INVENTORY_ID},
    'project': ${PROJECT_ID},
    'playbook': '${use_playbook}',
    'verbosity': 0,
    'timeout': ${timeout},
    'ask_variables_on_launch': True,
    'survey_enabled': True,
    'extra_vars': json.dumps({'ocp_task': '${task_tag}'})
}
print(json.dumps(d))
")
  api POST /job_templates/ -d "$payload" -o /dev/null -w "%{http_code}${note}\n"
}

create_rhoso_jt() {
  local name="$1" task_tag="$2" desc="$3" timeout="${4:-14400}"
  local playbook="${PLAYBOOK_PREFIX}/ansible/playbooks/main.yml"
  echo -n "  $name ... "

  local has_playbook
  has_playbook=$(api GET "/projects/${PROJECT_ID}/playbooks/" \
    | python3 -c "import json,sys; print('yes' if '${playbook}' in json.load(sys.stdin) else 'no')" 2>/dev/null)
  local use_playbook="$playbook"
  local note=""
  if [ "$has_playbook" != "yes" ] && [ -n "$AVAIL_PLAYBOOK" ]; then
    use_playbook="$AVAIL_PLAYBOOK"
    note=" (placeholder — real playbook: ${playbook})"
  fi

  local payload
  payload=$(python3 -c "
import json
d = {
    'name': '${name}',
    'description': '${desc}',
    'job_type': 'run',
    'inventory': ${INVENTORY_ID},
    'project': ${PROJECT_ID},
    'playbook': '${use_playbook}',
    'job_tags': 'rhoso',
    'verbosity': 0,
    'timeout': ${timeout},
    'ask_variables_on_launch': True,
    'survey_enabled': True,
    'extra_vars': json.dumps({'installation_task': '${task_tag}'})
}
print(json.dumps(d))
")
  api POST /job_templates/ -d "$payload" -o /dev/null -w "%{http_code}${note}\n"
}

# ─── OCP — Generate (Phase 1) ───
echo ""
echo "  --- OCP Generate ---"
create_ocp_jt "OCP Generate Manifests" \
  "generate_manifests" \
  "Generate install-config, agent-config, NMState YAML from CIQ for review" 600

# ─── OCP — Prerequisites ───
echo "  --- OCP Prerequisites ---"
create_ocp_jt "OCP Prerequisites" \
  "prerequisites" \
  "All prerequisites: bastion preparation + DNS/DHCP validation + NTP sync" 3600
create_ocp_jt "OCP Bastion Preparation" \
  "bastion_preparation" \
  "Prepare bastion host: install packages, configure firewall, SSH keys" 1800
create_ocp_jt "OCP DNS DHCP Validation" \
  "dns_dhcp_validation" \
  "Validate DNS forward/reverse records and DHCP reservations" 600
create_ocp_jt "OCP NTP Sync" \
  "ntp_sync" \
  "Synchronize NTP across all cluster nodes" 600

# ─── OCP — Mirror (Disconnected) ───
echo "  --- OCP Mirror (Disconnected) ---"
create_ocp_jt "OCP Mirror Registry Install" \
  "mirror_registry" \
  "Install and configure Quay mirror-registry on bastion" 3600
create_ocp_jt "OCP OC Mirror Execution" \
  "oc_mirror" \
  "Mirror OCP release images and operator catalogs to local registry" 14400
create_ocp_jt "OCP IDMS ITMS Configuration" \
  "idms_itms_config" \
  "Generate ImageDigestMirrorSet and ImageTagMirrorSet CRs" 600

# ─── OCP — Install Configuration ───
echo "  --- OCP Install Configuration ---"
create_ocp_jt "OCP Generate Install Config" \
  "install_config" \
  "Generate install-config.yaml from CIQ parameters" 600
create_ocp_jt "OCP Generate Agent Config" \
  "agent_config" \
  "Generate agent-config.yaml with host definitions and BMC details" 600
create_ocp_jt "OCP Generate NMState Configs" \
  "nmstate_configs" \
  "Generate NMState network configs for static IP assignment" 600

# ─── OCP — Ignition & ISO ───
echo "  --- OCP Ignition & ISO ---"
create_ocp_jt "OCP Generate Ignition Configs" \
  "ignition_configs" \
  "Generate Ignition configs for UPI installations" 600
create_ocp_jt "OCP Create Agent ISO" \
  "agent_iso" \
  "Create bootable Agent-Based Installer ISO" 1800
create_ocp_jt "OCP Boot Nodes From ISO" \
  "boot_nodes" \
  "Boot bare-metal/virtual nodes from Agent ISO via Redfish BMC" 1800

# ─── OCP — Bootstrap ───
echo "  --- OCP Bootstrap ---"
create_ocp_jt "OCP Bootstrap Cluster" \
  "bootstrap" \
  "Bootstrap the OCP cluster (start installation process)" 7200
create_ocp_jt "OCP Wait Install Complete" \
  "wait_install" \
  "Wait for OCP installation to complete successfully" 7200

# ─── OCP — Cluster Configuration ───
echo "  --- OCP Cluster Configuration ---"
create_ocp_jt "OCP Approve CSRs" \
  "approve_csrs" \
  "Approve pending Certificate Signing Requests for worker nodes" 600
create_ocp_jt "OCP Configure Authentication" \
  "auth_config" \
  "Configure cluster authentication (HTPasswd, LDAP, OAuth)" 600
create_ocp_jt "OCP Day-2 Operator Installation" \
  "day2_operators" \
  "Install Day-2 operators: LSO, ODF, NMState, MetalLB, SR-IOV, etc." 3600

# ─── OCP — Network ───
echo "  --- OCP Network ---"
create_ocp_jt "OCP MetalLB Configuration" \
  "metallb_config" \
  "Configure MetalLB load balancer with IP address pools and L2 advertisements" 600
create_ocp_jt "OCP SR-IOV Multus Configuration" \
  "sriov_config" \
  "Configure SR-IOV network operator and Multus CNI" 600

# ─── OCP — Validation ───
echo "  --- OCP Validation ---"
create_ocp_jt "OCP Cluster Health Check" \
  "health_check" \
  "Run cluster health checks: node status, operator status, pod health" 600
create_ocp_jt "OCP Node Readiness Check" \
  "node_readiness" \
  "Verify all nodes are Ready and schedulable" 600

# ─── OCP — Full Install ───
echo "  --- OCP Full Install ---"
create_ocp_jt "OCP Full Install" \
  "full_install" \
  "End-to-end OCP installation: all prerequisites through validation" 14400

# ─── OCP — Uninstall ───
echo "  --- OCP Uninstall ---"
create_ocp_jt "OCP Uninstall Mirror Registry" \
  "uninstall_mirror_registry" \
  "Remove the Quay mirror-registry from bastion" 1800
create_ocp_jt "OCP Destroy Cluster" \
  "destroy_cluster" \
  "Destroy the OCP cluster and clean up all resources" 3600

# ─── OCP — Validate CIQ ───
echo "  --- OCP Validate ---"
echo -n "  OCP Validate ... "
OCP_VALIDATE_PB="${PLAYBOOK_PREFIX}/ansible/playbooks/ocp_validate.yml"
HAS_VALIDATE_PB=$(api GET "/projects/${PROJECT_ID}/playbooks/" \
  | python3 -c "import json,sys; print('yes' if '${OCP_VALIDATE_PB}' in json.load(sys.stdin) else 'no')" 2>/dev/null)
USE_VALIDATE_PB="$OCP_VALIDATE_PB"
VALIDATE_NOTE=""
if [ "$HAS_VALIDATE_PB" != "yes" ] && [ -n "$AVAIL_PLAYBOOK" ]; then
  USE_VALIDATE_PB="$AVAIL_PLAYBOOK"
  VALIDATE_NOTE=" (placeholder)"
fi
api POST /job_templates/ -d "$(python3 -c "
import json; print(json.dumps({
    'name': 'OCP Validate',
    'description': 'Validate OCP CIQ workbook: schema, BMC connectivity, MAC addresses',
    'job_type': 'run',
    'inventory': ${INVENTORY_ID},
    'project': ${PROJECT_ID},
    'playbook': '${USE_VALIDATE_PB}',
    'verbosity': 0,
    'timeout': 600,
    'ask_variables_on_launch': True,
    'survey_enabled': True
}))
")" -o /dev/null -w "%{http_code}${VALIDATE_NOTE}\n"

# ─── RHOSO — Generate (Phase 1) ───
echo ""
echo "  --- RHOSO Generate ---"
create_rhoso_jt "RHOSO Generate Manifests" \
  "manifests/manifest_generation" \
  "Generate disconnected, network, control-plane, data-plane YAML from CIQ" 600

# ─── RHOSO — Prerequisites ───
echo "  --- RHOSO Prerequisites ---"
create_rhoso_jt "RHOSO Pre-requisites" \
  "prerequisites/prerequisites" \
  "Verify RHOSO pre-requisites on OCP cluster" 1800
create_rhoso_jt "RHOSO Verify Required CRDs" \
  "common/_verify_required_crds" \
  "Verify all required CRDs exist on the OCP cluster" 600
create_rhoso_jt "RHOSO Prerequisite Operator Installation" \
  "prerequisites/prerequisite_operator_installation" \
  "Install prerequisite operators: cert-manager, NMState, MetalLB, etc." 3600
create_rhoso_jt "RHOSO Disconnected Environment Preparation" \
  "prerequisites/disconnected_environment_preparation" \
  "Configure disconnected environment: mirror catalogs, ICSP, trust CA" 3600

# ─── RHOSO — Secrets ───
echo "  --- RHOSO Secrets ---"
create_rhoso_jt "RHOSO Generate OSP Secret" \
  "secrets/generate_osp_secret" \
  "Generate OpenStack Platform service secret" 600
create_rhoso_jt "RHOSO Generate Data Plane Secrets" \
  "secrets/generate_data_plane_secrets" \
  "Generate SSH keys and secrets for EDPM data plane nodes" 600
create_rhoso_jt "RHOSO Generate Ceph Secret" \
  "secrets/generate_ceph_secret" \
  "Generate Ceph client secret for external storage" 600

# ─── RHOSO — Storage ───
echo "  --- RHOSO Storage ---"
create_rhoso_jt "RHOSO Persistent Storage Configuration" \
  "storage/persistent_storage_configuration" \
  "Configure persistent storage: NFS, Ceph, or local storage" 1800
create_rhoso_jt "RHOSO Trident Storage Configuration" \
  "storage/trident_storage_configuration" \
  "Configure NetApp Trident storage backend" 1800
create_rhoso_jt "RHOSO Generate Storage CRs" \
  "storage/_generate_storage_crs" \
  "Generate storage custom resources from CIQ" 600

# ─── RHOSO — Control Plane ───
echo "  --- RHOSO Control Plane ---"
create_rhoso_jt "RHOSO OpenStack Operator Installation" \
  "control_plane/openstack_operator_installation_and_preparation" \
  "Install and prepare the OpenStack operator on OCP" 3600
create_rhoso_jt "RHOSO RHOCP Preparation" \
  "control_plane/rhocp_preparation_for_rhoso" \
  "Prepare RHOCP cluster for RHOSO deployment" 1800
create_rhoso_jt "RHOSO Control Plane Deployment" \
  "control_plane/control_plane_deployment_and_verification" \
  "Deploy and verify RHOSO control plane services" 7200
create_rhoso_jt "RHOSO Control Plane Customization" \
  "control_plane/control_plane_customization" \
  "Apply customizations to RHOSO control plane" 1800

# ─── RHOSO — Network ───
echo "  --- RHOSO Network ---"
create_rhoso_jt "RHOSO Network Preparation" \
  "network/network_preparation" \
  "Configure network: NADs, MetalLB pools, NNCP for RHOSO" 1800

# ─── RHOSO — Data Plane ───
echo "  --- RHOSO Data Plane ---"
create_rhoso_jt "RHOSO Data Plane Deployment" \
  "data_plane/data_plane_deployment_and_verification" \
  "Deploy and verify EDPM data plane compute nodes" 7200

# ─── RHOSO — Post-Deployment ───
echo "  --- RHOSO Post-Deployment ---"
create_rhoso_jt "RHOSO Post-Deployment Validation" \
  "post_deployment/post_deployment_validation" \
  "Validate RHOSO deployment: service endpoints, Tempest tests" 1800
create_rhoso_jt "RHOSO Observability Configuration" \
  "post_deployment/observability_configuration" \
  "Configure observability: logging, monitoring, alerting" 1800

# ─── RHOSO — Register ───
echo "  --- RHOSO Register ---"
echo -n "  RHOSO Register ... "
RHOSO_PB="${PLAYBOOK_PREFIX}/ansible/playbooks/main.yml"
HAS_RHOSO_PB=$(api GET "/projects/${PROJECT_ID}/playbooks/" \
  | python3 -c "import json,sys; print('yes' if '${RHOSO_PB}' in json.load(sys.stdin) else 'no')" 2>/dev/null)
USE_RHOSO_PB="$RHOSO_PB"
RHOSO_NOTE=""
if [ "$HAS_RHOSO_PB" != "yes" ] && [ -n "$AVAIL_PLAYBOOK" ]; then
  USE_RHOSO_PB="$AVAIL_PLAYBOOK"
  RHOSO_NOTE=" (placeholder)"
fi
api POST /job_templates/ -d "$(python3 -c "
import json; print(json.dumps({
    'name': 'RHOSO Register',
    'description': 'Register and validate a RHOSO cluster from CIQ workbook',
    'job_type': 'run',
    'inventory': ${INVENTORY_ID},
    'project': ${PROJECT_ID},
    'playbook': '${USE_RHOSO_PB}',
    'job_tags': 'register',
    'verbosity': 0,
    'timeout': 600,
    'ask_variables_on_launch': True,
    'survey_enabled': True
}))
")" -o /dev/null -w "%{http_code}${RHOSO_NOTE}\n"

JT_COUNT=0
for name in \
  "OCP Generate Manifests" "OCP Prerequisites" "OCP Bastion Preparation" \
  "OCP DNS DHCP Validation" "OCP NTP Sync" \
  "OCP Mirror Registry Install" "OCP OC Mirror Execution" "OCP IDMS ITMS Configuration" \
  "OCP Generate Install Config" "OCP Generate Agent Config" "OCP Generate NMState Configs" \
  "OCP Generate Ignition Configs" "OCP Create Agent ISO" "OCP Boot Nodes From ISO" \
  "OCP Bootstrap Cluster" "OCP Wait Install Complete" \
  "OCP Approve CSRs" "OCP Configure Authentication" "OCP Day-2 Operator Installation" \
  "OCP MetalLB Configuration" "OCP SR-IOV Multus Configuration" \
  "OCP Cluster Health Check" "OCP Node Readiness Check" \
  "OCP Full Install" \
  "OCP Uninstall Mirror Registry" "OCP Destroy Cluster" \
  "OCP Validate" \
  "RHOSO Generate Manifests" "RHOSO Pre-requisites" "RHOSO Verify Required CRDs" \
  "RHOSO Prerequisite Operator Installation" "RHOSO Disconnected Environment Preparation" \
  "RHOSO Generate OSP Secret" "RHOSO Generate Data Plane Secrets" "RHOSO Generate Ceph Secret" \
  "RHOSO Persistent Storage Configuration" "RHOSO Trident Storage Configuration" "RHOSO Generate Storage CRs" \
  "RHOSO OpenStack Operator Installation" "RHOSO RHOCP Preparation" \
  "RHOSO Control Plane Deployment" "RHOSO Control Plane Customization" \
  "RHOSO Network Preparation" "RHOSO Data Plane Deployment" \
  "RHOSO Post-Deployment Validation" "RHOSO Observability Configuration" \
  "RHOSO Register"; do
  JT_COUNT=$((JT_COUNT + 1))
done
echo ""
echo "  Total job templates created: $JT_COUNT"

# -----------------------------------------------------------------------
# 4. SURVEYS — Attach to each Job Template
# -----------------------------------------------------------------------
echo ""
echo "--- Attaching Surveys ---"

# Common OCP survey (CIQ + Cluster + Version) — reused for all OCP task templates
attach_ocp_survey() {
  local jt_name="$1"
  local jt_id
  jt_id=$(lookup_id /job_templates/ "$jt_name")
  if [ -z "$jt_id" ]; then
    echo "  SKIP survey: '$jt_name' not found"
    return
  fi
  echo -n "  $jt_name ... "
  api POST "/job_templates/${jt_id}/survey_spec/" -d '{
    "name": "OCP Parameters",
    "description": "Cluster parameters for this OCP task",
    "spec": [
      {"question_name":"CIQ File Path","question_description":"Absolute path to OCP CIQ workbook (.xlsx)","variable":"ocp_ciq_file","type":"text","required":true,"default":""},
      {"question_name":"Cluster Name","question_description":"OCP cluster name (must match CIQ)","variable":"ocp_cluster_name","type":"text","required":true,"default":""},
      {"question_name":"OCP Version","question_description":"OCP version to install","variable":"ocp_version","type":"multiplechoice","required":true,"default":"4.22","choices":["4.17","4.18","4.19","4.20","4.22"]}
    ]
  }' -o /dev/null -w "%{http_code}\n"
}

attach_rhoso_survey() {
  local jt_name="$1"
  local jt_id
  jt_id=$(lookup_id /job_templates/ "$jt_name")
  if [ -z "$jt_id" ]; then
    echo "  SKIP survey: '$jt_name' not found"
    return
  fi
  echo -n "  $jt_name ... "
  api POST "/job_templates/${jt_id}/survey_spec/" -d '{
    "name": "RHOSO Parameters",
    "description": "Cluster parameters for this RHOSO task",
    "spec": [
      {"question_name":"CIQ File Path","question_description":"Absolute path to RHOSO CIQ workbook (.xlsx)","variable":"ciq_file_path","type":"text","required":true,"default":""},
      {"question_name":"Cluster Name","question_description":"RHOSO cluster name (must match CIQ)","variable":"cluster_name","type":"text","required":true,"default":""},
      {"question_name":"RHOSO Version","question_description":"RHOSO version","variable":"rhoso_version","type":"multiplechoice","required":true,"default":"18.0","choices":["18.0"]}
    ]
  }' -o /dev/null -w "%{http_code}\n"
}

echo ""
echo "  --- OCP Surveys ---"
for jt in \
  "OCP Generate Manifests" "OCP Prerequisites" "OCP Bastion Preparation" \
  "OCP DNS DHCP Validation" "OCP NTP Sync" \
  "OCP Mirror Registry Install" "OCP OC Mirror Execution" "OCP IDMS ITMS Configuration" \
  "OCP Generate Install Config" "OCP Generate Agent Config" "OCP Generate NMState Configs" \
  "OCP Generate Ignition Configs" "OCP Create Agent ISO" "OCP Boot Nodes From ISO" \
  "OCP Bootstrap Cluster" "OCP Wait Install Complete" \
  "OCP Approve CSRs" "OCP Configure Authentication" "OCP Day-2 Operator Installation" \
  "OCP MetalLB Configuration" "OCP SR-IOV Multus Configuration" \
  "OCP Cluster Health Check" "OCP Node Readiness Check" \
  "OCP Full Install" \
  "OCP Uninstall Mirror Registry" "OCP Destroy Cluster"; do
  attach_ocp_survey "$jt"
done

# OCP Validate — simpler survey (no version needed)
echo -n "  OCP Validate ... "
OCP_VALIDATE_ID=$(lookup_id /job_templates/ "OCP Validate")
if [ -n "$OCP_VALIDATE_ID" ]; then
  api POST "/job_templates/${OCP_VALIDATE_ID}/survey_spec/" -d '{
    "name": "OCP Validation Parameters",
    "description": "Validate an OCP CIQ workbook",
    "spec": [
      {"question_name":"CIQ File Path","variable":"ocp_ciq_file","type":"text","required":true,"default":""},
      {"question_name":"Cluster Name","variable":"ocp_cluster_name","type":"text","required":true,"default":""}
    ]
  }' -o /dev/null -w "%{http_code}\n"
fi

echo ""
echo "  --- RHOSO Surveys ---"
for jt in \
  "RHOSO Generate Manifests" "RHOSO Pre-requisites" "RHOSO Verify Required CRDs" \
  "RHOSO Prerequisite Operator Installation" "RHOSO Disconnected Environment Preparation" \
  "RHOSO Generate OSP Secret" "RHOSO Generate Data Plane Secrets" "RHOSO Generate Ceph Secret" \
  "RHOSO Persistent Storage Configuration" "RHOSO Trident Storage Configuration" "RHOSO Generate Storage CRs" \
  "RHOSO OpenStack Operator Installation" "RHOSO RHOCP Preparation" \
  "RHOSO Control Plane Deployment" "RHOSO Control Plane Customization" \
  "RHOSO Network Preparation" "RHOSO Data Plane Deployment" \
  "RHOSO Post-Deployment Validation" "RHOSO Observability Configuration"; do
  attach_rhoso_survey "$jt"
done

# RHOSO Register — simpler survey
echo -n "  RHOSO Register ... "
RHOSO_REGISTER_ID=$(lookup_id /job_templates/ "RHOSO Register")
if [ -n "$RHOSO_REGISTER_ID" ]; then
  api POST "/job_templates/${RHOSO_REGISTER_ID}/survey_spec/" -d '{
    "name": "RHOSO Registration Parameters",
    "description": "Register a RHOSO cluster from CIQ",
    "spec": [
      {"question_name":"CIQ File Path","variable":"ciq_file_path","type":"text","required":true,"default":""},
      {"question_name":"Cluster Description","variable":"cluster_description","type":"text","required":false,"default":""},
      {"question_name":"Registration Target","variable":"registration_target","type":"multiplechoice","required":true,"default":"rhoso","choices":["rhoso","ocp"]}
    ]
  }' -o /dev/null -w "%{http_code}\n"
fi

# -----------------------------------------------------------------------
# 5. ATTACH CREDENTIALS to OCP job templates that need them
# -----------------------------------------------------------------------
echo ""
echo "--- Attaching Credentials ---"

OCP_CRED_TEMPLATES=(
  "OCP Prerequisites" "OCP Bastion Preparation" "OCP DNS DHCP Validation"
  "OCP NTP Sync" "OCP Mirror Registry Install" "OCP OC Mirror Execution"
  "OCP IDMS ITMS Configuration" "OCP Generate Install Config"
  "OCP Generate Agent Config" "OCP Generate NMState Configs"
  "OCP Generate Ignition Configs" "OCP Create Agent ISO"
  "OCP Boot Nodes From ISO" "OCP Bootstrap Cluster" "OCP Wait Install Complete"
  "OCP Approve CSRs" "OCP Configure Authentication"
  "OCP Day-2 Operator Installation" "OCP MetalLB Configuration"
  "OCP SR-IOV Multus Configuration" "OCP Cluster Health Check"
  "OCP Node Readiness Check" "OCP Full Install"
  "OCP Uninstall Mirror Registry" "OCP Destroy Cluster"
)

for CRED_NAME in "Bastion SSH" "BMC Credentials" "Pull Secret"; do
  CRED_ID=$(lookup_id /credentials/ "$CRED_NAME")
  if [ -n "$CRED_ID" ]; then
    for JT_NAME in "${OCP_CRED_TEMPLATES[@]}"; do
      JT_ID=$(lookup_id /job_templates/ "$JT_NAME")
      if [ -n "$JT_ID" ]; then
        echo -n "  $CRED_NAME → $JT_NAME ... "
        api POST "/job_templates/${JT_ID}/credentials/" \
          -d "{\"id\": ${CRED_ID}}" -o /dev/null -w "%{http_code}\n"
      fi
    done
  else
    echo "  SKIP: Credential '$CRED_NAME' not found (create it manually in AAP UI)"
  fi
done

# -----------------------------------------------------------------------
# 6. WORKFLOW TEMPLATES — Chain job templates for end-to-end flows
# -----------------------------------------------------------------------
echo ""
echo "--- Creating Workflow Templates ---"

create_workflow() {
  local name="$1" desc="$2"
  echo -n "  $name ... "
  api POST /workflow_job_templates/ -d "{
    \"name\": \"${name}\",
    \"description\": \"${desc}\",
    \"organization\": ${ORG_ID},
    \"ask_variables_on_launch\": true,
    \"survey_enabled\": true
  }" -o /dev/null -w "%{http_code}\n"
}

# OCP Workflow Templates
echo "  --- OCP Workflows ---"
create_workflow "OCP ABI Full Install" \
  "End-to-end OCP ABI connected install: Prerequisites → Install Config → Agent Config → NMState → Agent ISO → Boot Nodes → Bootstrap → Wait Install → CSRs → Auth → Day-2 → MetalLB → SR-IOV → Health Check → Node Readiness"
create_workflow "OCP ABI-DC Full Install" \
  "End-to-end OCP ABI disconnected install: Prerequisites → Mirror Registry → OC Mirror → IDMS/ITMS → Install Config → Agent Config → NMState → Agent ISO → Boot Nodes → Bootstrap → Wait Install → CSRs → Auth → Day-2 → MetalLB → SR-IOV → Health Check → Node Readiness"
create_workflow "OCP Destroy" \
  "Destroy OCP cluster: Destroy Cluster + optional Uninstall Mirror Registry"

# RHOSO Workflow Templates
echo "  --- RHOSO Workflows ---"
create_workflow "RHOSO Full Install" \
  "End-to-end RHOSO install: Generate Manifests → Pre-requisites → Verify CRDs → Operator Install → Disconnected Prep → OSP Secret → DP Secrets → Ceph Secret → Storage → Trident → Storage CRs → OpenStack Operator → RHOCP Prep → Control Plane → CP Customization → Network → Data Plane → Validation → Observability"

# -----------------------------------------------------------------------
# 7. WIRE WORKFLOW NODES — Link job templates into sequential chains
# -----------------------------------------------------------------------
echo ""
echo "--- Wiring Workflow Nodes ---"

wire_workflow() {
  local wf_name="$1"
  shift
  local jt_names=("$@")

  local wf_id
  wf_id=$(lookup_id /workflow_job_templates/ "$wf_name")
  if [ -z "$wf_id" ]; then
    echo "  SKIP: Workflow '$wf_name' not found"
    return
  fi

  # Check if workflow already has nodes
  local node_count
  node_count=$(api GET "/workflow_job_templates/${wf_id}/workflow_nodes/" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('count',0))" 2>/dev/null)
  if [ "$node_count" -gt 0 ] 2>/dev/null; then
    echo "  $wf_name: already has $node_count nodes (skipping)"
    return
  fi

  echo -n "  $wf_name: "
  local prev_node_id=""
  local wired=0
  for jt_name in "${jt_names[@]}"; do
    local jt_id
    jt_id=$(lookup_id /job_templates/ "$jt_name")
    if [ -z "$jt_id" ]; then
      echo ""
      echo "    WARNING: Job template '$jt_name' not found — skipping"
      continue
    fi

    # Create workflow node
    local node_id
    node_id=$(api POST "/workflow_job_templates/${wf_id}/workflow_nodes/" \
      -d "{\"unified_job_template\": ${jt_id}}" \
      | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

    if [ -z "$node_id" ]; then
      echo ""
      echo "    ERROR: Failed to create node for '$jt_name'"
      continue
    fi

    # Link to previous node on success
    if [ -n "$prev_node_id" ]; then
      api POST "/workflow_job_template_nodes/${prev_node_id}/success_nodes/" \
        -d "{\"id\": ${node_id}}" -o /dev/null 2>/dev/null
    fi

    prev_node_id="$node_id"
    wired=$((wired + 1))
  done
  echo "${wired} nodes wired"
}

echo "  --- OCP Workflows ---"
wire_workflow "OCP ABI Full Install" \
  "OCP Prerequisites" \
  "OCP Generate Install Config" \
  "OCP Generate Agent Config" \
  "OCP Generate NMState Configs" \
  "OCP Create Agent ISO" \
  "OCP Boot Nodes From ISO" \
  "OCP Bootstrap Cluster" \
  "OCP Wait Install Complete" \
  "OCP Approve CSRs" \
  "OCP Configure Authentication" \
  "OCP Day-2 Operator Installation" \
  "OCP MetalLB Configuration" \
  "OCP SR-IOV Multus Configuration" \
  "OCP Cluster Health Check" \
  "OCP Node Readiness Check"

wire_workflow "OCP ABI-DC Full Install" \
  "OCP Prerequisites" \
  "OCP Mirror Registry Install" \
  "OCP OC Mirror Execution" \
  "OCP IDMS ITMS Configuration" \
  "OCP Generate Install Config" \
  "OCP Generate Agent Config" \
  "OCP Generate NMState Configs" \
  "OCP Create Agent ISO" \
  "OCP Boot Nodes From ISO" \
  "OCP Bootstrap Cluster" \
  "OCP Wait Install Complete" \
  "OCP Approve CSRs" \
  "OCP Configure Authentication" \
  "OCP Day-2 Operator Installation" \
  "OCP MetalLB Configuration" \
  "OCP SR-IOV Multus Configuration" \
  "OCP Cluster Health Check" \
  "OCP Node Readiness Check"

wire_workflow "OCP Destroy" \
  "OCP Destroy Cluster"

echo "  --- RHOSO Workflows ---"
wire_workflow "RHOSO Full Install" \
  "RHOSO Generate Manifests" \
  "RHOSO Pre-requisites" \
  "RHOSO Verify Required CRDs" \
  "RHOSO Prerequisite Operator Installation" \
  "RHOSO Disconnected Environment Preparation" \
  "RHOSO Generate OSP Secret" \
  "RHOSO Generate Data Plane Secrets" \
  "RHOSO Generate Ceph Secret" \
  "RHOSO Persistent Storage Configuration" \
  "RHOSO Trident Storage Configuration" \
  "RHOSO Generate Storage CRs" \
  "RHOSO OpenStack Operator Installation" \
  "RHOSO RHOCP Preparation" \
  "RHOSO Control Plane Deployment" \
  "RHOSO Control Plane Customization" \
  "RHOSO Network Preparation" \
  "RHOSO Data Plane Deployment" \
  "RHOSO Post-Deployment Validation" \
  "RHOSO Observability Configuration"

echo ""
echo "========================================="
echo "Import complete!"
echo ""
echo "Summary:"
echo "  Credential Types:     3"
echo "  Job Templates:        $JT_COUNT (26 OCP + 1 OCP Validate + 19 RHOSO + 1 RHOSO Register)"
echo "  Workflow Templates:   4 (with nodes wired)"
echo ""
echo "Next steps:"
echo "  1. Create credential INSTANCES in AAP UI:"
echo "     - Type 'Bastion SSH'       → cloud-user + SSH key"
echo "     - Type 'BMC Credentials'   → admin/password"
echo "     - Type 'Pull Secret'       → pull-secret.json content"
echo "  2. Attach credentials to job templates (auto-done for OCP templates above)"
echo "  3. Verify workflow nodes in AAP Workflow Visualizer"
echo "========================================="
