/**
 * API service — wraps all backend calls in one place.
 * Uses relative URLs so Vite's proxy routes them to FastAPI.
 */
import axios from 'axios'

const api = axios.create({ baseURL: '/' })

// ── Error normaliser ─────────────────────────────────────────────────────────

function extractMessage(err) {
  if (err.response?.data?.detail) {
    const d = err.response.data.detail
    if (typeof d === 'string') return d
    if (d.message) return d.message
    if (Array.isArray(d)) return d.map(e => e.msg || e.message).join('; ')
  }
  if (err.response?.data?.error?.message) return err.response.data.error.message
  return err.message || 'Unknown error'
}

api.interceptors.response.use(
  res => res,
  err => {
    err.displayMessage = extractMessage(err)
    return Promise.reject(err)
  }
)

// ── Jobs ─────────────────────────────────────────────────────────────────────

export const createJob = (payload) => api.post('/api/jobs', payload).then(r => r.data)

export const listJobs = (params = {}) =>
  api.get('/api/jobs', { params }).then(r => r.data)

export const getJob = (jobId) => api.get(`/api/jobs/${jobId}`).then(r => r.data)

export const getJobCertificates = (jobId, params = {}) =>
  api.get(`/api/jobs/${jobId}/certificates`, { params }).then(r => r.data)

export const retryFailed = (jobId) =>
  api.post(`/api/jobs/${jobId}/retry-failed`).then(r => r.data)

export const downloadJobZip = (jobId) =>
  `/api/jobs/${jobId}/download`   // direct browser download link

// ── Certificates ─────────────────────────────────────────────────────────────

export const getCertificate = (certDbId) =>
  api.get(`/api/certificates/${certDbId}`).then(r => r.data)

export const downloadCertificateUrl = (certDbId) =>
  `/api/certificates/${certDbId}/download`

// ── Dashboard ────────────────────────────────────────────────────────────────

export const getDashboard = () => api.get('/api/dashboard').then(r => r.data)

// ── CSV utilities ─────────────────────────────────────────────────────────────

export const validateCSV = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/api/csv/validate', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const csvTemplateUrl = () => '/api/csv/template'

// ── Health ────────────────────────────────────────────────────────────────────

export const checkHealth = () => api.get('/health').then(r => r.data)
