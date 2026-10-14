import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import ExecutionTable from './ExecutionTable';
import InstallationLogModal from './InstallationLogModal';
import ManifestArtifactsPanel from './ManifestArtifactsPanel';

const RHOSO_VERSIONS = ['RHOSO 18.0'];

const RHOSO_GENERATE_TASK = 'Generate Manifests for Review';

/**
 * Deployment tasks that apply (and may consume reviewed manifests).
 * Order and names MUST match backend RHOSO_INSTALLATION_TASK_TAGS keys
 * (excluding 'Generate Manifests for Review').
 * Schema v1.4 — 18 deploy tasks (19 total with generate).
 */
const RHOSO_DEPLOY_TASKS = [
  // Pre-deployment checks
  'Pre-requisites',
  'Verify Required CRDs',
  // Operator & infrastructure preparation
  'Prerequisite Operator Installation',
  'Disconnected Environment Preparation',
  // Secret generation
  'Generate OSP Secret',
  'Generate Data Plane Secrets',
  'Generate Ceph Secret',
  // Storage (incl. Trident v1.4)
  'Persistent Storage Configuration',
  'Trident Storage Configuration',
  'Generate Storage CRs',
  // OpenStack operator & RHOCP preparation
  'OpenStack Operator Installation and Preparation',
  'RHOCP Preparation for RHOSO',
  // Network
  'Network Preparation',
  // Deployment & verification
  'Control Plane Deployment and Verification',
  'Control Plane Customization',
  'Data Plane Deployment and Verification',
  'Post-Deployment Validation',
  // Post-deployment configuration (v1.4)
  'Observability Configuration',
];

const TASKS_USING_REVIEWED_MANIFESTS = new Set([
  'Disconnected Environment Preparation',
  'Network Preparation',
  'Control Plane Deployment and Verification',
  'Data Plane Deployment and Verification',
]);

function upsertExecution(list, execution) {
  const index = list.findIndex((item) => item.id === execution.id);
  if (index === -1) return [execution, ...list];
  const next = [...list];
  next[index] = execution;
  return next;
}

