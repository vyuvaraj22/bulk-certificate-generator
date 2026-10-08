/**
 * Job Detail page.
 *
 * - Polls the job status while active.
 * - Shows progress bar, stat cards, and a searchable/filterable certificate table.
 * - Supports retry, ZIP download, certificate preview, individual PDF download.
 */
import {
  AlertTriangle, ArrowLeft, CheckCircle, Download,
  Eye, RefreshCw, RotateCcw, Search, XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import CertPreviewModal from '../components/CertPreviewModal'
import Header from '../components/Header'
import ProgressBar from '../components/ProgressBar'
import { CertBadge, JobBadge } from '../components/StatusBadge'
import { downloadCertificateUrl, downloadJobZip, getJobCertificates, retryFailed } from '../services/api'
import { useJobPolling } from '../hooks/useJobPolling'
import { fmtDateTime } from '../services/utils'

const STATUS_FILTERS = ['ALL', 'SUCCESS', 'FAILED', 'PENDING', 'PROCESSING']

export default function JobDetail() {
  const { jobId } = useParams()
  const nav = useNavigate()
  const { job, loading: jobLoading, error: jobError, refresh: refreshJob } = useJobPolling(jobId)

  const [certs, setCerts] = useState(null)
  const [certsLoading, setCertsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [page, setPage] = useState(1)
  const [previewCert, setPreviewCert] = useState(null)
  const [retrying, setRetrying] = useState(false)

  const loadCerts = useCallback(() => {
    if (!jobId) return
    setCertsLoading(true)
    getJobCertificates(jobId, {
      search: search || undefined,
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      page,
      page_size: 20,
    })
      .then(setCerts)
      .catch(console.error)
      .finally(() => setCertsLoading(false))
  }, [jobId, search, statusFilter, page])

  useEffect(() => { loadCerts() }, [loadCerts])
  // Reload certs when job transitions to a terminal state
  useEffect(() => {
    if (job && !['QUEUED', 'PROCESSING'].includes(job.status)) {
      loadCerts()
    }
  }, [job?.status])

  const handleRetry = async () => {
    setRetrying(true)
    try {
      const res = await retryFailed(jobId)
      toast.success(res.message)
      refreshJob()
      loadCerts()
    } catch (e) {
      toast.error(e.displayMessage || 'Retry failed')
    } finally {
      setRetrying(false)
    }
  }

  if (jobLoading) return (
    <>
      <Header title="Job Details" />
      <main className="main-content">
        <div className="card" style={{ padding: 40 }}>
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-text mt-8" />
          <div style={{ marginTop: 24 }}><div className="skeleton" style={{ height: 8, borderRadius: 999 }} /></div>
        </div>
      </main>
    </>
  )

  if (jobError || !job) return (
    <>
      <Header title="Job Details" />
      <main className="main-content">
        <div className="error-item">{jobError || 'Job not found'}</div>
        <button className="btn btn-ghost mt-12" onClick={() => nav('/jobs')}><ArrowLeft size={14} /> Back</button>
      </main>
    </>
  )

  const statsCards = [
    { label: 'Total',      value: job.total,      color: 'var(--text-primary)' },
    { label: 'Completed',  value: job.completed,  color: 'var(--info)' },
    { label: 'Successful', value: job.successful, color: 'var(--success)' },
    { label: 'Failed',     value: job.failed,     color: 'var(--danger)' },
  ]

  const isActive = ['QUEUED', 'PROCESSING'].includes(job.status)
  const canDownload = (job.status === 'COMPLETED' || job.status === 'COMPLETED_WITH_ERRORS') && job.successful > 0
  const hasFailed = job.failed > 0

  return (
    <>
      <Header title={job.event_name} subtitle={`Job ${job.job_id.slice(0, 8)}…`} />
      <main className="main-content">
        {/* Back + actions */}
        <div className="page-header">
          <button className="btn btn-ghost btn-sm" onClick={() => nav('/jobs')}>
            <ArrowLeft size={14} /> All Jobs
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            {canDownload && (
              <a href={downloadJobZip(jobId)} className="btn btn-secondary btn-sm">
                <Download size={14} /> Download All ZIP
              </a>
            )}
            {hasFailed && !isActive && (
              <button className="btn btn-danger btn-sm" onClick={handleRetry} disabled={retrying}>
                <RotateCcw size={14} /> {retrying ? 'Retrying…' : 'Retry Failed'}
              </button>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => { refreshJob(); loadCerts() }}>
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* Job overview card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{ fontFamily: 'Sora, sans-serif', fontSize: 20, fontWeight: 700 }}>{job.event_name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                {job.organization} · {job.certificate_title}
              </div>
              <div style={{ marginTop: 8 }}><JobBadge status={job.status} /></div>
            </div>
            <div style={{ textAlign: 'right', fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }}>
              <div>Created: {fmtDateTime(job.created_at)}</div>
              {job.started_at && <div>Started: {fmtDateTime(job.started_at)}</div>}
              {job.completed_at && <div>Completed: {fmtDateTime(job.completed_at)}</div>}
            </div>
          </div>

          {/* Progress */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {job.completed} / {job.total} processed
              </span>
              <span className="progress-pct">{job.progress_percentage}%</span>
            </div>
            <ProgressBar value={job.progress_percentage} showPct={false} />
            {isActive && (
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <div className="badge-dot" style={{ background: 'var(--warning)', animation: 'pulse 1.2s infinite' }} />
                Generating certificates in the background…
              </div>
            )}
          </div>

          {/* Stat mini-cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {statsCards.map(s => (
              <div key={s.label} style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '14px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Certificates table */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Certificates</div>
              <div className="card-subtitle">{certs?.total ?? '—'} recipients</div>
            </div>
            <div className="filter-bar">
              <div className="search-input-wrap">
                <Search size={14} />
                <input
                  className="search-input"
                  placeholder="Search name, email, ID…"
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1) }}
                />
              </div>
              <div className="tabs" style={{ padding: 3 }}>
                {STATUS_FILTERS.map(s => (
                  <button
                    key={s}
                    className={`tab-btn${statusFilter === s ? ' active' : ''}`}
                    onClick={() => { setStatusFilter(s); setPage(1) }}
                  >
                    {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Recipient</th>
                  <th>Email</th>
                  <th>Certificate ID</th>
                  <th>Status</th>
                  <th>Completed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {certsLoading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 6 }).map((_, j) => (
                          <td key={j}><div className="skeleton skeleton-text" /></td>
                        ))}
                      </tr>
                    ))
                  : certs?.certificates.length === 0
                  ? (
                    <tr>
                      <td colSpan={6}>
                        <div className="empty-state" style={{ padding: '30px 0' }}>
                          <div className="empty-state-title">No certificates match your filter</div>
                        </div>
                      </td>
                    </tr>
                  )
                  : certs?.certificates.map(cert => (
                      <tr key={cert.id}>
                        <td className="fw-600">{cert.recipient_name}</td>
                        <td className="text-sm text-muted">{cert.recipient_email}</td>
                        <td>
                          <code style={{ fontSize: 12 }}>{cert.certificate_id}</code>
                        </td>
                        <td>
                          <CertBadge status={cert.status} />
                          {cert.error_message && (
                            <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 4, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                 title={cert.error_message}>
                              {cert.error_message}
                            </div>
                          )}
                        </td>
                        <td className="text-sm text-muted">{fmtDateTime(cert.completed_at)}</td>
                        <td>
                          <div className="table-actions">
                            {cert.status === 'SUCCESS' && (
                              <>
                                <button
                                  className="btn btn-ghost btn-sm"
                                  onClick={() => setPreviewCert(cert)}
                                  title="Preview"
                                >
                                  <Eye size={13} />
                                </button>
                                <a
                                  href={downloadCertificateUrl(cert.id)}
                                  className="btn btn-ghost btn-sm"
                                  title="Download PDF"
                                >
                                  <Download size={13} />
                                </a>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {certs && certs.total > certs.page_size && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button className="btn btn-ghost btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                Previous
              </button>
              <span style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: '32px' }}>
                Page {page} of {Math.ceil(certs.total / certs.page_size)}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={page >= Math.ceil(certs.total / certs.page_size)}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Certificate preview modal */}
        {previewCert && (
          <CertPreviewModal cert={previewCert} onClose={() => setPreviewCert(null)} />
        )}
      </main>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </>
  )
}
