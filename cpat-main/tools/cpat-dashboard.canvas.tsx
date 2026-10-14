// @ts-nocheck
import {
  Stack,
  Row,
  H1,
  H2,
  Text,
  Button,
  Pill,
  Stat,
  Divider,
  Callout,
  CollapsibleSection,
  useHostTheme,
  useCanvasState,
  useCanvasAction,
} from "cursor/canvas";

type Artifact = {
  name: string;
  command: string;
  agent: string;
};

type Category = {
  id: string;
  label: string;
  artifacts: Artifact[];
};

const categories: Category[] = [
  {
    id: "ciq",
    label: "CIQ & Schema",
    artifacts: [
      { name: "CIQ Parameter Reference", command: "Generate CIQ parameter reference from @cpat", agent: "RHOSO DA" },
      { name: "CIQ Workbook (Sample + Template)", command: "Generate CIQ workbooks from @cpat", agent: "RHOSO DA" },
      { name: "CIQ Schema Code", command: "Generate CIQ schema code for @cpat", agent: "RHOSO DA" },
      { name: "Project-Specific CIQ from Artifacts", command: "Generate project CIQ from @input/rhoso/project-artifacts/", agent: "RHOSO DA" },
      { name: "CIQ Field Guide (GUIDELINES)", command: "Generate CIQ field guide from @cpat", agent: "RHOSO DA" },
      { name: "EDPM Topology Guide", command: "Generate EDPM topology guide for @cpat", agent: "RHOSO DA" },
    ],
  },
  {
    id: "analysis",
    label: "Analysis & Planning",
    artifacts: [
      { name: "PDF-to-CIQ Gap Matrix", command: "Generate RHOSO PDF gap matrix from @input/rhoso/docs/", agent: "RHOSO DA" },
      { name: "Lab Requirements Workbook", command: "Generate lab requirements from @input/rhoso/docs/", agent: "RHOSO DA" },
      { name: "Registration Input Files List", command: "List registration input files from @cpat", agent: "RHOSO DA" },
    ],
  },
  {
    id: "manifests",
    label: "Manifests & Templates",
    artifacts: [
      { name: "Manifest Catalog (15 Templates)", command: "Generate manifest catalog from @cpat", agent: "RHOSO Deployment Engineer" },
      { name: "Generate RHOSO Manifests", command: "Generate RHOSO manifests from CIQ", agent: "RHOSO Deployment Engineer" },
      { name: "Cluster Commands Reference", command: "Generate cluster commands for @cpat", agent: "RHOSO Deployment Engineer" },
    ],
  },
  {
    id: "workflow",
    label: "Workflow & Deployment",
    artifacts: [
      { name: "CPAT Deployment Workflow MoP", command: "Generate CPAT deployment workflow from @cpat", agent: "RHOSO Deployment Engineer" },
      { name: "Deployment Task Brief", command: "Generate RHOSO deployment task brief from @cpat", agent: "RHOSO Deployment Engineer" },
    ],
  },
  {
    id: "code",
    label: "Code Generation",
    artifacts: [
      { name: "CPAT Project Scaffold (Full)", command: "Scaffold CPAT project from @cpat", agent: "RHOSO Deployment Engineer" },
      { name: "Add Ansible Task/Template", command: "Add Ansible task to @cpat for [feature]", agent: "RHOSO Deployment Engineer" },
      { name: "Add Flask Route", command: "Add Flask route to @cpat for [feature]", agent: "RHOSO Deployment Engineer" },
      { name: "Add React Component", command: "Add React component to @cpat for [feature]", agent: "RHOSO Deployment Engineer" },
      { name: "CPAT Code Enhancement", command: "Add [feature] to CPAT codebase", agent: "RHOSO Deployment Engineer" },
    ],
  },
];

type PipelineStage = {
  abbrev: string;
  agent: string;
  output: string;
};

type PipelineDef = {
  id: string;
  name: string;
  command: string;
  stages: PipelineStage[];
  promoted?: boolean;
};

const AGENT_COLORS: Record<string, string> = {
  "RHOSO DA": "#dc2626",
  "RHOSO Deployment Engineer": "#b91c1c",
};

