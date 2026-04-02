import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/leads', icon: '👥', label: 'Lead Center' },
  { to: '/approval', icon: '✅', label: 'Aprobación' },
  { to: '/conversations', icon: '💬', label: 'Conversaciones' },
  { to: '/templates', icon: '✍️', label: 'Templates' },
  { to: '/dispatch', icon: '🚀', label: 'Dispatch' },
  { to: '/logs', icon: '📋', label: 'Activity Log' },
];

const settingsItems = [
  { to: '/blacklist', icon: '🚫', label: 'Blacklist' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🔗</div>
        <div>
          <h1>StudioLink</h1>
          <small>Outreach Engine</small>
        </div>
      </div>

      <nav className="sidebar-nav">
        <span className="sidebar-section-title">Principal</span>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-link-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        <span className="sidebar-section-title" style={{ marginTop: '0.5rem' }}>
          Configuración
        </span>
        {settingsItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-link-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{
        padding: '1rem 1.25rem',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.2rem' }}>🕺</span>
          <div>
            <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Fernando Contreras</div>
            <div>@studio.link1</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
