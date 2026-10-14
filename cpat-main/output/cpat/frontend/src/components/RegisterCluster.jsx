import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { RHOSO_INPUT_FILE_FIELDS } from '../rhosoInputFiles';

export default function RegisterCluster() {
  const navigate = useNavigate();
  const logContentRef = useRef(null);
  const [description, setDescription] = useState('');
  const [ciqFile, setCiqFile] = useState(null);
  const [inputFiles, setInputFiles] = useState({});
  const [reregister, setReregister] = useState(false);
  const [scrollRecentLog, setScrollRecentLog] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [parsedInfo, setParsedInfo] = useState(null);

  useEffect(() => {
    if (!scrollRecentLog || !logContentRef.current) return;
    logContentRef.current.scrollTop = logContentRef.current.scrollHeight;
  }, [logs, scrollRecentLog]);

  const handleInputFileChange = (field, file) => {
    setInputFiles((prev) => {
      const next = { ...prev };
      if (file) next[field] = file;
      else delete next[field];
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLogs([]);
    setParsedInfo(null);
    setScrollRecentLog(false);

    if (!ciqFile) {
      setError('Please upload a CIQ (Customer Information Questionnaire) .xlsx file.');
      return;
    }

    if (!ciqFile.name.toLowerCase().endsWith('.xlsx')) {
      setError('CIQ file must be an .xlsx workbook.');
      return;
    }

    const formData = new FormData();
    formData.append('description', description);
    formData.append('ciq_file', ciqFile);
    if (reregister) {
      formData.append('reregister', 'true');
    }
    for (const [field, file] of Object.entries(inputFiles)) {
      if (file) formData.append(field, file);
    }

    setLoading(true);
    try {
      const data = await api.registerCluster(formData, (event) => {
        if (event.type === 'info') {
          if (event.cluster_count) {
            setParsedInfo({
              cluster_count: event.cluster_count,
              clusters: event.clusters,
            });
          }
          setLogs((prev) => [...prev, event.message]);
        } else if (event.type === 'log') {
          setLogs((prev) => [...prev, event.line]);
        }
      });

      setSuccess(data.message);
      setDescription('');
      setCiqFile(null);
      setInputFiles({});
      setReregister(false);
      e.target.reset();

      setTimeout(() => navigate('/'), 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section-card register-form-card register-cluster-page">
      <h3>Register RHOSO</h3>
      <p className="register-help">
        Upload a RHOSO CIQ <strong>.xlsx</strong> workbook that includes a
        <strong> rhoso_details</strong> table with <strong>Type = RHOSO</strong>, plus supporting
        tables (<strong>rhoso_access</strong>, <strong>rhoso_networks</strong>,
        <strong>rhoso_data_plane_nodes</strong>, and other RHOSO parameter tables as needed).
      </p>
      <p className="register-help">
        Optionally upload path-based input files below (kubeconfig, pull secret, SSH key, etc.).
        CPAT stores them under <code>data/secrets/&lt;cluster-id&gt;/</code> (outside
        source code; container: <code>/cpat-data/secrets/…</code>) and overrides the CIQ
        path parameters. You can also upload or replace these files after registration from the
        dashboard.
      </p>
      <p className="register-help">
        To apply an updated CIQ for an environment that is already registered, enable
        <strong> Re-register existing cluster</strong> before submitting. The same cluster name
        is updated in place (id and existing secrets kept unless you upload replacements).
      </p>

      <form onSubmit={handleSubmit}>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <div className="form-group">
          <label htmlFor="description">Description (optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of the RHOSO environment..."
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="ciq_file">RHOSO CIQ File (.xlsx)</label>
          <div className="file-input-wrapper">
            <input
              id="ciq_file"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setCiqFile(e.target.files[0] || null)}
              required
              disabled={loading}
            />
          </div>
        </div>

        <div className="form-group reregister-option">
          <label className="tail-toggle" htmlFor="reregister">
            <input
              id="reregister"
              type="checkbox"
              checked={reregister}
              onChange={(e) => setReregister(e.target.checked)}
              disabled={loading}
            />
            <span className="tail-toggle-label">
              Re-register existing cluster (update CIQ for the same name)
            </span>
          </label>
        </div>

        <fieldset className="input-files-fieldset" disabled={loading}>
          <legend>Input files (optional)</legend>
          <p className="field-hint">
            Recommended: kubeconfig, pull secret, and data-plane SSH key. Disconnected-only files
            can be skipped for connected deployments. On re-register, leave a field empty to keep
            the previously stored file.
          </p>
          <div className="input-files-grid">
            {RHOSO_INPUT_FILE_FIELDS.map((spec) => (
              <div key={spec.field} className="form-group">
                <label htmlFor={`reg_${spec.field}`}>
                  {spec.label}
                  {spec.recommended ? ' *' : ''}
                </label>
                <p className="field-hint">{spec.help}</p>
                <div className="file-input-wrapper">
                  <input
                    id={`reg_${spec.field}`}
                    type="file"
                    accept={spec.accept}
                    disabled={loading}
                    onChange={(e) =>
                      handleInputFileChange(spec.field, e.target.files[0] || null)
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </fieldset>

        {(loading || logs.length > 0) && (
          <div className="ansible-log-panel">
            <div className="ansible-log-header">
              <span>Ansible execution log</span>
              {parsedInfo && (
                <span className="ansible-log-meta">
                  {parsedInfo.cluster_count
                    ? `${parsedInfo.cluster_count} cluster(s)`
                    : `${parsedInfo.cluster_name} — ${parsedInfo.cluster_type_label}`}
                </span>
              )}
              {loading && <span className="ansible-log-status">Running...</span>}
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
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading
              ? 'Running Ansible...'
              : reregister
                ? 'Re-register RHOSO'
                : 'Register RHOSO'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/')}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
