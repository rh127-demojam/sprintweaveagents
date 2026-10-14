import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import ExecutionTable from './ExecutionTable';
import InstallationLogModal from './InstallationLogModal';
import ManifestArtifactsPanel from './ManifestArtifactsPanel';
import OcpTaskProgress from './OcpTaskProgress';

const OCP_VERSIONS = ['4.17', '4.18', '4.19', '4.20'];

const OCP_GENERATE_TASK = 'OCP Generate Manifests';

/**
 * Deployment tasks that apply to the cluster.
 * Order and names MUST match backend OCP_INSTALLATION_TASK_TAGS keys.
 */
const OCP_DEPLOY_TASKS = [
  // Prerequisites (combined)
  'OCP Prerequisites',
  // Mirror (disconnected)
  'OCP Mirror Registry Install',
  'OCP OC Mirror Execution',
  'OCP IDMS ITMS Configuration',
  // Install configuration
  'OCP Generate Install Config',
  'OCP Generate Agent Config',
  'OCP Generate NMState Configs',
  // Ignition & ISO
  'OCP Generate Ignition Configs',
  'OCP Create Agent ISO',
  'OCP Boot Nodes From ISO',
  // Bootstrap
  'OCP Bootstrap Cluster',
  'OCP Wait Install Complete',
  // Cluster configuration
  'OCP Approve CSRs',
  'OCP Configure Authentication',
  'OCP Day-2 Operator Installation',
  // Network
  'OCP MetalLB Configuration',
  'OCP SR-IOV Multus Configuration',
  // Validation
  'OCP Cluster Health Check',
  'OCP Node Readiness Check',
  // Full install
  'OCP Full Install',
];

const OCP_UNINSTALL_TASKS = [
  'OCP Uninstall Mirror Registry',
  'OCP Destroy Cluster',
];

const TASKS_USING_REVIEWED_MANIFESTS = new Set([
  'OCP Generate Install Config',
  'OCP Generate Agent Config',
  'OCP Generate NMState Configs',
  'OCP Generate Ignition Configs',
  'OCP Create Agent ISO',
]);

function upsertExecution(list, execution) {
  const index = list.findIndex((item) => item.id === execution.id);
  if (index === -1) return [execution, ...list];
  const next = [...list];
  next[index] = execution;
  return next;
}

