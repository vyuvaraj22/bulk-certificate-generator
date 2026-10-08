/** Top header bar. */
import { Bell, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Header({ title, subtitle }) {
  const nav = useNavigate()
  return (
    <header className="header">
      <div>
        <div className="header-title">{title}</div>
        {subtitle && <div className="header-subtitle">{subtitle}</div>}
      </div>
      <div className="header-actions">
        <span className="status-dot" title="Backend connected" />
        <button
          className="btn btn-primary btn-sm"
          onClick={() => nav('/create')}
        >
          <Plus size={14} /> New Job
        </button>
      </div>
    </header>
  )
}
