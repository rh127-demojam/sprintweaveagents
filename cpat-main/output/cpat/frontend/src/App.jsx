import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import RegisterCluster from './components/RegisterCluster';
import RhosoInstallation from './components/RhosoInstallation';
import OcpDeploymentAutomation from './components/OcpDeploymentAutomation';
import OcpInstallation from './components/OcpInstallation';
import { api } from './api';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then((data) => {
        if (data.authenticated) {
          setUser(data);
        } else {
          setUser(null);
        }
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  };

  if (loading) {
    return <div className="loading">Loading CPAT...</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          user?.authenticated ? (
            <Navigate to="/" replace />
          ) : (
            <Login onLogin={handleLogin} />
          )
        }
      />
      <Route
        path="/"
        element={
          user?.authenticated ? (
            <Layout user={user} onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="register" element={<RegisterCluster />} />
        <Route path="register-cluster" element={<RegisterCluster />} />
        <Route path="rhoso/:clusterId" element={<RhosoInstallation />} />
        <Route path="rhoso-installation" element={<RhosoInstallation />} />
        <Route path="ocp" element={<OcpDeploymentAutomation />} />
        <Route path="ocp-deployment" element={<OcpDeploymentAutomation />} />
        <Route path="register-ocp" element={<OcpDeploymentAutomation />} />
        <Route path="ocp-installation" element={<OcpInstallation />} />
        <Route path="ocp-installation/:clusterId" element={<OcpInstallation />} />
      </Route>
      <Route path="*" element={<Navigate to={user?.authenticated ? '/' : '/login'} replace />} />
    </Routes>
  );
}

export default App;
