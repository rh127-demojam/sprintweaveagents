function formatStatusLabel(status) {
  if (status === 'in_progress') return 'In Progress';
  if (status === 'complete') return 'Complete';
  if (status === 'failed') return 'Failed';
  return status;
}

export default function ExecutionTable({
  title,
  emptyMessage,
  executions,
  loading,
  onViewLog,
  onViewCommandLog,
  taskColumnLabel = 'Task',
  versionHeader = 'OCP Version',
}) {
  return (
    <div className="section-card executions-card">
      <h3>{title}</h3>
      {loading && executions.length === 0 ? (
        <div className="loading">Loading executions...</div>
      ) : executions.length === 0 ? (
        <div className="empty-state">
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <table className="cluster-table execution-table">
          <thead>
            <tr>
              <th>Cluster</th>
              <th>{versionHeader}</th>
              <th>{taskColumnLabel}</th>
              <th>Status</th>
              <th>Started At</th>
              <th>Completed At</th>
              <th>Log</th>
            </tr>
          </thead>
          <tbody>
            {executions.map((execution) => (
              <tr key={execution.id}>
                <td>{execution.cluster_name}</td>
                <td>{execution.rhoso_version || execution.ocp_version}</td>
                <td>{execution.task_name}</td>
                <td>
                  <span className={`badge badge-${execution.status}`}>
                    {formatStatusLabel(execution.status)}
                  </span>
                </td>
                <td>{new Date(execution.started_at).toLocaleString()}</td>
                <td>
                  {execution.completed_at
                    ? new Date(execution.completed_at).toLocaleString()
                    : '—'}
                </td>
                <td className="execution-log-actions">
                  {execution.has_execution_log || execution.status === 'in_progress' ? (
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => onViewLog(execution)}
                    >
                      View Log
                    </button>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                  {execution.has_command_log && onViewCommandLog && (
                    <button
                      type="button"
                      className="btn-link"
                      style={{ marginLeft: 8 }}
                      onClick={() => onViewCommandLog(execution)}
                    >
                      Command Log
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
