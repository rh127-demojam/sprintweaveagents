import { useCallback, useEffect, useState } from 'react';

function formatBytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatModified(epochSeconds) {
  if (!epochSeconds) return '—';
  return new Date(epochSeconds * 1000).toLocaleString();
}

/**
 * Review / view / download rendered manifests under artifacts/<cluster>/.
 */
export default function ManifestArtifactsPanel({
  clusterId,
  clusterName,
  listArtifacts,
  getArtifact,
  downloadArtifact,
  downloadAllArtifacts,
  refreshToken = 0,
}) {
  const [artifacts, setArtifacts] = useState([]);
  const [artifactsDir, setArtifactsDir] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState('');
  const [viewLoading, setViewLoading] = useState(false);
  const [downloading, setDownloading] = useState('');

  const loadList = useCallback(async () => {
    if (!clusterId) {
      setArtifacts([]);
      setArtifactsDir('');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await listArtifacts(clusterId);
      setArtifacts(data.artifacts || []);
      setArtifactsDir(data.artifacts_dir || '');
    } catch (err) {
      setError(err.message);
      setArtifacts([]);
      setArtifactsDir('');
    } finally {
      setLoading(false);
    }
  }, [clusterId, listArtifacts]);

  useEffect(() => {
    loadList();
  }, [loadList, refreshToken]);

  useEffect(() => {
    setSelected(null);
    setContent('');
    setViewLoading(false);
  }, [clusterId]);

  const handleClosePreview = () => {
    setSelected(null);
    setContent('');
    setViewLoading(false);
  };

  useEffect(() => {
    if (!selected) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') {
        setSelected(null);
        setContent('');
        setViewLoading(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selected]);

  const handleView = async (name) => {
    if (!clusterId) return;
    setViewLoading(true);
    setError('');
    setSelected(name);
    setContent('Loading…');
    try {
      const data = await getArtifact(clusterId, name);
      const text = data?.text ?? data?.content ?? '';
      if (!text) {
        setError(`File '${name}' is empty or could not be loaded for preview.`);
        setContent('');
      } else {
        setContent(text);
      }
    } catch (err) {
      setError(err.message || 'Failed to load artifact preview.');
      setContent('');
    } finally {
      setViewLoading(false);
    }
  };

  const handleDownload = async (name) => {
    if (!clusterId) return;
    setDownloading(name);
    setError('');
    try {
      await downloadArtifact(clusterId, name);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading('');
    }
  };

  const handleDownloadAll = async () => {
    if (!clusterId || artifacts.length === 0) return;
    setError('');
    setDownloading('__all__');
    try {
      await downloadAllArtifacts(clusterId, clusterName);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading('');
    }
  };

  if (!clusterId) {
    return (
      <div className="manifest-artifacts-panel manifest-artifacts-empty">
        <p className="field-hint">
          Select a RHOSO environment above to list, view, and download rendered manifests.
        </p>
      </div>
    );
  }

  return (
    <div className="manifest-artifacts-panel manifest-artifacts-card">
      <div className="manifest-artifacts-header">
        <div>
          <p className="field-hint">
            Environment <strong>{clusterName}</strong>
            {artifactsDir ? (
              <>
                {' '}
                · <code className="manifest-artifacts-path">{artifactsDir}</code>
              </>
            ) : null}
            {artifacts.length > 0 ? <> · {artifacts.length} file(s)</> : null}
          </p>
        </div>
        <div className="manifest-artifacts-header-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={loadList}
            disabled={loading}
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
          {artifacts.length > 0 && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleDownloadAll}
              disabled={Boolean(downloading)}
            >
              {downloading === '__all__' ? 'Downloading…' : 'Download All (ZIP)'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && artifacts.length === 0 ? (
        <p className="field-hint">Loading artifacts…</p>
      ) : artifacts.length === 0 ? (
        <p className="field-hint">
          No rendered manifests yet. Run <strong>Generate Manifests for Review</strong> first, then
          click Refresh.
        </p>
      ) : (
        <div
          className={`manifest-artifacts-layout${
            selected || viewLoading ? ' has-viewer' : ''
          }`}
        >
          <table className="manifest-artifacts-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Size</th>
                <th>Modified</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {artifacts.map((item) => (
                <tr
                  key={item.name}
                  className={selected === item.name ? 'is-selected' : undefined}
                >
                  <td>
                    <button
                      type="button"
                      className="btn-link manifest-artifact-name"
                      onClick={() => handleView(item.name)}
                      disabled={viewLoading}
                      title="View file"
                    >
                      <code>{item.name}</code>
                    </button>
                  </td>
                  <td>{formatBytes(item.size)}</td>
                  <td>{formatModified(item.modified_at)}</td>
                  <td className="manifest-artifact-actions">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => handleView(item.name)}
                      disabled={viewLoading}
                    >
                      {viewLoading && selected === item.name ? 'Loading…' : 'View'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => handleDownload(item.name)}
                      disabled={downloading === item.name}
                    >
                      {downloading === item.name ? '…' : 'Download'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(selected || viewLoading) && (
            <div className="manifest-artifact-viewer is-open">
              <div className="manifest-artifact-viewer-title">
                <div className="manifest-artifact-viewer-title-text">
                  {viewLoading
                    ? `Loading ${selected || 'file'}…`
                    : (
                      <>
                        Viewing <code>{selected}</code>
                        {content && content !== 'Loading…'
                          ? ` (${content.length} chars)`
                          : ''}
                      </>
                      )}
                </div>
                <button
                  type="button"
                  className="btn manifest-artifact-viewer-close"
                  onClick={handleClosePreview}
                  title="Close preview (Esc)"
                >
                  Close
                </button>
              </div>
              <div className="manifest-artifact-content-scroll">
                <pre className="manifest-artifact-content" aria-live="polite">
                  {content || (viewLoading ? 'Loading…' : '—')}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
