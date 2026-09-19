export default function TextArea({
  id,
  label,
  value,
  onChange,
  required = false,
  placeholder,
  error,
  rows = 4,
}) {
  return (
    <label className="block" htmlFor={id}>
      <span className="text-sm font-medium text-ink-800">{label}</span>
      <textarea
        id={id}
        name={id}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        rows={rows}
        className={`mt-1.5 w-full rounded-lg border bg-paper-raised px-3 py-2.5 text-sm text-ink-950 outline-none transition-colors placeholder:text-ink-400 focus:border-ink-700 ${
          error ? 'border-danger-600' : 'border-ink-300'
        }`}
      />
      {error ? <span className="mt-1 block text-xs text-danger-700">{error}</span> : null}
    </label>
  )
}
