/**
 * OCP path-based input file fields (multipart form keys).
 * Field names MUST match backend OCP_INPUT_FILE_SPECS keys in app.py.
 */
export const OCP_INPUT_FILE_FIELDS = [
  {
    field: 'ocp_pull_secret',
    label: 'Pull secret',
    parameter: 'Pull Secret Path',
    accept: '.json,application/json',
    help: 'Red Hat / OpenShift pull-secret JSON',
    recommended: true,
  },
  {
    field: 'ocp_ssh_public_key',
    label: 'SSH public key',
    parameter: 'SSH Public Key Path',
    accept: '.pub,text/plain,*/*',
    help: 'SSH public key injected into CoreOS nodes',
    recommended: true,
  },
  {
    field: 'ocp_bastion_ssh_key',
    label: 'Bastion SSH private key',
    parameter: 'Bastion SSH Private Key Path',
    accept: '*/*',
    help: 'SSH private key for bastion access (e.g. id_ed25519). CPAT uses this to SSH into bastion for deployment tasks.',
    recommended: true,
  },
  {
    field: 'ocp_mirror_pull_secret',
    label: 'Mirror pull secret',
    parameter: 'Mirror Pull Secret Path',
    accept: '.json,application/json',
    help: 'Disconnected mirror registry credentials (optional)',
    recommended: false,
  },
  {
    field: 'ocp_mirror_ca',
    label: 'Mirror registry CA',
    parameter: 'Mirror Registry CA Path',
    accept: '.crt,.pem,.cer,text/plain',
    help: 'CA certificate for disconnected mirror registry (optional)',
    recommended: false,
  },
];
