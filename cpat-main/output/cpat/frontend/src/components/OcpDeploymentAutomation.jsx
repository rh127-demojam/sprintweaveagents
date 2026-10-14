/**
 * OCP Deployment Automation — Register & overview page.
 * Allows uploading an OCP CIQ workbook to register an OCP cluster.
 * Streams live Ansible validation logs during registration (like RHOSO).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { OCP_INPUT_FILE_FIELDS } from '../ocpInputFiles';
import RegistrationLogModal from './RegistrationLogModal';

export default function OcpDeploymentAutomation() {
  const navigate = useNavigate();
  const logContentRef = useRef(null);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [registering, setRegistering] = useState(false);
  const [ciqFile, setCiqFile] = useState(null);
  const [description, setDescription] = useState('');
  const [reregister, setReregister] = useState(false);
  const [logClusterId, setLogClusterId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [scrollRecentLog, setScrollRecentLog] = useState(false);
  const [parsedInfo, setParsedInfo] = useState(null);

  useEffect(() => {
    if (!scrollRecentLog || !logContentRef.current) return;
    logContentRef.current.scrollTop = logContentRef.current.scrollHeight;
  }, [logs, scrollRecentLog]);

  const loadClusters = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getClusters('ocp');
      setClusters(data.clusters || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadClusters();
  }, [loadClusters]);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLogs([]);
    setParsedInfo(null);
    setScrollRecentLog(false);

    if (!ciqFile) {
      setError('Please select an OCP CIQ workbook (.xlsx).');
      return;
    }

    setRegistering(true);
    try {
      const formData = new FormData();
      formData.append('ciq_file', ciqFile);
      formData.append('description', description);
      if (reregister) formData.append('reregister', 'true');

      const data = await api.registerOcpCluster(formData, (event) => {
        if (event.type === 'info') {
          if (event.cluster_name) {
            setParsedInfo({
              cluster_name: event.cluster_name,
              cluster_type: event.cluster_type || 'OCP',
            });
          }
          setLogs((prev) => [...prev, event.message]);
        } else if (event.type === 'log') {
          setLogs((prev) => [...prev, event.line]);
        }
      });

      setSuccess(data.message || 'OCP cluster registered successfully. All validations passed.');
      setCiqFile(null);
      setDescription('');
      await loadClusters();
    } catch (err) {
      setError(err.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleDelete = async (clusterId, clusterName) => {
    if (!window.confirm(`Delete OCP cluster '${clusterName}'? This cannot be undone.`)) return;
    try {
      await api.deleteCluster(clusterId);
      setSuccess(`Cluster '${clusterName}' deleted.`);
      await loadClusters();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      {/* Registration form */}
      <div className="section-card register-form-card">
        <h3>Register OCP Cluster</h3>
        <p className="register-help">
          Upload an OCP CIQ workbook to register a cluster. The workbook must
          contain an <code>ocp_details</code> table with <code>Type = OCP</code>.
          CPAT will run <strong>schema-based validation</strong> on every parameter,
          BMC host, NMState interface, and DNS record with live Ansible logs.
        </p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleRegister}>
          <div className="form-group">
            <label htmlFor="ocp_ciq_file">OCP CIQ Workbook (.xlsx)</label>
            <input
              type="file"
              id="ocp_ciq_file"
              accept=".xlsx"
              onChange={(e) => setCiqFile(e.target.files[0] || null)}
              disabled={registering}
            />
          </div>

          <div className="form-group">
            <label htmlFor="ocp_description">Description (optional)</label>
            <input
              type="text"
              id="ocp_description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Troshka lab OCP 4.20 ABI-DC disconnected"
              disabled={registering}
            />
          </div>

          <label className="task-checkbox-item">
            <input
              type="checkbox"
              checked={reregister}
              onChange={(e) => setReregister(e.target.checked)}
              disabled={registering}
            />
            <span>Re-register if cluster already exists</span>
          </label>

          {/* Live Ansible log panel */}
          {(registering || logs.length > 0) && (
            <div className="ansible-log-panel">
              <div className="ansible-log-header">
                <span>Ansible validation log</span>
                {parsedInfo && (
                  <span className="ansible-log-meta">
                    {parsedInfo.cluster_name} — {parsedInfo.cluster_type || 'OCP'}
                  </span>
                )}
                {registering && <span className="ansible-log-status">Running...</span>}
              </div>
              <pre ref={logContentRef} className="ansible-log-content">
                {logs.join('\n')}
              </pre>
              <div className="ansible-log-footer">
                <label className="tail-toggle">
                  <input
                    type="checkbox"
                    checked={scrollRecentLog}
                    onChange={(e) => setScrollRecentLog(e.target.checked)}
                  />
                  <span className="tail-toggle-label">Auto-scroll to latest</span>
                </label>
                {scrollRecentLog && (
                  <span className="tail-status">Following latest output</span>
                )}
              </div>
            </div>
          )}

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={registering || !ciqFile}
            >
              {registering ? 'Running Ansible...' : 'Register OCP Cluster'}
            </button>
          </div>
        </form>
      </div>

      {/* Registered clusters list */}
      <div className="section-card">
        <h3>Registered OCP Clusters</h3>
        {loading ? (
          <div className="loading">Loading clusters...</div>
        ) : clusters.length === 0 ? (
          <div className="empty-state">
            <p>No OCP clusters registered yet. Upload a CIQ workbook above.</p>
          </div>
        ) : (
          <table className="cluster-table">
            <thead>
              <tr>
                <th>Cluster Name</th>
                <th>CIQ File</th>
                <th>Description</th>
                <th>Status</th>
                <th>Registered</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clusters.map((cluster) => (
                <tr key={cluster.id}>
                  <td>
                    <strong>{cluster.cluster_name}</strong>
                  </td>
                  <td>{cluster.ciq_filename}</td>
                  <td>{cluster.description || '\u2014'}</td>
                  <td>
                    <span
                      className={
                        cluster.status === 'registered'
                          ? 'status-badge status-passed'
                          : cluster.status === 'validation_failed'
                            ? 'status-badge status-failed'
                            : 'status-badge'
                      }
                    >
                      {cluster.status === 'registered'
                        ? '✓ Validated'
                        : cluster.status === 'validation_failed'
                          ? '✗ Failed'
                          : cluster.status}
                    </span>
                  </td>
                  <td>{new Date(cluster.registered_at).toLocaleString()}</td>
                  <td>
                    {cluster.status === 'registered' && (
                      <>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() => navigate(`/ocp-installation/${cluster.id}`)}
                        >
                          Install
                        </button>
                        {' | '}
                      </>
                    )}
                    {cluster.has_registration_log && (
                      <>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() => setLogClusterId(cluster.id)}
                        >
                          Log
                        </button>
                        {' | '}
                      </>
                    )}
                    <button
                      type="button"
                      className="btn-link text-danger"
                      onClick={() => handleDelete(cluster.id, cluster.cluster_name)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Registration log modal */}
      {logClusterId && (
        <RegistrationLogModal
          cluster={clusters.find((c) => c.id === logClusterId)}
          open={Boolean(logClusterId)}
          onClose={() => setLogClusterId(null)}
        />
      )}

      {/* Input files reference */}
      <div className="section-card">
        <h3>OCP Input Files Reference</h3>
        <p className="register-help">
          These files are referenced by CIQ parameter paths and consumed during installation.
        </p>
        <table className="cluster-table">
          <thead>
            <tr>
              <th>File</th>
              <th>CIQ Parameter</th>
              <th>Required</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {OCP_INPUT_FILE_FIELDS.map((f) => (
              <tr key={f.field}>
                <td><strong>{f.label}</strong></td>
                <td><code>{f.parameter}</code></td>
                <td>{f.recommended ? 'Yes' : 'Optional'}</td>
                <td>{f.help}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
