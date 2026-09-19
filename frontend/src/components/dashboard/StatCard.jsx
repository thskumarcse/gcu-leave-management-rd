export default function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-paper-raised p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold text-ink-950">{value}</p>
      {hint ? <p className="mt-1 text-xs text-ink-500">{hint}</p> : null}
    </div>
  )
}