const pipelineDefs: PipelineDef[] = [
  {
    id: "rhoso-delivery",
    name: "RHOSO Delivery",
    command: "Run RHOSO delivery pipeline on @cpat",
    promoted: true,
    stages: [
      { abbrev: "RDA", agent: "RHOSO DA", output: "CIQ schema code, generators, CIQ workbooks (.xlsx)" },
      { abbrev: "RDE-1", agent: "RHOSO Deployment Engineer", output: "Ansible: 22 tasks, 15 templates, ~163 defaults, Ceph/HA/Watcher" },
      { abbrev: "RDE-2", agent: "RHOSO Deployment Engineer", output: "Backend: Flask API, 18 routes, CIQ parser" },
      { abbrev: "RDE-3", agent: "RHOSO Deployment Engineer", output: "Frontend: React 11 components, Vite, Nginx" },
      { abbrev: "RDE-4", agent: "RHOSO Deployment Engineer", output: "Docker: Dockerfile, entrypoint, bringup.sh" },
    ],
  },
  {
    id: "rhoso-da",
    name: "RHOSO Design Architect",
    command: "Run RHOSO DA pipeline on @cpat",
    promoted: true,
    stages: [
      { abbrev: "RDA", agent: "RHOSO DA", output: "CIQ schema code, all generators, all CIQ workbooks" },
    ],
  },
  {
    id: "rhoso-de",
    name: "RHOSO Deployment Engineer",
    command: "Run RHOSO DE pipeline on @cpat",
    promoted: true,
    stages: [
      { abbrev: "RDE-1", agent: "RHOSO Deployment Engineer", output: "Ansible: tasks, templates, defaults" },
      { abbrev: "RDE-2", agent: "RHOSO Deployment Engineer", output: "Backend: Flask, parser, runner" },
      { abbrev: "RDE-3", agent: "RHOSO Deployment Engineer", output: "Frontend: React, Vite, Nginx" },
      { abbrev: "RDE-4", agent: "RHOSO Deployment Engineer", output: "Docker, bringup, USAGE" },
    ],
  },
];

function ArtifactButton({ artifact }: { artifact: Artifact }) {
  const dispatch = useCanvasAction();
  const theme = useHostTheme();
  const agentColor = AGENT_COLORS[artifact.agent] || "#6b7280";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 12px",
        borderRadius: 6,
        background: theme.fill.quaternary,
        cursor: "pointer",
        gap: 8,
      }}
      onClick={() => dispatch({ type: "newComposerChat", userPrompt: artifact.command })}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <Text weight="medium">{artifact.name}</Text>
        <Text size="small" style={{ color: agentColor }}>{artifact.agent}</Text>
      </div>
      <div
        style={{
          width: 20,
          height: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 4,
          background: theme.accent.control,
          flexShrink: 0,
        }}
      >
        <svg width={10} height={10} viewBox="0 0 10 10" fill="none">
          <path d="M1 9L9 1M9 1H3M9 1V7" stroke={theme.text.onAccent} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

function StageNode({ stage }: { stage: PipelineStage }) {
  const color = AGENT_COLORS[stage.agent] || "#6b7280";
  return (
    <div
      title={`${stage.agent}\n→ ${stage.output}`}
      style={{
        padding: "4px 10px",
        borderRadius: 6,
        background: `${color}20`,
        border: `1.5px solid ${color}55`,
        fontSize: 11,
        fontWeight: 700,
        color: color,
        letterSpacing: "0.3px",
        whiteSpace: "nowrap",
        cursor: "default",
      }}
    >
      {stage.abbrev}
    </div>
  );
}

