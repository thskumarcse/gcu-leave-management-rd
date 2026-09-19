import { useEffect, useState } from 'react'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import { fetchApprovalEmployeeLeaves } from '../../services/approvalService'

export default function ApplicantLeaveSummary({ applicationId, highlightCode }) {
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchApprovalEmployeeLeaves(applicationId, { page: 1, pageSize: 1 })
        if (!cancelled) setPayload(body.data)
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || "Could not load this employee's leave record.")
          setPayload(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [applicationId])

  return (
    <div>
      <h3 className="font-display text-lg font-semibold text-ink-950">
        Leave balance this year
      </h3>
      {payload?.year ? (
        <p className="mt-1 text-sm text-ink-600">Usage this year for the applicant ({payload.year}).</p>
      ) : (
        <p className="mt-1 text-sm text-ink-600">Usage this year for the applicant.</p>
      )}

      {loading && !payload ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-ink-600">
          <LoadingSpinner size={14} />
          Loading leave balance…
        </div>
      ) : null}
      {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}

      {payload?.balances?.length ? (
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {payload.balances.map((item) => {
            const highlighted = highlightCode && item.code === highlightCode
            return (
              <li
                key={item.id || item.code}
                className={`rounded-lg border px-3 py-2 ${
                  highlighted ? 'border-gold-400 bg-gold-100' : 'border-ink-100'
                }`}
              >
                <p className="text-sm font-medium text-ink-950">{item.name}</p>
                <p className="text-xs text-ink-600">
                  {item.max_days_per_year == null
                    ? `${item.used} day${item.used === 1 ? '' : 's'} used · no annual cap`
                    : `${item.remaining} of ${item.max_days_per_year} remaining (${item.used} used)`}
                </p>
              </li>
            )
          })}
        </ul>
      ) : !loading && !error ? (
        <p className="mt-4 text-sm text-ink-600">No leave balances on record.</p>
      ) : null}
    </div>
  )
}
