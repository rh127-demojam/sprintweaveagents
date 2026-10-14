const API_BASE = '/api';

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };
  // Avoid sending Content-Type on GET — some stacks mishandle it and return empty bodies.
  if (method !== 'GET' && method !== 'HEAD' && headers['Content-Type'] === undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  });

  const raw = await response.text();
  let data = {};
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      throw new Error('Server returned a non-JSON response.');
    }
  }

  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }

  return data;
}

export const api = {
  login: (username, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  me: () => request('/auth/me'),

  getDashboard: () => request('/dashboard'),

  getClusters: (type) => {
    const query = type ? `?type=${type}` : '';
    return request(`/clusters${query}`);
  },

  getCluster: (clusterId) => request(`/clusters/${clusterId}`),

  deleteCluster: (clusterId) =>
    request(`/clusters/${clusterId}`, { method: 'DELETE' }),

  registerCluster: async (formData, onEvent) => {
    const response = await fetch(`${API_BASE}/clusters/register`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      if (contentType.includes('application/json')) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Request failed (${response.status})`);
      }
      throw new Error(`Request failed (${response.status})`);
    }

    if (!response.body) {
      throw new Error('No response stream from server.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let lastSuccess = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (onEvent) onEvent(event);
        if (event.type === 'success') lastSuccess = event;
        if (event.type === 'error') {
          throw new Error(event.message || 'Registration failed.');
        }
      }
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (onEvent) onEvent(event);
      if (event.type === 'success') lastSuccess = event;
      if (event.type === 'error') {
        throw new Error(event.message || 'Registration failed.');
      }
    }

    if (!lastSuccess) {
      throw new Error('Registration did not complete successfully.');
    }

    return lastSuccess;
  },

  getRegistrationLog: (clusterId) =>
    request(`/clusters/${clusterId}/registration-log`),

  getClusterInputFiles: (clusterId) => request(`/clusters/${clusterId}/input-files`),

  uploadClusterInputFiles: async (clusterId, formData) => {
    const response = await fetch(`${API_BASE}/clusters/${clusterId}/input-files`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `Upload failed (${response.status})`);
    }
    return data;
  },

  getRhosoInstallations: (clusterName, status) => {
    const params = new URLSearchParams();
    if (clusterName) params.set('cluster_name', clusterName);
    if (status) params.set('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/rhoso-installations${query}`);
  },

  getRhosoInstallationStatus: (executionId) =>
    request(`/rhoso-installations/${executionId}`),

  runRhosoInstallation: async (payload, onEvent) => {
    const response = await fetch(`${API_BASE}/rhoso-installations/run`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      if (contentType.includes('application/json')) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Request failed (${response.status})`);
      }
      throw new Error(`Request failed (${response.status})`);
    }

    if (!response.body) {
      throw new Error('No response stream from server.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let lastSuccess = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (onEvent) onEvent(event);
        if (event.type === 'success') lastSuccess = event;
        if (event.type === 'error' && event.fatal) {
          throw new Error(event.message || 'Installation failed.');
        }
      }
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (onEvent) onEvent(event);
      if (event.type === 'success') lastSuccess = event;
      if (event.type === 'error' && event.fatal) {
        throw new Error(event.message || 'Installation failed.');
      }
    }

    if (!lastSuccess) {
      throw new Error('Installation did not complete successfully.');
    }

    return lastSuccess;
  },

  getRhosoInstallationLog: (executionId) =>
    request(`/rhoso-installations/${executionId}/log`),

  downloadRhosoInstallationLog: async (executionId, filename) => {
    const response = await fetch(
      `${API_BASE}/rhoso-installations/${executionId}/log?download=1`,
      { credentials: 'include' }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${response.status})`);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'rhoso-installation.log';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  getClusterArtifacts: (clusterId) => request(`/clusters/${clusterId}/artifacts`),

  /**
   * Load artifact text for the in-UI preview.
   * Uses the same ?download=1 endpoint as Download (plain text) — that path is
   * proven working; JSON view responses were arriving empty in the browser.
   */
  getClusterArtifact: async (clusterId, filename) => {
    const response = await fetch(
      `${API_BASE}/clusters/${clusterId}/artifacts/${encodeURIComponent(filename)}?download=1`,
      { credentials: 'include' }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Failed to load artifact (${response.status})`);
    }
    const text = await response.text();
    return { name: filename, text, content: text, size: text.length };
  },

  downloadClusterArtifact: async (clusterId, filename) => {
    const response = await fetch(
      `${API_BASE}/clusters/${clusterId}/artifacts/${encodeURIComponent(filename)}?download=1`,
      { credentials: 'include' }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  downloadAllClusterArtifacts: async (clusterId, clusterName) => {
    const response = await fetch(
      `${API_BASE}/clusters/${clusterId}/artifacts/download-all`,
      { credentials: 'include' }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${clusterName || 'rhoso'}-manifests.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  // =========================================================================
  // OCP API
  // =========================================================================

  registerOcpCluster: async (formData, onEvent) => {
    const response = await fetch(`${API_BASE}/ocp/clusters/register`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      if (contentType.includes('application/json')) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Request failed (${response.status})`);
      }
      throw new Error(`Request failed (${response.status})`);
    }

    if (!response.body) {
      throw new Error('No response stream from server.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let lastSuccess = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (onEvent) onEvent(event);
        if (event.type === 'success') lastSuccess = event;
        if (event.type === 'error' && event.fatal) {
          throw new Error(event.message || 'Registration failed.');
        }
      }
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (onEvent) onEvent(event);
      if (event.type === 'success') lastSuccess = event;
      if (event.type === 'error' && event.fatal) {
        throw new Error(event.message || 'Registration failed.');
      }
    }

    if (!lastSuccess) {
      throw new Error('Registration did not complete successfully.');
    }

    return lastSuccess;
  },

  getOcpInstallationTasks: () => request('/ocp-installations/tasks'),

  getOcpInstallations: (clusterName, status) => {
    const params = new URLSearchParams();
    if (clusterName) params.set('cluster_name', clusterName);
    if (status) params.set('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/ocp-installations${query}`);
  },

  getOcpInstallationStatus: (executionId) =>
    request(`/ocp-installations/${executionId}`),

  runOcpInstallation: async (payload) => {
    const data = await request('/ocp-installations/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return data;
  },

  getOcpInstallationLog: (executionId) =>
    request(`/ocp-installations/${executionId}/log`),

  downloadOcpInstallationLog: async (executionId, filename) => {
    const response = await fetch(
      `${API_BASE}/ocp-installations/${executionId}/log?download=1`,
      { credentials: 'include' }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${response.status})`);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'ocp-installation.log';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  getOcpCommandLog: (executionId) =>
    request(`/ocp-installations/${executionId}/command-log`),

  downloadOcpCommandLog: async (executionId, filename) => {
    const response = await fetch(
      `${API_BASE}/ocp-installations/${executionId}/command-log?download=1`,
      { credentials: 'include' }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'command.log';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  health: () => request('/health'),
};

/**
 * CPAT version format YY.M.W (year.month.week-of-month) — same as API / image tag.
 * Month has no leading zero for 1–9 (e.g. 7); 10–12 unchanged.
 */
export function formatCpatVersion(when = new Date()) {
  const yy = String(when.getFullYear() % 100).padStart(2, '0');
  const m = String(when.getMonth() + 1); // no pad: 7 not 07
  const w = Math.floor((when.getDate() - 1) / 7) + 1;
  return `${yy}.${m}.${w}`;
}

/** UI display only: prefix with v → vYY.M.W */
export function displayCpatVersion(version) {
  const raw = (version || formatCpatVersion()).replace(/^v/i, '');
  return `v${raw}`;
}
