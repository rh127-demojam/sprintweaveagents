/**
 * Shared RHOSO path-based input file fields (multipart form keys).
 * Field names MUST match backend INPUT_FILE_SPECS keys in input_files.py.
 * Schema v1.4 — 8 fields (added netapp_config, multipath_config, ceph_keyring).
 */
export const RHOSO_INPUT_FILE_FIELDS = [
  {
    field: 'kubeconfig',
    label: 'Kubeconfig',
    parameter: 'Kubeconfig Path',
    accept: '.kubeconfig,.yaml,.yml,text/plain,*/*',
    help: 'RHOCP cluster-admin kubeconfig',
    recommended: true,
  },
  {
    field: 'pull_secret',
    label: 'Pull secret',
    parameter: 'Pull Secret Path',
    accept: '.json,application/json',
    help: 'Registry pull-secret JSON',
    recommended: true,
  },
  {
    field: 'mirror_pull_secret',
    label: 'Mirror pull secret',
    parameter: 'Mirror Pull Secret Path',
    accept: '.json,application/json',
    help: 'Disconnected mirror auth (optional)',
    recommended: false,
  },
  {
    field: 'mirror_ca',
    label: 'Mirror registry CA',
    parameter: 'Mirror Registry CA Path',
    accept: '.crt,.pem,.cer,text/plain',
    help: 'Disconnected mirror CA certificate (optional)',
    recommended: false,
  },
  {
    field: 'dataplane_ssh_key',
    label: 'Data plane SSH private key',
    parameter: 'Data Plane SSH Private Key Path',
    accept: '*/*',
    help: 'SSH private key for EDPM Ansible',
    recommended: true,
  },
  {
    field: 'netapp_config',
    label: 'NetApp / Trident config',
    parameter: 'Trident Secret Name',
    accept: '.json,application/json,*/*',
    help: 'NetApp ONTAP credentials for Trident CSI storage backend (optional)',
    recommended: false,
  },
  {
    field: 'multipath_config',
    label: 'Multipath config',
    parameter: 'Multipath Config Secret Name',
    accept: '.conf,text/plain,*/*',
    help: 'Multipath configuration for NetApp ONTAP iSCSI/FC LUNs (optional)',
    recommended: false,
  },
  {
    field: 'ceph_keyring',
    label: 'Ceph client keyring',
    parameter: 'Ceph Client Key Path',
    accept: '*/*',
    help: 'Ceph client keyring for external Ceph integration (optional)',
    recommended: false,
  },
];
