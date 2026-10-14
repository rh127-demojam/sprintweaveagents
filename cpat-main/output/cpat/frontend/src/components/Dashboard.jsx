import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import RegistrationLogModal from './RegistrationLogModal';
import InputFilesModal from './InputFilesModal';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [logCluster, setLogCluster] = useState(null);
  const [filesCluster, setFilesCluster] = useState(null);

  useEffect(() => {
    api
      .getDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleViewLog = (cluster) => {
    setLogCluster(cluster);
  };

  const handleCloseLog = () => {
    setLogCluster(null);
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  const { summary, recent_clusters: recentClusters } = data;

  return (
    <>
      <div className="welcome-banner">
        <h2>Welcome to CPAT</h2>
        <p>
          Cloud Platform Automation Tool for Red Hat OpenStack Services on OpenShift
          (RHOSO) and OpenShift Container Platform (OCP) registration and deployment.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="label">Total Environments</div>
          <div className="value">{summary.total_clusters}</div>
        </div>
        <div className="stat-card rhoso">
          <div className="label">RHOSO Environments</div>
          <div className="value">{summary.rhoso_environments ?? 0}</div>
        </div>
        <div className="stat-card ocp">
          <div className="label">OCP Clusters</div>
          <div className="value">{summary.ocp_clusters ?? 0}</div>
        </div>
      </div>

      <div className="section-card">
        <h3>Recently Registered Environments</h3>
        {recentClusters.length === 0 ? (
          <div className="empty-state">
            <p>No environments registered yet.</p>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <Link to="/ocp-deployment" className="btn btn-primary" style={{ minWidth: '160px', textAlign: 'center' }}>
                Register OCP
              </Link>
              <Link to="/register-cluster" className="btn btn-primary" style={{ minWidth: '160px', textAlign: 'center' }}>
                Register RHOSO
              </Link>
            </div>
          </div>
        ) : (
          <table className="cluster-table">
            <thead>
              <tr>
                <th>Environment Name</th>
                <th>Type</th>
                <th>CIQ File</th>
                <th>Status</th>
                <th>Registered At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recentClusters.map((cluster) => (
                <tr key={cluster.id}>
                  <td>{cluster.cluster_name}</td>
                  <td>
                    <span className={`badge badge-${cluster.cluster_type}`}>
                      {cluster.cluster_type_label}
                    </span>
                  </td>
                  <td>{cluster.ciq_filename}</td>
                  <td>
                    <span className="badge badge-registered">{cluster.status}</span>
                  </td>
                  <td>{new Date(cluster.registered_at).toLocaleString()}</td>
                  <td className="table-actions">
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => setFilesCluster(cluster)}
                    >
                      Input files
                    </button>
                    {cluster.has_registration_log ? (
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => handleViewLog(cluster)}
                      >
                        View log
                      </button>
                    ) : null}
                    <Link
                      to={cluster.cluster_type === 'ocp'
                        ? `/ocp-installation/${cluster.id}`
                        : `/rhoso/${cluster.id}`}
                      className="btn-link"
                    >
                      Install
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <RegistrationLogModal
        cluster={logCluster}
        open={Boolean(logCluster)}
        onClose={handleCloseLog}
      />
      <InputFilesModal
        cluster={filesCluster}
        open={Boolean(filesCluster)}
        onClose={() => setFilesCluster(null)}
      />
    </>
  );
}
