/**
 * Base content card. Uses a hairline border rather than a heavy drop
 * shadow, so it reads calm at scale on dashboards with many cards.
 */
export default function Card({ children, className = '', padded = true }) {
  return (
    <div
      className={`rounded-xl border border-ink-200 bg-paper-raised ${padded ? 'p-6' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
