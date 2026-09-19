const VARIANT_CLASSES = {
  neutral: 'bg-ink-100 text-ink-800',
  success: 'bg-success-100 text-success-700',
  danger: 'bg-danger-100 text-danger-700',
  warn: 'bg-warn-100 text-warn-700',
  gold: 'bg-gold-100 text-gold-700',
}

/**
 * Small status pill. `variant` picks the colour pairing; `dot` renders a
 * leading status dot for at-a-glance scanning in tables and cards.
 */
export default function Badge({ children, variant = 'neutral', dot = false, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}
