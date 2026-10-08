/**
 * useJobPolling — polls GET /api/jobs/{jobId} until job is complete.
 *
 * Automatically stops when status is COMPLETED / COMPLETED_WITH_ERRORS / FAILED.
 * Returns { job, loading, error }.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob } from '../services/api'
import { isJobActive } from '../services/utils'

const POLL_INTERVAL_MS = 1500

export function useJobPolling(jobId) {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)
  const mountedRef = useRef(true)

  const fetch = useCallback(async () => {
    if (!jobId) return
    try {
      const data = await getJob(jobId)
      if (!mountedRef.current) return
      setJob(data)
      setError(null)

      // Keep polling if job is still active
      if (isJobActive(data.status)) {
        timerRef.current = setTimeout(fetch, POLL_INTERVAL_MS)
      }
    } catch (err) {
      if (!mountedRef.current) return
      setError(err.displayMessage || 'Failed to load job')
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    mountedRef.current = true
    setLoading(true)
    setJob(null)
    setError(null)
    fetch()

    return () => {
      mountedRef.current = false
      clearTimeout(timerRef.current)
    }
  }, [fetch])

  const refresh = useCallback(() => {
    clearTimeout(timerRef.current)
    fetch()
  }, [fetch])

  return { job, loading, error, refresh }
}
