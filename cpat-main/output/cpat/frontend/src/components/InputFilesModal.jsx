import { useEffect, useState } from 'react';
import { api } from '../api';
import { RHOSO_INPUT_FILE_FIELDS } from '../rhosoInputFiles';
import { OCP_INPUT_FILE_FIELDS } from '../ocpInputFiles';

export default function InputFilesModal({ cluster, open, onClose }) {
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!open || !cluster?.id) return undefined;

    let cancelled = false;
    setError('');
    setSuccess('');
    setSelected({});
    setLoading(true);

    api
      .getClusterInputFiles(cluster.id)
      .then((data) => {
        if (!cancelled) setFiles(data.files || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, cluster?.id]);

  if (!open || !cluster) return null;

  const statusByField = Object.fromEntries(
    (files || []).map((row) => [row.field, row])
  );

  const handleFileChange = (field, file) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (file) next[field] = file;
      else delete next[field];
      return next;
    });
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const entries = Object.entries(selected).filter(([, file]) => file);
    if (entries.length === 0) {
      setError('Select at least one file to upload.');
      return;
    }

    const formData = new FormData();
    for (const [field, file] of entries) {
      formData.append(field, file);
    }

    setUploading(true);
    try {
      const data = await api.uploadClusterInputFiles(cluster.id, formData);
      setFiles(data.files || []);
      setSelected({});
      setSuccess(data.message || 'Input files updated.');
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-dialog input-files-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="input-files-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h3 id="input-files-title">Input files</h3>
            <p className="modal-subtitle">{cluster.cluster_name}</p>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <p className="register-help" style={{ margin: '0 1.25rem 0.75rem' }}>
          Upload path-based secrets individually. CPAT stores them under{' '}
          <code>data/secrets/&lt;cluster-id&gt;/</code> (runtime data dir; container{' '}
          <code>/cpat-data</code>) and updates the corresponding CIQ path parameters for
          installation tasks.
        </p>

        {error && <div className="modal-error">{error}</div>}
        {success && (
          <div className="success-message" style={{ margin: '0 1.25rem 0.75rem' }}>
            {success}
          </div>
        )}

        {loading ? (
          <div className="loading" style={{ padding: '1.5rem' }}>
            Loading input file status...
          </div>
        ) : (
          <form onSubmit={handleUpload}>
            <div className="input-files-grid">
              {(cluster.cluster_type === 'ocp' ? OCP_INPUT_FILE_FIELDS : RHOSO_INPUT_FILE_FIELDS).map((spec) => {
                const status = statusByField[spec.field];
                return (
                  <div key={spec.field} className="form-group input-file-row">
                    <label htmlFor={`post_${spec.field}`}>
                      {spec.label}
                      {status?.uploaded ? (
                        <span className="badge badge-registered" style={{ marginLeft: '0.5rem' }}>
                          uploaded
                        </span>
                      ) : (
                        <span className="text-muted" style={{ marginLeft: '0.5rem' }}>
                          not uploaded
                        </span>
                      )}
                    </label>
                    <p className="field-hint">{spec.help}</p>
                    {status?.original_filename && (
                      <p className="field-hint">
                        Last file: {status.original_filename}
                        {status.uploaded_at
                          ? ` (${new Date(status.uploaded_at).toLocaleString()})`
                          : ''}
                      </p>
                    )}
                    <div className="file-input-wrapper">
                      <input
                        id={`post_${spec.field}`}
                        type="file"
                        accept={spec.accept}
                        disabled={uploading}
                        onChange={(e) =>
                          handleFileChange(spec.field, e.target.files[0] || null)
                        }
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={uploading}>
                Close
              </button>
              <button type="submit" className="btn btn-primary" disabled={uploading}>
                {uploading ? 'Uploading...' : 'Upload selected'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