function FlowConnector() {
  const theme = useHostTheme();
  return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke={theme.text.tertiary} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PipelineFlow({ pipeline }: { pipeline: PipelineDef }) {
  const dispatch = useCanvasAction();
  const theme = useHostTheme();

  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: 10,
        background: theme.fill.quaternary,
        border: `1px solid ${theme.fill.tertiary}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Text weight="medium">{pipeline.name}</Text>
          {pipeline.promoted && <Pill active>Promoted</Pill>}
          <Text size="small" tone="tertiary">{pipeline.stages.length} {pipeline.stages.length === 1 ? "stage" : "stages"}</Text>
        </div>
        <Button variant="primary" onClick={() => dispatch({ type: "newComposerChat", userPrompt: pipeline.command })}>
          Launch
        </Button>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
        {pipeline.stages.map((stage, i) => (
          <div key={stage.abbrev + i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <StageNode stage={stage} />
            {i < pipeline.stages.length - 1 && <FlowConnector />}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CpatRhosoDashboard() {
  const theme = useHostTheme();
  const [selectedCategory, setSelectedCategory] = useCanvasState<string>("selectedCategory", "ciq");
  const dispatch = useCanvasAction();

  const activeCategory = categories.find(c => c.id === selectedCategory) || categories[0];
  const totalArtifacts = categories.reduce((sum, c) => sum + c.artifacts.length, 0);

  return (
    <Stack gap={20} style={{ padding: 20 }}>
      <Row align="center" justify="space-between">
        <div>
          <H1>CPAT — RHOSO Automation</H1>
          <Text tone="secondary">CIQ-to-Deployment Pipeline — Click to generate</Text>
        </div>
        <Row gap={12}>
          <Stat value="2" label="Agents" />
          <Stat value={String(totalArtifacts)} label="Artifacts" />
          <Stat value="3" label="Pipelines" />
        </Row>
      </Row>

      <Callout tone="info" title="Agents">
        RHOSO DA handles CIQ workbooks, schema, and analysis. RHOSO Deployment Engineer handles manifests, workflows, and CPAT code.
      </Callout>

      <Divider />

      <H2>Pipelines</H2>
      <Text size="small" tone="secondary">Agents execute left-to-right — hover any stage for details</Text>
      <Stack gap={10}>
        {pipelineDefs.map(p => (
          <PipelineFlow key={p.id + p.name} pipeline={p} />
        ))}
      </Stack>

      <Divider />

      <H2>Individual Artifacts</H2>
      <Row gap={6} wrap>
        <Pill active={selectedCategory === "all"} onClick={() => setSelectedCategory("all")}>
          All ({totalArtifacts})
        </Pill>
        {categories.map(cat => (
          <Pill
            key={cat.id}
            active={cat.id === selectedCategory}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.label}
          </Pill>
        ))}
      </Row>

      {selectedCategory === "all" ? (
        <Stack gap={14}>
          {categories.map(cat => (
            <Stack key={cat.id} gap={4}>
              <Text weight="medium" size="small" tone="secondary">{cat.label}</Text>
              {cat.artifacts.map(a => (
                <ArtifactButton key={a.name} artifact={a} />
              ))}
            </Stack>
          ))}
        </Stack>
      ) : (
        <Stack gap={6}>
          {activeCategory.artifacts.map(artifact => (
            <ArtifactButton key={artifact.name} artifact={artifact} />
          ))}
        </Stack>
      )}

      <Divider />

      <CollapsibleSection title="Schema Coverage" count={172}>
        <Stack gap={8}>
          <Text size="small" tone="secondary">CIQ Schema v1.3 — 15 tables, 172+ parameters</Text>
          {[
            { table: "rhoso_details", params: 11, desc: "Cluster identity, versions, deployment mode, FIPS" },
            { table: "rhoso_access", params: 3, desc: "Kubeconfig, API URL, pull secret" },
            { table: "rhoso_disconnected", params: 16, desc: "Mirror registry, IDMS/ITMS, CatalogSource" },
            { table: "rhoso_storage", params: 2, desc: "Storage class, backend type" },
            { table: "rhoso_ceph_storage", params: 12, desc: "Ceph external, FSID, mon host, pools, RGW" },
            { table: "rhoso_control_plane", params: 29, desc: "VIPs, operator config, DNS, TLS, messaging/notifications bus" },
            { table: "rhoso_edpm_network_config", params: 24, desc: "Bridge, bond, DPDK, NTP, tuning" },
            { table: "rhoso_data_plane", params: 13, desc: "SSH, secrets, subscription" },
            { table: "rhoso_services", params: 40, desc: "Enable flags, replicas, Watcher, HA operators" },
            { table: "rhoso_pv_sizing", params: 10, desc: "Galera, OVN, telemetry storage" },
            { table: "rhoso_cinder_backend", params: 8, desc: "NetApp driver, protocol, vserver" },
            { table: "rhoso_neutron_config", params: 5, desc: "MTU, OVN emit-need-to-frag, MAC binding age" },
            { table: "rhoso_networks", params: 16, desc: "Row table: CIDR, VLAN, MetalLB ranges" },
            { table: "rhoso_data_plane_nodes", params: 16, desc: "Row table: BMC, boot mode, NIC MACs" },
          ].map(t => (
            <Row key={t.table} align="center" justify="space-between" style={{ padding: "4px 8px", borderRadius: 4, background: theme.fill.quaternary }}>
              <div>
                <Text size="small" weight="medium">{t.table}</Text>
                <Text size="small" tone="tertiary">{t.desc}</Text>
              </div>
              <Pill>{t.params} params</Pill>
            </Row>
          ))}
        </Stack>
      </CollapsibleSection>

      <CollapsibleSection title="Manifest Templates" count={15}>
        <Stack gap={6}>
          {[
            { num: 1, name: "openstack_nncp.yaml.j2", cr: "NodeNetworkConfigurationPolicy", cond: "Always" },
            { num: 2, name: "openstack_nad.yaml.j2", cr: "NetworkAttachmentDefinition", cond: "Always" },
            { num: 3, name: "openstack_metallb.yaml.j2", cr: "IPAddressPool + L2Advertisement", cond: "Always" },
            { num: 4, name: "openstack_netconfig.yaml.j2", cr: "NetConfig", cond: "Always" },
            { num: 5, name: "openstack_control_plane.yaml.j2", cr: "OpenStackControlPlane", cond: "Always" },
            { num: 6, name: "edpm_network_config_template.j2", cr: "EDPM NIC config (os-net-config)", cond: "Always" },
            { num: 7, name: "openstack_dataplane_nodeset.yaml.j2", cr: "OpenStackDataPlaneNodeSet", cond: "Always" },
            { num: 8, name: "openstack_dataplane_deployment.yaml.j2", cr: "OpenStackDataPlaneDeployment", cond: "Always" },
            { num: 9, name: "openstack_baremetalhosts.yaml.j2", cr: "BareMetalHost + BMC Secrets", cond: "Unprovisioned" },
            { num: 10, name: "openstack_nmstate_secrets.yaml.j2", cr: "NMState provisioning Secrets", cond: "Unprovisioned" },
            { num: 11, name: "openstack_nova_cpu_pinning_cm.yaml.j2", cr: "Nova CPU pinning ConfigMap", cond: "CPU Dedicated Set" },
            { num: 12, name: "catalog_source.yaml.j2", cr: "CatalogSource", cond: "Disconnected" },
            { num: 13, name: "image_digest_mirror_set.yaml.j2", cr: "ImageDigestMirrorSet", cond: "Disconnected" },
            { num: 14, name: "image_tag_mirror_set.yaml.j2", cr: "ImageTagMirrorSet", cond: "Disconnected" },
            { num: 15, name: "operatorhub_disable_defaults.yaml.j2", cr: "OperatorHub patch", cond: "Disconnected" },
          ].map(t => (
            <Row key={t.num} align="center" justify="space-between" style={{ padding: "4px 8px", borderRadius: 4, background: theme.fill.quaternary }}>
              <div>
                <Text size="small" weight="medium">{t.num}. {t.name}</Text>
                <Text size="small" tone="tertiary">{t.cr}</Text>
              </div>
              <Pill tone={t.cond === "Always" ? undefined : "warning"}>{t.cond}</Pill>
            </Row>
          ))}
        </Stack>
      </CollapsibleSection>

      <Divider />

      <Callout tone="warning" title="Important">
        All artifacts are AI-generated and require human validation. Verify CIQ parameters, manifests, and deployment steps against RHOSO documentation before use in production.
      </Callout>

      <Text size="small" tone="tertiary">
        CPAT v1.3 — Schema v1.3 — 15 templates — 172+ params — 2 agents — 3 pipelines
      </Text>
    </Stack>
  );
}
