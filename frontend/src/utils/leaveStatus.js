const VARIANT = {
  PENDING: 'warn',
  APPROVED: 'success',
  REJECTED: 'danger',
  CANCELLED: 'neutral',
}

const STEP_LABEL = {
  HOD: 'HOD',
  VC: 'Vice-Chancellor',
  APPROVER_1: 'Approver 1',
  APPROVER_2: 'Approver 2',
}

export function leaveStatusVariant(status) {
  return VARIANT[status] || 'neutral'
}

export function stepLabel(step) {
  if (!step) return '—'
  return STEP_LABEL[step] || step
}

export function leaveStatusLabel(status, currentStep) {
  if (!status) return '—'
  if (status === 'PENDING' && currentStep) {
    return `Pending with ${stepLabel(currentStep)}`
  }
  return status.charAt(0) + status.slice(1).toLowerCase()
}

export function countLeaveDays(start, end, session = 'FULL_DAY') {
  if (!start || !end) return 0
  if (session === 'FIRST_HALF' || session === 'SECOND_HALF') return 0.5
  const from = new Date(`${start}T00:00:00`)
  const to = new Date(`${end}T00:00:00`)
  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime()) || to < from) return 0
  return Math.round((to - from) / 86400000) + 1
}

export function formatLeaveDays(days) {
  const value = Number(days)
  if (!Number.isFinite(value) || value <= 0) return '—'
  return `${value} day${value === 1 ? '' : 's'}`
}

export function sessionLabel(session) {
  if (session === 'FIRST_HALF') return 'First Half'
  if (session === 'SECOND_HALF') return 'Second Half'
  if (session === 'FULL_DAY') return 'Full day'
  return ''
}
