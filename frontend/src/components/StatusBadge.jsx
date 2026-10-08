/** Status badge for job and certificate statuses. */
import { getJobBadge, getCertBadge } from '../services/utils'

export function JobBadge({ status }) {
  const { cls, label } = getJobBadge(status)
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {label}
    </span>
  )
}

export function CertBadge({ status }) {
  const { cls, label } = getCertBadge(status)
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {label}
    </span>
  )
}
