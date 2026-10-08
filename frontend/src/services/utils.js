/** Shared helper utilities for the frontend. */

// Map backend status strings to CSS badge classes and labels
export function getJobBadge(status) {
  switch (status) {
    case 'QUEUED':              return { cls: 'badge-queued',     label: 'Queued' }
    case 'PROCESSING':          return { cls: 'badge-processing', label: 'Processing' }
    case 'COMPLETED':           return { cls: 'badge-completed',  label: 'Completed' }
    case 'COMPLETED_WITH_ERRORS': return { cls: 'badge-errors',   label: 'With Errors' }
    case 'FAILED':              return { cls: 'badge-failed',     label: 'Failed' }
    default:                    return { cls: 'badge-pending',    label: status }
  }
}

export function getCertBadge(status) {
  switch (status) {
    case 'SUCCESS':    return { cls: 'badge-success',    label: 'Success' }
    case 'FAILED':     return { cls: 'badge-failed',     label: 'Failed' }
    case 'PROCESSING': return { cls: 'badge-processing', label: 'Processing' }
    case 'PENDING':    return { cls: 'badge-pending',    label: 'Pending' }
    default:           return { cls: 'badge-pending',    label: status }
  }
}

// Format ISO date string to human-readable
export function fmtDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch { return iso }
}

export function fmtDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

// Whether the job is still in-progress
export function isJobActive(status) {
  return status === 'QUEUED' || status === 'PROCESSING'
}

// Clamp number between min/max
export function clamp(n, min, max) { return Math.min(Math.max(n, min), max) }
