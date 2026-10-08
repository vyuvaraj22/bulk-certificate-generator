/** Sidebar navigation component. */
import { Award, BarChart3, FilePlus, History, LayoutDashboard } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/',        icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/jobs',    icon: History,         label: 'Jobs' },
  { to: '/create',  icon: FilePlus,        label: 'Create Job' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <Award size={18} color="#fff" />
        </div>
        <div className="logo-text">
          Cert<span>Gen</span>
          <div style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-muted)' }}>
            Certificate Generator
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-label">Navigation</div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>CertGen v1.0</div>
        <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginTop: 2 }}>
          Powered by FastAPI + React
        </div>
      </div>
    </aside>
  )
}
