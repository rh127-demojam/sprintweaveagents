# SprintWeave vs gold — comparison by agent/stage

- **Artifacts:** `sprintweave-6692295a-artifacts (1).zip` (96 files)
- **Gold:** `cpat-main/output/` (143 files)

Percent = `matched / gold files in scope` (same relative path, SHA256 match).
Path-only = file exists in zip but content differs.

## RDA-1 — RHOSO DA / Schema

| Metric | Count |
|--------|------:|
| Gold files in scope | 0 |
| In artifacts (any path) | 1 |
| Same path as gold | 0 |
| **Content match** | **0** (100%) |
| Path present, content differs | 0 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 1 |
| **Coverage (path)** | **100%** |

**Extra in zip (not in gold for this stage):**
- `ciq-generators/rhoso_ciq_schema.py`

<details><summary>All artifact files in this stage</summary>

- `ciq-generators/rhoso_ciq_schema.py` (50724 B)

</details>

## RDA-2 — RHOSO DA / Generator

| Metric | Count |
|--------|------:|
| Gold files in scope | 0 |
| In artifacts (any path) | 2 |
| Same path as gold | 0 |
| **Content match** | **0** (100%) |
| Path present, content differs | 0 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 2 |
| **Coverage (path)** | **100%** |

**Extra in zip (not in gold for this stage):**
- `ciq-generators/generate_rhoso_ciq_workbooks.py`
- `ciq-generators/requirements.txt`

<details><summary>All artifact files in this stage</summary>

- `ciq-generators/generate_rhoso_ciq_workbooks.py` (40660 B)
- `ciq-generators/requirements.txt` (9 B)

</details>

## RDA-3 — RHOSO DA / Workbooks

| Metric | Count |
|--------|------:|
| Gold files in scope | 0 |
| In artifacts (any path) | 2 |
| Same path as gold | 0 |
| **Content match** | **0** (100%) |
| Path present, content differs | 0 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 2 |
| **Coverage (path)** | **100%** |

**Extra in zip (not in gold for this stage):**
- `ciq-workbooks/rhoso/rhoso-ciq-template.xlsx`
- `ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx`

<details><summary>All artifact files in this stage</summary>

- `ciq-workbooks/rhoso/rhoso-ciq-template.xlsx` (24929 B)
- `ciq-workbooks/rhoso/sample-rhoso.ciq.xlsx` (25961 B)

</details>

## RDA-report — RHOSO DA / Reports

| Metric | Count |
|--------|------:|
| Gold files in scope | 1 |
| In artifacts (any path) | 2 |
| Same path as gold | 1 |
| **Content match** | **0** (0%) |
| Path present, content differs | 1 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 1 |
| **Coverage (path)** | **100%** |

**Same path, different content:**
- `pipeline-reports/rda/ciq-parameter-reference.md`

**Extra in zip (not in gold for this stage):**
- `pipeline-reports/rda/rda-report.md`

<details><summary>All artifact files in this stage</summary>

- `pipeline-reports/rda/ciq-parameter-reference.md` (897 B)
- `pipeline-reports/rda/rda-report.md` (897 B)

</details>

## RDE-1 — RHOSO DE / Ansible

| Metric | Count |
|--------|------:|
| Gold files in scope | 50 |
| In artifacts (any path) | 44 |
| Same path as gold | 40 |
| **Content match** | **0** (0%) |
| Path present, content differs | 40 |
| Missing vs gold | 10 |
| Extra (not in gold scope) | 4 |
| **Coverage (path)** | **80%** |

**Missing (gold has, zip does not):**
- `cpat/ansible/library/get_ciq_validation_schema.py`
- `cpat/ansible/library/parse_ciq.py`
- `cpat/ansible/module_utils/cpat_ciq_parser.py`
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/_generate_control_plane_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/data_plane/_generate_data_plane_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/storage/_generate_storage_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_lso.yaml.j2`
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_multipath_config.yaml.j2`
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_observability_operator.yaml.j2`
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_trident.yaml.j2`

