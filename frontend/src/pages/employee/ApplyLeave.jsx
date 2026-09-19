import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../../layouts/AppShell'
import Card from '../../components/common/Card'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import TextArea from '../../components/forms/TextArea'
import { applyLeave, fetchLeaveTypes } from '../../services/leaveService'
import { countLeaveDays, formatLeaveDays } from '../../utils/leaveStatus'

const CL_SESSIONS = [
  { value: 'FULL_DAY', label: 'Full day' },
  { value: 'FIRST_HALF', label: 'First Half' },
  { value: 'SECOND_HALF', label: 'Second Half' },
]

function fieldError(err, field) {
  const errors = err?.response?.data?.errors
  if (!errors) return ''
  const value = errors[field]
  if (Array.isArray(value)) return value[0]
  return value || ''
}

function localISODate() {
  const now = new Date()
  const pad = (part) => String(part).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export default function ApplyLeave() {
  const navigate = useNavigate()
  const [types, setTypes] = useState([])
  const [leaveTypeId, setLeaveTypeId] = useState('')
  const [session, setSession] = useState('FULL_DAY')
  const [applicationDate] = useState(() => localISODate())
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [reason, setReason] = useState('')
  const [loadingTypes, setLoadingTypes] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const body = await fetchLeaveTypes()
        if (!cancelled) {
          setTypes(body.data)
          if (body.data[0]) setLeaveTypeId(String(body.data[0].id))
        }
      } catch (err) {
        if (!cancelled) {
          setFormError(err?.response?.data?.message || 'Could not load leave types.')
        }
      } finally {
        if (!cancelled) setLoadingTypes(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const selectedType = types.find((item) => String(item.id) === String(leaveTypeId))
  const isCasual = selectedType?.code === 'CL'
  const isHalfDay = isCasual && (session === 'FIRST_HALF' || session === 'SECOND_HALF')
  const days = useMemo(() => {
    if (isHalfDay) return countLeaveDays(startDate, startDate, session)
    return countLeaveDays(startDate, endDate, session)
  }, [isHalfDay, startDate, endDate, session])
  const remaining = selectedType?.remaining
  const overBalance =
    remaining != null && days != null && Number(days) > Number(remaining)

  function handleLeaveTypeChange(event) {
    const nextId = event.target.value
    setLeaveTypeId(nextId)
    const nextType = types.find((item) => String(item.id) === String(nextId))
    if (nextType?.code !== 'CL') setSession('FULL_DAY')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFieldErrors({})
    if (remaining != null && days != null && Number(days) > Number(remaining)) {
      setFormError(
        `${selectedType?.name || 'This leave type'} has ${remaining} day(s) remaining.`,
      )
      setFieldErrors({
        leave_type_id: 'Not enough balance for this leave type.',
      })
      return
    }
    setSubmitting(true)
    const leaveEnd = isHalfDay ? startDate : endDate
    try {
      await applyLeave({
        leave_type_id: Number(leaveTypeId),
        start_date: startDate,
        end_date: leaveEnd,
        session: isCasual ? session : 'FULL_DAY',
        reason,
      })
      navigate('/leaves', { replace: true })
    } catch (err) {
      setFormError(err?.response?.data?.message || 'Could not submit the application.')
      setFieldErrors({
        leave_type_id: fieldError(err, 'leave_type_id'),
        session: fieldError(err, 'session'),
        start_date: fieldError(err, 'start_date'),
        end_date: fieldError(err, 'end_date'),
        reason: fieldError(err, 'reason'),
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Apply for leave</h2>
      <p className="mt-1 max-w-2xl text-sm text-ink-700">
        Submit a request against your employee record. Faculty applications go to the Head of
        Department, then the Vice-Chancellor. HOD applicants go to the Vice-Chancellor only.
        Staff applications go Approver 1 → Approver 2 → Vice-Chancellor.
      </p>

      <Card className="mt-8 max-w-xl">
        {loadingTypes ? (
          <div className="flex items-center gap-2 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading leave types…
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            {formError ? (
              <p className="rounded-lg bg-danger-100 px-3 py-2 text-sm text-danger-700">{formError}</p>
            ) : null}

            <TextField
              id="requested_on"
              label="Date of application"
              type="date"
              value={applicationDate}
              disabled
            />

            <label className="block" htmlFor="leave_type_id">
              <span className="text-sm font-medium text-ink-800">Leave type</span>
              <select
                id="leave_type_id"
                value={leaveTypeId}
                onChange={handleLeaveTypeChange}
                required
                className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950 outline-none focus:border-ink-700"
              >
                {types.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.code})
                    {item.remaining != null && item.max_days_per_year != null
                      ? ` · ${item.remaining ?? 0} of ${item.max_days_per_year} left`
                      : ''}
                  </option>
                ))}
              </select>
              {selectedType?.description ? (
                <span className="mt-1 block text-xs text-ink-500">{selectedType.description}</span>
              ) : null}
              {selectedType?.remaining != null ? (
                <span className="mt-1 block text-xs text-ink-600">
                  Used this year: {selectedType.used ?? 0} day
                  {selectedType.used === 1 ? '' : 's'} · remaining {selectedType.remaining ?? 0}
                </span>
              ) : null}
              {fieldErrors.leave_type_id ? (
                <span className="mt-1 block text-xs text-danger-700">{fieldErrors.leave_type_id}</span>
              ) : null}
            </label>

            {isCasual ? (
              <fieldset>
                <legend className="text-sm font-medium text-ink-800">Casual leave type</legend>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {CL_SESSIONS.map((item) => (
                    <label
                      key={item.value}
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                        session === item.value
                          ? 'border-ink-800 bg-ink-50 text-ink-950'
                          : 'border-ink-300 bg-paper-raised text-ink-800'
                      }`}
                    >
                      <input
                        type="radio"
                        name="session"
                        value={item.value}
                        checked={session === item.value}
                        onChange={() => {
                          setSession(item.value)
                          if (item.value !== 'FULL_DAY' && startDate) setEndDate(startDate)
                        }}
                      />
                      {item.label}
                    </label>
                  ))}
                </div>
                {fieldErrors.session ? (
                  <span className="mt-1 block text-xs text-danger-700">{fieldErrors.session}</span>
                ) : null}
              </fieldset>
            ) : null}

            <div className={`grid gap-4 ${isHalfDay ? '' : 'sm:grid-cols-2'}`}>
              <TextField
                id="start_date"
                label={isHalfDay ? 'Leave date' : 'From'}
                type="date"
                value={startDate}
                onChange={(event) => {
                  const value = event.target.value
                  setStartDate(value)
                  if (isHalfDay) setEndDate(value)
                }}
                required
                error={fieldErrors.start_date}
              />
              {isHalfDay ? null : (
                <TextField
                  id="end_date"
                  label="To"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  required
                  error={fieldErrors.end_date}
                />
              )}
            </div>

            <p className="text-sm text-ink-600">
              Duration: <span className="font-medium text-ink-950">{formatLeaveDays(days)}</span>
            </p>
            {overBalance ? (
              <p className="text-sm text-danger-700">
                This request is for {formatLeaveDays(days)}, but only {remaining} day
                {Number(remaining) === 1 ? '' : 's'} remain.
              </p>
            ) : null}

            <TextArea
              id="reason"
              label="Reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
              placeholder="Briefly explain why you need this leave."
              error={fieldErrors.reason}
            />

            <Button type="submit" disabled={submitting || !types.length || overBalance}>
              {submitting ? 'Submitting…' : 'Submit application'}
            </Button>
          </form>
        )}
      </Card>
    </AppShell>
  )
}
