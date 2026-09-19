export default function LoadingSpinner({ size = 20, className = '' }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-ink-200 border-t-ink-700 ${className}`}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  )
}
