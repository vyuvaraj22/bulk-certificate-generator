/** Dashboard page — aggregate stats + recent jobs table. */
import { BarChart3, CheckCircle, FileText, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ProgressBar from '../components/ProgressBar'
import { JobBadge } from '../components/StatusBadge'
import { getDashboard } from '../services/api'
import { fmtDate } from '../services/utils'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch(e => setError(e.displayMessage || 'Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  const cards = stats
    ? [
        { icon: FileText,    cls: 'accent',   value: stats.total_jobs,          label: 'Total Jobs' },
        { icon: BarChart3,   cls: 'warning',  value: stats.total_certificates,  label: 'Total Certificates' },
        { icon: CheckCircle, cls: 'success',  value: stats.total_successful,    label: 'Successful' },
        { icon: XCircle,     cls: 'danger',   value: stats.total_failed,        label: 'Failed' },
      ]
    : []

  return (
    <>
      <Header title="Dashboard" subtitle="Overview of certificate generation activity" />
      <main className="main-content">
        {/* Stat cards */}
        <div className="stats-grid">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="stat-card">
                  <div>
                    <div className="skeleton skeleton-text" style={{ width: 60 }} />
                    <div className="skeleton skeleton-text mt-8" style={{ width: 90 }} />
                  </div>
                  <div className="skeleton" style={{ width: 40, height: 40, borderRadius: 8 }} />
                </div>
              ))
            : cards.map(({ icon: Icon, cls, value, label }) => (
                <div key={label} className="stat-card">
                  <div className="stat-info">
                    <div className="stat-value">{value.toLocaleString()}</div>
                    <div className="stat-label">{label}</div>
                  </div>
                  <div className={`stat-icon ${cls}`}>
                    <Icon size={20} />
                  </div>
                </div>
              ))}
        </div>

        {/* Recent jobs */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Recent Jobs</div>
              <div className="card-subtitle">Latest certificate generation activity</div>
            </div>
          </div>

          {error && <div className="error-item">{error}</div>}

          {!loading && !error && (!stats?.recent_jobs?.length) ? (
            <div className="empty-state">
              <FileText size={48} className="empty-state-icon" />
              <div className="empty-state-title">No jobs yet</div>
              <div className="empty-state-sub">Create your first certificate generation job to get started.</div>
              <button className="btn btn-primary mt-12" onClick={() => nav('/create')}>
                Create First Job
              </button>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Event</th>
                    <th>Date</th>
                    <th>Recipients</th>
                    <th>Progress</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <tr key={i}>
                          {Array.from({ length: 7 }).map((_, j) => (
                            <td key={j}><div className="skeleton skeleton-text" /></td>
                          ))}
                        </tr>
                      ))
                    : stats?.recent_jobs?.map(job => (
                        <tr key={job.job_id}>
                          <td>
                            <code style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                              {job.job_id.slice(0, 8)}…
                            </code>
                          </td>
                          <td>
                            <div className="fw-600">{job.event_name}</div>
                            <div className="text-sm text-muted">{job.organization}</div>
                          </td>
                          <td className="text-sm">{fmtDate(job.issue_date)}</td>
                          <td>{job.total}</td>
                          <td style={{ minWidth: 120 }}>
                            <ProgressBar value={job.progress_percentage} showPct={false} />
                            <div className="text-sm text-muted mt-8">{job.progress_percentage}%</div>
                          </td>
                          <td><JobBadge status={job.status} /></td>
                          <td>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => nav(`/jobs/${job.job_id}`)}
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
