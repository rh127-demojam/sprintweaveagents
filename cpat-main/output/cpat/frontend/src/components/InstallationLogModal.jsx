import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';

function formatStatusLabel(status) {
  if (status === 'in_progress') return 'In Progress';
  if (status === 'complete') return 'Complete';
  if (status === 'failed') return 'Failed';
  return status;
}

export default function InstallationLogModal({
  execution,
  open,
  onClose,
  getLog = api.getInstallationLog,
  downloadLog = api.downloadInstallationLog,
  logTitle = 'Installation Log',
}) {
  const [logContent, setLogContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');
  const [tailEnabled, setTailEnabled] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');
  const logContainerRef = useRef(null);

  const fetchLog = useCallback(async () => {
    if (!execution?.id) return;

    try {
      const data = await getLog(execution.id);
      setLogContent(data.content || '');
      setLastUpdated(data.updated_at || '');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [execution?.id, getLog]);

  useEffect(() => {
    if (!open || !execution) {
      setLogContent('');
      setError('');
      setTailEnabled(false);
      return;
    }

    // Auto-enable tailing when viewing an in-progress execution
    if (execution.status === 'in_progress') {
      setTailEnabled(true);
    }

    setLoading(true);
    fetchLog().finally(() => setLoading(false));
  }, [open, execution, fetchLog]);

  useEffect(() => {
    if (!open || !execution || !tailEnabled) return undefined;

    const intervalId = setInterval(fetchLog, 2000);
    return () => clearInterval(intervalId);
  }, [open, execution, tailEnabled, fetchLog]);

  useEffect(() => {
    if (execution?.status !== 'in_progress') {
      setTailEnabled(false);
    }
  }, [execution?.status]);

  useEffect(() => {
    if (!tailEnabled || !logContainerRef.current) return;
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
  }, [logContent, tailEnabled]);

  useEffect(() => {
    if (!open) return undefined;

    const handleEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  const handleDownload = async () => {
    if (!execution?.id) return;

    setDownloading(true);
    setError('');
    try {
      const safeCluster = execution.cluster_name.replace(/[^\w.-]+/g, '-');
      const safeTask = execution.task_name.replace(/[^\w.-]+/g, '-');
      await downloadLog(
        execution.id,
        `${safeCluster}-${safeTask}-installation.log`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (!open || !execution) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal-dialog log-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="installation-log-title"
      >
        <div className="modal-header">
          <div>
            <h3 id="installation-log-title">{logTitle}</h3>
            <p className="modal-subtitle">
              {execution.cluster_name} — {execution.task_name} ({execution.ocp_version})
            </p>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-toolbar">
          {lastUpdated && !tailEnabled && (
            <span className="tail-status">
              Last updated: {new Date(lastUpdated).toLocaleString()}
            </span>
          )}
          {execution.status === 'in_progress' && tailEnabled && (
            <span className="tail-status">Refreshing every 2s</span>
          )}
          <span className={`badge badge-${execution.status}`}>
            {formatStatusLabel(execution.status)}
          </span>
        </div>

        {error && <div className="error-message modal-error">{error}</div>}

        <div ref={logContainerRef} className="modal-log-content">
          {loading && !logContent ? (
            <span className="text-muted">Loading log...</span>
          ) : (
            <pre>{logContent || 'No log content available yet.'}</pre>
          )}
        </div>

        <div className="modal-footer modal-footer-with-tail">
          {execution.status === 'in_progress' && (
            <label className="tail-toggle">
              <input
                type="checkbox"
                checked={tailEnabled}
                onChange={(e) => setTailEnabled(e.target.checked)}
              />
              <span className="tail-toggle-label">Auto-scroll to latest</span>
            </label>
          )}
          <div className="modal-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleDownload}
              disabled={downloading || !execution.has_execution_log}
            >
              {downloading ? 'Downloading...' : 'Download Log'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