export default function OcpInstallation() {
  const navigate = useNavigate();
  const { clusterId: routeClusterId } = useParams();
  const [ocpClusters, setOcpClusters] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [loadingClusters, setLoadingClusters] = useState(true);
  const [loadingExecutions, setLoadingExecutions] = useState(true);
  const [clusterError, setClusterError] = useState('');
  const [selectedCluster, setSelectedCluster] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedTasks, setSelectedTasks] = useState([]);
  const [selectedUninstallTasks, setSelectedUninstallTasks] = useState([]);
  const [reRenderManifests, setReRenderManifests] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [running, setRunning] = useState(false);
  const [logExecution, setLogExecution] = useState(null);
  const [commandLogExecution, setCommandLogExecution] = useState(null);
  const [artifactRefresh, setArtifactRefresh] = useState(0);

  const selectedClusterRecord = useMemo(
    () => ocpClusters.find((c) => c.cluster_name === selectedCluster) || null,
    [ocpClusters, selectedCluster]
  );

  const loadExecutions = useCallback(async (clusterName) => {
    setLoadingExecutions(true);
    try {
      const data = await api.getOcpInstallations(clusterName || undefined);
      setExecutions(data.executions || []);
    } catch (err) {
      setError((prev) => prev || err.message);
    } finally {
      setLoadingExecutions(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadOcpClusters() {
      setLoadingClusters(true);
      setClusterError('');
      try {
        const data = await api.getClusters('ocp');
        if (!cancelled) {
          setOcpClusters(data.clusters || []);
        }
      } catch (err) {
        if (!cancelled) {
          setClusterError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoadingClusters(false);
        }
      }
    }

    loadOcpClusters();
    loadExecutions();
    return () => {
      cancelled = true;
    };
  }, [loadExecutions]);

  useEffect(() => {
    if (routeClusterId && ocpClusters.length > 0 && !selectedCluster) {
      const match = ocpClusters.find((c) => c.id === routeClusterId);
      if (match) {
        setSelectedCluster(match.cluster_name);
      }
    }
  }, [routeClusterId, ocpClusters, selectedCluster]);

  useEffect(() => {
    if (!logExecution) return;
    const updated = executions.find((item) => item.id === logExecution.id);
    if (updated && updated.status !== logExecution.status) {
      setLogExecution(updated);
    }
  }, [executions, logExecution]);

  const hasInProgress = executions.some((ex) => ex.status === 'in_progress');

  useEffect(() => {
    if (!hasInProgress || running) return undefined;
    const intervalId = setInterval(
      () => loadExecutions(selectedCluster || undefined),
      2000
    );
    return () => clearInterval(intervalId);
  }, [hasInProgress, running, loadExecutions, selectedCluster]);

  const handleTaskToggle = (task) => {
    setSelectedTasks((prev) =>
      prev.includes(task) ? prev.filter((t) => t !== task) : [...prev, task]
    );
  };

  const handleSelectAllTasks = () => {
    if (selectedTasks.length === OCP_DEPLOY_TASKS.length) {
      setSelectedTasks([]);
    } else {
      setSelectedTasks([...OCP_DEPLOY_TASKS]);
    }
  };

  const runInstallation = async ({ tasks, executionMode, reRender = false, successHint }) => {
    setError('');
    setSuccess('');

    if (!selectedCluster) {
      setError('Please select a registered OCP cluster.');
      return;
    }
    if (!selectedVersion) {
      setError('Please select an OCP version.');
      return;
    }
    if (!tasks.length) {
      setError('Please select at least one task to execute.');
      return;
    }

    setRunning(true);
    try {
      const data = await api.runOcpInstallation({
        cluster_name: selectedCluster,
        ocp_version: selectedVersion,
        tasks,
        execution_mode: executionMode,
        re_render_manifests: reRender,
      });

      // Backend returns 202 with execution records — task runs in background.
      // Merge returned executions so the pipeline shows them immediately.
      if (data.executions) {
        setExecutions((prev) => {
          let next = [...prev];
          for (const execution of data.executions) {
            next = upsertExecution(next, execution);
          }
          return next;
        });
      }

      setSuccess(
        successHint ||
          data.message ||
          `Started ${tasks.length} task(s). Progress updates automatically.`
      );

      // The useEffect polling (every 2s when hasInProgress) picks up
      // status changes — no long-lived HTTP connection needed.
      if (executionMode === 'generate') {
        document.getElementById('ocp-review-manifests')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }
    } catch (err) {
      setError(err.message);
      await loadExecutions(selectedCluster);
      setArtifactRefresh((n) => n + 1);
    } finally {
      setRunning(false);
    }
  };

  const handleGenerate = async () => {
    await runInstallation({
      tasks: [OCP_GENERATE_TASK],
      executionMode: 'generate',
      successHint:
        'OCP manifests generated. Review or download them below, then select deployment tasks.',
    });
  };

  const handleDeploy = async (e) => {
    e.preventDefault();
    await runInstallation({
      tasks: selectedTasks,
      executionMode: reRenderManifests ? 'full' : 'deploy',
      reRender: reRenderManifests,
    });
  };

  const handleUninstallToggle = (task) => {
    setSelectedUninstallTasks((prev) =>
      prev.includes(task) ? prev.filter((t) => t !== task) : [...prev, task]
    );
  };

  const handleUninstall = async (e) => {
    e.preventDefault();
    if (!window.confirm(`Are you sure you want to run: ${selectedUninstallTasks.map(t => t.replace(/^OCP /, '')).join(', ')}?\n\nThis action cannot be undone.`)) {
      return;
    }
    await runInstallation({
      tasks: selectedUninstallTasks,
      executionMode: 'deploy',
      reRender: false,
    });
  };

  const usesReviewed = selectedTasks.some((t) => TASKS_USING_REVIEWED_MANIFESTS.has(t));

  return (
    <>
      <div className="section-card register-form-card rhoso-installation-page">
        <h3>OCP Installation</h3>
        <p className="register-help">
          Workflow: <strong>1) Generate</strong> install-config, agent-config, and NMState YAML
          from CIQ &rarr; <strong>2) Review</strong> (view/download) &rarr;{' '}
          <strong>3) Deploy</strong> selected tasks.
          <br />
          Supports ABI, IPI-BM, UPI-BM, ABI-DC, and SNO installation methods.
        </p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        {clusterError && <div className="error-message">{clusterError}</div>}

        {/* Cluster selector */}
        <div className="form-group">
          <label htmlFor="ocp_cluster">OCP Cluster</label>
          <select
            id="ocp_cluster"
            value={selectedCluster}
            onChange={(e) => setSelectedCluster(e.target.value)}
            disabled={loadingClusters || running || ocpClusters.length === 0}
          >
            <option value="">
              {loadingClusters
                ? 'Loading OCP clusters...'
                : ocpClusters.length === 0
                  ? 'No registered OCP clusters'
                  : 'Select an OCP cluster'}
            </option>
            {ocpClusters.map((cluster) => (
              <option key={cluster.id} value={cluster.cluster_name}>
                {cluster.cluster_name}
              </option>
            ))}
          </select>
          {!loadingClusters && ocpClusters.length === 0 && (
            <p className="field-hint">
              Register an OCP cluster first from{' '}
              <button
                type="button"
                className="btn-link"
                onClick={() => navigate('/register-ocp')}
              >
                Register OCP Cluster
              </button>{' '}
              using the OCP CIQ workbook.
            </p>
          )}
        </div>

        {/* Version selector */}
        <div className="form-group">
          <label htmlFor="ocp_version">OCP Version</label>
          <select
            id="ocp_version"
            value={selectedVersion}
            onChange={(e) => setSelectedVersion(e.target.value)}
            disabled={running}
          >
            <option value="">Select OCP version</option>
            {OCP_VERSIONS.map((version) => (
              <option key={version} value={version}>
                OCP {version}
              </option>
            ))}
          </select>
        </div>

        {/* Phase 1: Generate */}
        <section className="rhoso-phase">
          <h4>1. Generate manifests for review</h4>
          <p className="field-hint">
            Renders install-config.yaml, agent-config.yaml, NMState configs, and
            disconnected CRs from CIQ into the cluster artifacts directory. Does not
            apply anything to the cluster.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleGenerate}
            disabled={loadingClusters || running || hasInProgress || ocpClusters.length === 0}
          >
            {running || hasInProgress ? 'Running...' : 'Generate OCP Manifests'}
          </button>
        </section>

        {/* Phase 2: Review */}
        <section className="rhoso-phase" id="ocp-review-manifests">
          <h4>2. Review rendered manifests</h4>
          <p className="field-hint">
            After generate completes, use <strong>View</strong> / <strong>Download</strong> below.
          </p>
          <ManifestArtifactsPanel
            clusterId={selectedClusterRecord?.id}
            clusterName={selectedCluster}
            listArtifacts={api.getClusterArtifacts}
            getArtifact={api.getClusterArtifact}
            downloadArtifact={api.downloadClusterArtifact}
            downloadAllArtifacts={api.downloadAllClusterArtifacts}
            refreshToken={artifactRefresh}
          />
        </section>

        {/* Phase 3: Deploy */}
        <section className="rhoso-phase">
          <h4>3. Deploy using reviewed manifests</h4>
          <p className="field-hint">
            Select deployment tasks. For config generation tasks,
            CPAT applies the files you reviewed (no re-render) unless you enable re-render below.
          </p>

          <form onSubmit={handleDeploy}>
            <div className="form-group">
              <div className="task-select-header">
                <label htmlFor="ocp_installation_tasks">Deployment tasks</label>
                <button
                  type="button"
                  className="btn-link task-select-all"
                  onClick={handleSelectAllTasks}
                  disabled={running}
                >
                  {selectedTasks.length === OCP_DEPLOY_TASKS.length ? 'Clear all' : 'Select all'}
                </button>
              </div>
              <div className="task-checkbox-list" id="ocp_installation_tasks">
                {OCP_DEPLOY_TASKS.map((task) => (
                  <label key={task} className="task-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedTasks.includes(task)}
                      onChange={() => handleTaskToggle(task)}
                      disabled={running}
                    />
                    <span>
                      {task.replace(/^OCP /, '')}
                      {TASKS_USING_REVIEWED_MANIFESTS.has(task) ? (
                        <em className="task-uses-artifacts"> · uses reviewed YAML</em>
                      ) : null}
                    </span>
                  </label>
                ))}
              </div>
              {selectedTasks.length > 0 && (
                <p className="field-hint">{selectedTasks.length} task(s) selected</p>
              )}
            </div>

            <label className="task-checkbox-item re-render-option">
              <input
                type="checkbox"
                checked={reRenderManifests}
                onChange={(e) => setReRenderManifests(e.target.checked)}
                disabled={running}
              />
              <span>
                Re-render templates before apply
                {usesReviewed
                  ? ' (overrides reviewed files for config-generation tasks)'
                  : ''}
              </span>
            </label>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loadingClusters || running || hasInProgress || ocpClusters.length === 0}
              >
                {running || hasInProgress ? 'Running Deployment...' : 'Run OCP Deployment'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate('/')}
                disabled={running}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>

        {/* Phase 4: Uninstall */}
        <section className="rhoso-phase">
          <h4>4. Uninstall / Cleanup</h4>
          <p className="field-hint">
            Remove deployed components. Use with caution — these actions cannot be undone.
          </p>

          <form onSubmit={handleUninstall}>
            <div className="form-group">
              <div className="task-checkbox-list">
                {OCP_UNINSTALL_TASKS.map((task) => (
                  <label key={task} className="task-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedUninstallTasks.includes(task)}
                      onChange={() => handleUninstallToggle(task)}
                      disabled={running}
                    />
                    <span>{task.replace(/^OCP /, '')}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-danger"
                disabled={loadingClusters || running || hasInProgress || selectedUninstallTasks.length === 0 || ocpClusters.length === 0}
              >
                {running || hasInProgress ? 'Running...' : 'Run Uninstall'}
              </button>
            </div>
          </form>
        </section>
      </div>

      <OcpTaskProgress executions={executions} />

      <ExecutionTable
        title="OCP Installation Executions"
        emptyMessage="No OCP installation executions yet. Generate or deploy to see progress here."
        executions={executions}
        loading={loadingExecutions}
        onViewLog={setLogExecution}
        onViewCommandLog={setCommandLogExecution}
        taskColumnLabel="OCP Task"
        versionHeader="OCP Version"
      />

      <InstallationLogModal
        execution={logExecution}
        open={Boolean(logExecution)}
        onClose={() => setLogExecution(null)}
        getLog={api.getOcpInstallationLog}
        downloadLog={api.downloadOcpInstallationLog}
        logTitle="OCP Installation Log"
      />

      <InstallationLogModal
        execution={commandLogExecution}
        open={Boolean(commandLogExecution)}
        onClose={() => setCommandLogExecution(null)}
        getLog={api.getOcpCommandLog}
        downloadLog={api.downloadOcpCommandLog}
        logTitle="Command Output Log"
      />
    </>
  );
}