**Same path, different content:**
- `cpat/ansible/module_utils/rhoso_ciq_schema.py`
- `cpat/ansible/playbooks/main.yml`
- `cpat/ansible/playbooks/roles/rhoso/defaults/main.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_load_ciq_context.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_validate_ciq.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_verify_required_crds.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/control_plane_customization.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/control_plane_deployment_and_verification.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/openstack_operator_installation_and_preparation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/rhocp_preparation_for_rhoso.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/data_plane/data_plane_deployment_and_verification.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/main.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_disconnected_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/manifest_generation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/network/network_preparation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/post_deployment/observability_configuration.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/post_deployment/post_deployment_validation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/disconnected_environment_preparation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/prerequisite_operator_installation.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/prerequisites.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_ceph_secret.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_data_plane_secrets.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_osp_secret.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/storage/persistent_storage_configuration.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/storage/trident_storage_configuration.yml`
- … +15 more

**Extra in zip (not in gold for this stage):**
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_control_plane_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_data_plane_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_network_crs.yml`
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_storage_crs.yml`

<details><summary>All artifact files in this stage</summary>

- `cpat/ansible/module_utils/rhoso_ciq_schema.py` (50724 B)
- `cpat/ansible/playbooks/main.yml` (315 B)
- `cpat/ansible/playbooks/roles/rhoso/defaults/main.yml` (11237 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_load_ciq_context.yml` (5025 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_validate_ciq.yml` (2708 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/common/_verify_required_crds.yml` (1326 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/control_plane_customization.yml` (1408 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/control_plane_deployment_and_verification.yml` (1273 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/openstack_operator_installation_and_preparation.yml` (1887 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/control_plane/rhocp_preparation_for_rhoso.yml` (1140 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/data_plane/data_plane_deployment_and_verification.yml` (3713 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/main.yml` (507 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_control_plane_crs.yml` (863 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_data_plane_crs.yml` (1528 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_disconnected_crs.yml` (1054 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_network_crs.yml` (817 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/_generate_storage_crs.yml` (1140 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/manifests/manifest_generation.yml` (1573 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/network/network_preparation.yml` (1971 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/post_deployment/observability_configuration.yml` (1271 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/post_deployment/post_deployment_validation.yml` (2550 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/disconnected_environment_preparation.yml` (2264 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/prerequisite_operator_installation.yml` (7566 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/prerequisites/prerequisites.yml` (1975 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_ceph_secret.yml` (1475 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_data_plane_secrets.yml` (3624 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/secrets/generate_osp_secret.yml` (2204 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/storage/persistent_storage_configuration.yml` (1620 B)
- `cpat/ansible/playbooks/roles/rhoso/tasks/storage/trident_storage_configuration.yml` (1520 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/catalog_source.yaml.j2` (559 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/edpm_network_config_template.j2` (1352 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/image_digest_mirror_set.yaml.j2` (406 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/image_tag_mirror_set.yaml.j2` (397 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_baremetalhosts.yaml.j2` (1239 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_control_plane.yaml.j2` (11929 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_dataplane_deployment.yaml.j2` (309 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_dataplane_nodeset.yaml.j2` (3563 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_metallb.yaml.j2` (887 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_nad.yaml.j2` (777 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_netconfig.yaml.j2` (782 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_nmstate_secrets.yaml.j2` (1138 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_nncp.yaml.j2` (1593 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/openstack_nova_cpu_pinning_cm.yaml.j2` (487 B)
- `cpat/ansible/playbooks/roles/rhoso/templates/operatorhub_disable_defaults.yaml.j2` (181 B)

</details>

## RDE-2 — RHOSO DE / Backend

| Metric | Count |
|--------|------:|
| Gold files in scope | 11 |
| In artifacts (any path) | 10 |
| Same path as gold | 10 |
| **Content match** | **0** (0%) |
| Path present, content differs | 10 |
| Missing vs gold | 1 |
| Extra (not in gold scope) | 0 |
| **Coverage (path)** | **91%** |

**Missing (gold has, zip does not):**
- `cpat/backend/ocp_ciq_parser.py`

**Same path, different content:**
- `cpat/backend/.gitignore`
- `cpat/backend/ansible_runner.py`
- `cpat/backend/app.py`
- `cpat/backend/ciq_parser.py`
- `cpat/backend/input_files.py`
- `cpat/backend/models.py`
- `cpat/backend/paths.py`
- `cpat/backend/requirements.txt`
- `cpat/backend/rhoso_ciq_schema.py`
- `cpat/backend/version.py`

<details><summary>All artifact files in this stage</summary>

- `cpat/backend/.gitignore` (126 B)
- `cpat/backend/ansible_runner.py` (8113 B)
- `cpat/backend/app.py` (32658 B)
- `cpat/backend/ciq_parser.py` (9637 B)
- `cpat/backend/input_files.py` (5401 B)
- `cpat/backend/models.py` (4395 B)
- `cpat/backend/paths.py` (4723 B)
- `cpat/backend/requirements.txt` (226 B)
- `cpat/backend/rhoso_ciq_schema.py` (2110 B)
- `cpat/backend/version.py` (304 B)

</details>

## RDE-3 — RHOSO DE / Frontend

| Metric | Count |
|--------|------:|
| Gold files in scope | 26 |
| In artifacts (any path) | 22 |
| Same path as gold | 20 |
| **Content match** | **0** (0%) |
| Path present, content differs | 20 |
| Missing vs gold | 6 |
| Extra (not in gold scope) | 2 |
| **Coverage (path)** | **77%** |

**Missing (gold has, zip does not):**
- `cpat/frontend/.gitignore`
- `cpat/frontend/public/redhat-logo-sidebar.svg`
- `cpat/frontend/public/redhat-logo.svg`
- `cpat/frontend/src/components/OcpInstallation.jsx`
- `cpat/frontend/src/components/OcpTaskProgress.jsx`
- `cpat/frontend/src/ocpInputFiles.js`

**Same path, different content:**
- `cpat/frontend/index.html`
- `cpat/frontend/nginx/default.conf`
- `cpat/frontend/package.json`
- `cpat/frontend/src/App.jsx`
- `cpat/frontend/src/api.js`
- `cpat/frontend/src/components/Dashboard.jsx`
- `cpat/frontend/src/components/ExecutionTable.jsx`
- `cpat/frontend/src/components/InputFilesModal.jsx`
- `cpat/frontend/src/components/InstallationLogModal.jsx`
- `cpat/frontend/src/components/Layout.jsx`
- `cpat/frontend/src/components/Login.jsx`
- `cpat/frontend/src/components/ManifestArtifactsPanel.jsx`
- `cpat/frontend/src/components/OcpDeploymentAutomation.jsx`
- `cpat/frontend/src/components/RegisterCluster.jsx`
- `cpat/frontend/src/components/RegistrationLogModal.jsx`
- `cpat/frontend/src/components/RhosoInstallation.jsx`
- `cpat/frontend/src/index.css`
- `cpat/frontend/src/main.jsx`
- `cpat/frontend/src/rhosoInputFiles.js`
- `cpat/frontend/vite.config.js`

**Extra in zip (not in gold for this stage):**
- `cpat/frontend/public/cpat-logo.svg`
- `cpat/frontend/public/rhoso-logo.svg`

<details><summary>All artifact files in this stage</summary>

- `cpat/frontend/index.html` (396 B)
- `cpat/frontend/nginx/default.conf` (1334 B)
- `cpat/frontend/package.json` (504 B)
- `cpat/frontend/public/cpat-logo.svg` (369 B)
- `cpat/frontend/public/rhoso-logo.svg` (280 B)
- `cpat/frontend/src/App.jsx` (2209 B)
- `cpat/frontend/src/api.js` (743 B)
- `cpat/frontend/src/components/Dashboard.jsx` (3817 B)
- `cpat/frontend/src/components/ExecutionTable.jsx` (2205 B)
- `cpat/frontend/src/components/InputFilesModal.jsx` (4015 B)
- `cpat/frontend/src/components/InstallationLogModal.jsx` (3122 B)
- `cpat/frontend/src/components/Layout.jsx` (2985 B)
- `cpat/frontend/src/components/Login.jsx` (3048 B)
- `cpat/frontend/src/components/ManifestArtifactsPanel.jsx` (5455 B)
- `cpat/frontend/src/components/OcpDeploymentAutomation.jsx` (633 B)
- `cpat/frontend/src/components/RegisterCluster.jsx` (5265 B)
- `cpat/frontend/src/components/RegistrationLogModal.jsx` (1903 B)
- `cpat/frontend/src/components/RhosoInstallation.jsx` (16820 B)
- `cpat/frontend/src/index.css` (14698 B)
- `cpat/frontend/src/main.jsx` (235 B)
- `cpat/frontend/src/rhosoInputFiles.js` (1410 B)
- `cpat/frontend/vite.config.js` (341 B)

</details>

## RDE-4 — RHOSO DE / Docker

| Metric | Count |
|--------|------:|
| Gold files in scope | 5 |
| In artifacts (any path) | 5 |
| Same path as gold | 5 |
| **Content match** | **0** (0%) |
| Path present, content differs | 5 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 0 |
| **Coverage (path)** | **100%** |

**Same path, different content:**
- `cpat/.dockerignore`
- `cpat/Dockerfile`
- `cpat/USAGE.md`
- `cpat/bringup.sh`
- `cpat/docker/entrypoint.sh`

<details><summary>All artifact files in this stage</summary>

- `cpat/.dockerignore` (1044 B)
- `cpat/Dockerfile` (4869 B)
- `cpat/USAGE.md` (18794 B)
- `cpat/bringup.sh` (8894 B)
- `cpat/docker/entrypoint.sh` (3193 B)

</details>

## RDE-report — RHOSO DE / Reports

| Metric | Count |
|--------|------:|
| Gold files in scope | 2 |
| In artifacts (any path) | 0 |
| Same path as gold | 0 |
| **Content match** | **0** (0%) |
| Path present, content differs | 0 |
| Missing vs gold | 2 |
| Extra (not in gold scope) | 0 |
| **Coverage (path)** | **0%** |

**Missing (gold has, zip does not):**
- `pipeline-reports/rde/cpat-source-inventory.md`
- `pipeline-reports/rde/manifest-catalog.md`

<details><summary>All artifact files in this stage</summary>


</details>

## extra — SprintWeave / OpenShift deploy extras

| Metric | Count |
|--------|------:|
| Gold files in scope | 0 |
| In artifacts (any path) | 5 |
| Same path as gold | 0 |
| **Content match** | **0** (100%) |
| Path present, content differs | 0 |
| Missing vs gold | 0 |
| Extra (not in gold scope) | 5 |
| **Coverage (path)** | **100%** |

**Extra in zip (not in gold for this stage):**
- `RDA.md`
- `RDE.md`
- `cpat-openshift/cpat-app.yaml`
- `cpat-openshift/deploy-cpat.sh`
- `summary.md`

<details><summary>All artifact files in this stage</summary>

- `RDA.md` (1913 B)
- `RDE.md` (9037 B)
- `cpat-openshift/cpat-app.yaml` (1750 B)
- `cpat-openshift/deploy-cpat.sh` (427 B)
- `summary.md` (11002 B)

</details>

## Unbucketed

- Gold not mapped to any stage above: **48**
  - `cpat/README-OCP.md`
  - `cpat/README-RHOSO.md`
  - `cpat/README.md`
  - `cpat/ansible.cfg`
  - `cpat/ansible/playbooks/ocp_install.yml`
  - `cpat/ansible/playbooks/roles/ocp/defaults/main.yml`
  - `cpat/ansible/playbooks/roles/ocp/meta/main.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/bootstrap/bootstrap_cluster.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/bootstrap/wait_bootstrap_complete.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/cluster_config/approve_csrs.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/cluster_config/configure_authentication.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/cluster_config/day2_operator_installation.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/common/_load_ciq_context.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/common/_validate_ciq.yml`
  - `cpat/ansible/playbooks/roles/ocp/tasks/common/_verify_prerequisites.yml`
- Artifacts not mapped: **3**
  - `cpat/ansible.cfg`
  - `cpat/data/.gitignore`
  - `cpat/data/README.md`

## Summary table

| Stage | Agent | Gold | Art | Match % | Path % |
|-------|-------|-----:|----:|--------:|-------:|
| RDA-1 | Schema | 0 | 1 | 0% | 0% |
| RDA-2 | Generator | 0 | 2 | 0% | 0% |
| RDA-3 | Workbooks | 0 | 2 | 0% | 0% |
| RDA-report | Reports | 1 | 2 | 0% | 100% |
| RDE-1 | Ansible | 50 | 44 | 0% | 80% |
| RDE-2 | Backend | 11 | 10 | 0% | 91% |
| RDE-3 | Frontend | 26 | 22 | 0% | 77% |
| RDE-4 | Docker | 5 | 5 | 0% | 100% |
| RDE-report | Reports | 2 | 0 | 0% | 0% |
| extra | OpenShift deploy extras | 0 | 5 | 0% | 0% |