export default function RhosoInstallation() {
  const navigate = useNavigate();
  const { clusterId: routeClusterId } = useParams();
  const [rhosoClusters, setRhosoClusters] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [loadingClusters, setLoadingClusters] = useState(true);
  const [loadingExecutions, setLoadingExecutions] = useState(true);
  const [clusterError, setClusterError] = useState('');
  const [selectedCluster, setSelectedCluster] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedTasks, setSelectedTasks] = useState([]);
  const [reRenderManifests, setReRenderManifests] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [running, setRunning] = useState(false);
  const [logExecution, setLogExecution] = useState(null);
  const [artifactRefresh, setArtifactRefresh] = useState(0);

  const selectedClusterRecord = useMemo(
    () => rhosoClusters.find((c) => c.cluster_name === selectedCluster) || null,
    [rhosoClusters, selectedCluster]
  );

  const loadExecutions = useCallback(async (clusterName) => {
    setLoadingExecutions(true);
    try {
      const data = await api.getRhosoInstallations(clusterName || undefined);
      setExecutions(data.executions || []);
    } catch (err) {
      setError((prev) => prev || err.message);
    } finally {
      setLoadingExecutions(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadRhosoClusters() {
      setLoadingClusters(true);
      setClusterError('');
      try {
        const data = await api.getClusters('rhoso');
        if (!cancelled) {
          setRhosoClusters(data.clusters || []);
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

    loadRhosoClusters();
    loadExecutions();
    return () => {
      cancelled = true;
    };
  }, [loadExecutions]);

  useEffect(() => {
    if (routeClusterId && rhosoClusters.length > 0 && !selectedCluster) {
      const match = rhosoClusters.find((c) => c.id === routeClusterId);
      if (match) {
        setSelectedCluster(match.cluster_name);
      }
    }
  }, [routeClusterId, rhosoClusters, selectedCluster]);

  useEffect(() => {
    if (!logExecution) return;
    const updated = executions.find((item) => item.id === logExecution.id);
    if (updated && updated.status !== logExecution.status) {
      setLogExecution(updated);
    }
  }, [executions, logExecution]);

  const hasInProgress = executions.some((execution) => execution.status === 'in_progress');

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
      prev.includes(task) ? prev.filter((item) => item !== task) : [...prev, task]
    );
  };

  const handleSelectAllTasks = () => {
    if (selectedTasks.length === RHOSO_DEPLOY_TASKS.length) {
      setSelectedTasks([]);
    } else {
      setSelectedTasks([...RHOSO_DEPLOY_TASKS]);
    }
  };

  const runInstallation = async ({ tasks, executionMode, reRender = false, successHint }) => {
    setError('');
    setSuccess('');

    if (!selectedCluster) {
      setError('Please select a registered RHOSO environment.');
      return;
    }
    if (!selectedVersion) {
      setError('Please select a RHOSO version.');
      return;
    }
    if (!tasks.length) {
      setError('Please select at least one task to execute.');
      return;
    }

    setRunning(true);
    try {
      const data = await api.runRhosoInstallation(
        {
          cluster_name: selectedCluster,
          rhoso_version: selectedVersion,
          tasks,
          execution_mode: executionMode,
          re_render_manifests: reRender,
        },
        (event) => {
          if (event.type === 'info' && event.executions) {
            setExecutions((prev) => {
              let next = [...prev];
              for (const execution of event.executions) {
                next = upsertExecution(next, execution);
              }
              return next;
            });
          } else if (event.type === 'task_start' && event.execution) {
            setExecutions((prev) => upsertExecution(prev, event.execution));
          } else if (event.type === 'task_complete' && event.execution) {
            setExecutions((prev) => upsertExecution(prev, event.execution));
          }
        }
      );

      setSuccess(successHint || data.message);
      await loadExecutions(selectedCluster);
      setArtifactRefresh((n) => n + 1);
      if (executionMode === 'generate') {
        document.getElementById('rhoso-review-manifests')?.scrollIntoView({
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
      tasks: [RHOSO_GENERATE_TASK],
      executionMode: 'generate',
      successHint:
        'Manifests generated. Review or download them below, then select deployment tasks.',
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

  const usesReviewed = selectedTasks.some((t) => TASKS_USING_REVIEWED_MANIFESTS.has(t));

  return (
    <>
      <div className="section-card register-form-card rhoso-installation-page">
        <h3>RHOSO Installation</h3>
        <p className="register-help">
          Workflow: <strong>1) Generate</strong> manifests from CIQ → <strong>2) Review</strong>{' '}
          (view/download) → <strong>3) Deploy</strong> selected tasks using the reviewed files.
          Tasks that apply YAML from artifacts (Disconnected, Network, Control Plane, Data Plane)
          skip re-rendering unless you opt in below.
        </p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        {clusterError && <div className="error-message">{clusterError}</div>}

        <div className="form-group">
          <label htmlFor="rhoso_cluster">RHOSO Environment</label>
          <select
            id="rhoso_cluster"
            value={selectedCluster}
            onChange={(e) => setSelectedCluster(e.target.value)}
            disabled={loadingClusters || running || rhosoClusters.length === 0}
          >
            <option value="">
              {loadingClusters
                ? 'Loading RHOSO environments...'
                : rhosoClusters.length === 0
                  ? 'No registered RHOSO environments'
                  : 'Select a RHOSO environment'}
            </option>
            {rhosoClusters.map((cluster) => (
              <option key={cluster.id} value={cluster.cluster_name}>
                {cluster.cluster_name}
              </option>
            ))}
          </select>
          {!loadingClusters && rhosoClusters.length === 0 && (
            <p className="field-hint">
              Register a RHOSO environment first from{' '}
              <button
                type="button"
                className="btn-link"
                onClick={() => navigate('/register-cluster')}
              >
                Register Cluster
              </button>{' '}
              using the RHOSO CIQ template.
            </p>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="rhoso_version">RHOSO Version</label>
          <select
            id="rhoso_version"
            value={selectedVersion}
            onChange={(e) => setSelectedVersion(e.target.value)}
            disabled={running}
          >
            <option value="">Select RHOSO version</option>
            {RHOSO_VERSIONS.map((version) => (
              <option key={version} value={version}>
                {version}
              </option>
            ))}
          </select>
        </div>

        <section className="rhoso-phase">
          <h4>1. Generate manifests for review</h4>
          <p className="field-hint">
            Renders disconnected (if applicable), network, control-plane, and data-plane YAML from
            CIQ into the cluster artifacts directory. Does not apply anything to the cluster.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleGenerate}
            disabled={loadingClusters || running || rhosoClusters.length === 0}
          >
            {running ? 'Running…' : 'Generate Manifests for Review'}
          </button>
        </section>

        <section className="rhoso-phase" id="rhoso-review-manifests">
          <h4>2. Review rendered manifests</h4>
          <p className="field-hint">
            After generate completes, use <strong>View</strong> / <strong>Download</strong> below
            (scroll here if needed). Select the RHOSO environment first.
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

        <section className="rhoso-phase">
          <h4>3. Deploy using reviewed manifests</h4>
          <p className="field-hint">
            Select deployment tasks. For Network / Control Plane / Data Plane / Disconnected,
            CPAT applies the files you reviewed (no re-render) unless you enable re-render below.
          </p>

          <form onSubmit={handleDeploy}>
            <div className="form-group">
              <div className="task-select-header">
                <label htmlFor="rhoso_installation_tasks">Deployment tasks</label>
                <button
                  type="button"
                  className="btn-link task-select-all"
                  onClick={handleSelectAllTasks}
                  disabled={running}
                >
                  {selectedTasks.length === RHOSO_DEPLOY_TASKS.length ? 'Clear all' : 'Select all'}
                </button>
              </div>
              <div className="task-checkbox-list" id="rhoso_installation_tasks">
                {RHOSO_DEPLOY_TASKS.map((task) => (
                  <label key={task} className="task-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedTasks.includes(task)}
                      onChange={() => handleTaskToggle(task)}
                      disabled={running}
                    />
                    <span>
                      {task}
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
                  ? ' (overrides reviewed files for template-based tasks)'
                  : ''}
              </span>
            </label>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loadingClusters || running || rhosoClusters.length === 0}
              >
                {running ? 'Running Deployment…' : 'Run Deployment'}
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
      </div>

      <ExecutionTable
        title="Installation Executions"
        emptyMessage="No RHOSO installation executions yet. Generate or deploy to see progress here."
        executions={executions}
        loading={loadingExecutions}
        onViewLog={setLogExecution}
        versionHeader="RHOSO Version"
      />

      <InstallationLogModal
        execution={logExecution}
        open={Boolean(logExecution)}
        onClose={() => setLogExecution(null)}
        getLog={api.getRhosoInstallationLog}
        downloadLog={api.downloadRhosoInstallationLog}
        logTitle="RHOSO Installation Log"
      />
    </>
  );
}
