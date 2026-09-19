const VARIANT = {
  primary:
    'bg-ink-900 text-white hover:bg-ink-800 disabled:bg-ink-400',
  secondary:
    'border border-ink-300 bg-paper-raised text-ink-800 hover:bg-ink-50 disabled:opacity-50',
}

export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  className = '',
  disabled = false,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${VARIANT[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
