/**
 * OCP task progress indicator — shows the ordered task pipeline
 * with status badges for each step.
 */

const OCP_TASK_GROUPS = [
  {
    label: 'Prerequisites',
    tasks: [
      'OCP Bastion Preparation',
      'OCP DNS DHCP Validation',
      'OCP NTP Sync',
    ],
  },
  {
    label: 'Mirror (Disconnected)',
    tasks: [
      'OCP Mirror Registry Install',
      'OCP OC Mirror Execution',
      'OCP IDMS ITMS Configuration',
    ],
  },
  {
    label: 'Install Configuration',
    tasks: [
      'OCP Generate Install Config',
      'OCP Generate Agent Config',
      'OCP Generate NMState Configs',
    ],
  },
  {
    label: 'Ignition & ISO',
    tasks: [
      'OCP Generate Ignition Configs',
      'OCP Create Agent ISO',
    ],
  },
  {
    label: 'Bootstrap',
    tasks: [
      'OCP Bootstrap Cluster',
      'OCP Wait Install Complete',
    ],
  },
  {
    label: 'Cluster Configuration',
    tasks: [
      'OCP Approve CSRs',
      'OCP Configure Authentication',
      'OCP Day-2 Operator Installation',
    ],
  },
  {
    label: 'Network',
    tasks: [
      'OCP MetalLB Configuration',
      'OCP SR-IOV Multus Configuration',
    ],
  },
  {
    label: 'Validation',
    tasks: [
      'OCP Cluster Health Check',
      'OCP Node Readiness Check',
    ],
  },
];

function statusIcon(status) {
  if (status === 'complete') return '\u2714';
  if (status === 'failed') return '\u2718';
  if (status === 'in_progress') return '\u25CB';
  return '\u2500';
}

export default function OcpTaskProgress({ executions = [] }) {
  const executionMap = {};
  for (const ex of executions) {
    if (!executionMap[ex.task_name]) {
      executionMap[ex.task_name] = ex;
    }
  }

  if (executions.length === 0) return null;

  return (
    <div className="section-card">
      <h4>OCP Installation Pipeline</h4>
      <div className="ocp-task-pipeline">
        {OCP_TASK_GROUPS.map((group) => {
          const groupTasks = group.tasks.filter((t) => executionMap[t]);
          if (groupTasks.length === 0) return null;

          return (
            <div key={group.label} className="ocp-pipeline-group">
              <div className="ocp-pipeline-group-label">{group.label}</div>
              {groupTasks.map((taskName) => {
                const ex = executionMap[taskName];
                return (
                  <div
                    key={taskName}
                    className={`ocp-pipeline-step ocp-pipeline-step-${ex.status}`}
                  >
                    <span className="ocp-pipeline-icon">{statusIcon(ex.status)}</span>
                    <span className="ocp-pipeline-task">{taskName.replace(/^OCP /, '')}</span>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export { OCP_TASK_GROUPS };
