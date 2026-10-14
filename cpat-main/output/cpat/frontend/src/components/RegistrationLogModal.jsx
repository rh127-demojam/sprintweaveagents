import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';

export default function RegistrationLogModal({ cluster, open, onClose }) {
  const [logContent, setLogContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [scrollRecentLog, setScrollRecentLog] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');
  const logContainerRef = useRef(null);

  const fetchLog = useCallback(async () => {
    if (!cluster?.id) return;

    try {
      const data = await api.getRegistrationLog(cluster.id);
      setLogContent(data.content || '');
      setLastUpdated(data.updated_at || '');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [cluster?.id]);

  useEffect(() => {
    if (!open || !cluster) {
      setLogContent('');
      setError('');
      setScrollRecentLog(false);
      return;
    }

    setLoading(true);
    fetchLog().finally(() => setLoading(false));
  }, [open, cluster, fetchLog]);

  useEffect(() => {
    if (!open || !cluster || !scrollRecentLog) return undefined;

    const intervalId = setInterval(fetchLog, 2000);
    return () => clearInterval(intervalId);
  }, [open, cluster, scrollRecentLog, fetchLog]);

  useEffect(() => {
    if (!scrollRecentLog || !logContainerRef.current) return;
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
  }, [logContent, scrollRecentLog]);

  useEffect(() => {
    if (!open) return undefined;

    const handleEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  if (!open || !cluster) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal-dialog log-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="registration-log-title"
      >
        <div className="modal-header">
          <div>
            <h3 id="registration-log-title">Registration Log</h3>
            <p className="modal-subtitle">
              {cluster.cluster_name} — {cluster.cluster_type_label}
            </p>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-toolbar">
          {lastUpdated && !scrollRecentLog && (
            <span className="tail-status">
              Last updated: {new Date(lastUpdated).toLocaleString()}
            </span>
          )}
          {scrollRecentLog && (
            <span className="tail-status">Refreshing every 2s</span>
          )}
        </div>

        {error && <div className="error-message modal-error">{error}</div>}

        <div ref={logContainerRef} className="modal-log-content">
          {loading && !logContent ? (
            <span className="text-muted">Loading log...</span>
          ) : (
            <pre>{logContent || 'No log content available.'}</pre>
          )}
        </div>

        <div className="modal-footer modal-footer-with-tail">
          <label className="tail-toggle">
            <input
              type="checkbox"
              checked={scrollRecentLog}
              onChange={(e) => setScrollRecentLog(e.target.checked)}
            />
            <span className="tail-toggle-label">Auto-scroll to latest</span>
          </label>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
