import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { displayCpatVersion, formatCpatVersion } from '../api';

const dashboardNavItems = [
  { path: '/', label: 'Dashboard', icon: '▣', end: true },
];

const ocpNavItems = [
  { path: '/ocp-deployment', label: 'Register OCP', icon: '⊕', end: false },
  { path: '/ocp-installation', label: 'OCP Installation', icon: '◎', end: false },
];

const rhosoNavItems = [
  { path: '/register-cluster', label: 'Register RHOSO', icon: '⊕', end: false },
  { path: '/rhoso-installation', label: 'RHOSO Installation', icon: '◎', end: false },
];

const pageTitles = {
  '/': 'Dashboard',
  '/register': 'Register RHOSO',
  '/register-cluster': 'Register RHOSO',
  '/rhoso-installation': 'RHOSO Installation',
  '/ocp': 'OCP Deployment Automation',
  '/ocp-deployment': 'Register OCP Cluster',
  '/register-ocp': 'Register OCP Cluster',
  '/ocp-installation': 'OCP Installation',
};

export default function Layout({ user, onLogout }) {
  const location = useLocation();
  const pageTitle =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/rhoso/') ? 'RHOSO Installation' :
     location.pathname.startsWith('/ocp-installation/') ? 'OCP Installation' : 'CPAT');
  const version = displayCpatVersion(user?.version || formatCpatVersion());

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <img src="/redhat-logo-sidebar.svg" alt="Red Hat" />
          <h2>CPAT</h2>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            {dashboardNavItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>

          <div className="nav-section">
            <div className="nav-section-label">OCP Deployment Automation</div>
            {ocpNavItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>

          <div className="nav-section">
            <div className="nav-section-label">RHOSO Deployment Automation</div>
            {rhosoNavItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        <div className="sidebar-footer">Version {version}</div>
      </aside>

      <div className="main-content">
        <header className="top-bar">
          <h1>{pageTitle}</h1>
          <div className="top-bar-actions">
            <span className="user-badge">{user.username}</span>
            <button type="button" className="btn btn-secondary" onClick={onLogout}>
              Logout
            </button>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
