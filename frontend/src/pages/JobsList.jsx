/** Jobs list page with search, filter, and sort. */
import { Download, Eye, RefreshCw, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ProgressBar from '../components/ProgressBar'
import { JobBadge } from '../components/StatusBadge'
import { downloadJobZip, listJobs } from '../services/api'
import { fmtDateTime } from '../services/utils'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'QUEUED', label: 'Queued' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'COMPLETED_WITH_ERRORS', label: 'With Errors' },
  { value: 'FAILED', label: 'Failed' },
]

export default function JobsList() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const nav = useNavigate()

  const load = () => {
    setLoading(true)
    listJobs({ search: search || undefined, status: statusFilter || undefined })
      .then(setJobs)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [search, statusFilter])

  return (
    <>
      <Header title="Jobs" subtitle="All certificate generation jobs" />
      <main className="main-content">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Generation Jobs</div>
              <div className="card-subtitle">{jobs.length} job{jobs.length !== 1 ? 's' : ''} found</div>
            </div>
            <div className="filter-bar">
              <div className="search-input-wrap">
                <Search size={14} />
                <input
                  className="search-input"
                  placeholder="Search by event name…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
              <select
                className="form-select"
                style={{ width: 160 }}
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                {STATUS_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <button className="btn btn-ghost btn-sm" onClick={load} title="Refresh">
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          {jobs.length === 0 && !loading ? (
            <div className="empty-state">
              <div className="empty-state-title">No jobs found</div>
              <div className="empty-state-sub">Try adjusting your search or filter, or create a new job.</div>
              <button className="btn btn-primary mt-12" onClick={() => nav('/create')}>Create Job</button>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Event</th>
                    <th>Organisation</th>
                    <th>Created</th>
                    <th>Total</th>
                    <th>Success / Failed</th>
                    <th>Progress</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <tr key={i}>
                          {Array.from({ length: 9 }).map((_, j) => (
                            <td key={j}><div className="skeleton skeleton-text" /></td>
                          ))}
                        </tr>
                      ))
                    : jobs.map(job => (
                        <tr key={job.job_id}>
                          <td>
                            <code style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                              {job.job_id.slice(0, 8)}…
                            </code>
                          </td>
                          <td className="fw-600">{job.event_name}</td>
                          <td className="text-sm text-muted">{job.organization}</td>
                          <td className="text-sm">{fmtDateTime(job.created_at)}</td>
                          <td>{job.total}</td>
                          <td>
                            <span className="text-success fw-600">{job.successful}</span>
                            {' / '}
                            <span className="text-danger fw-600">{job.failed}</span>
                          </td>
                          <td style={{ minWidth: 100 }}>
                            <ProgressBar value={job.progress_percentage} showPct={false} />
                          </td>
                          <td><JobBadge status={job.status} /></td>
                          <td>
                            <div className="table-actions">
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => nav(`/jobs/${job.job_id}`)}
                                title="View details"
                              >
                                <Eye size={13} />
                              </button>
                              {(job.status === 'COMPLETED' || job.status === 'COMPLETED_WITH_ERRORS') && job.successful > 0 && (
                                <a
                                  href={downloadJobZip(job.job_id)}
                                  className="btn btn-ghost btn-sm"
                                  title="Download ZIP"
                                >
                                  <Download size={13} />
                                </a>
                              )}
                            </div>
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
