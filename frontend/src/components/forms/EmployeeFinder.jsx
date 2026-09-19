import { useEffect, useRef, useState } from 'react'
import { fetchAdminEmployees } from '../../services/adminService'

const INPUT_CLASS =
  'mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950'

export default function EmployeeFinder({
  id,
  label,
  value,
  onChange,
  excludeId = '',
  disabled = false,
}) {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [open, setOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const boxRef = useRef(null)

  useEffect(() => {
    function onDoc(event) {
      if (boxRef.current && !boxRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  useEffect(() => {
    if (!open || disabled) return undefined
    let cancelled = false
    const handle = setTimeout(
      async () => {
        setSearching(true)
        try {
          const body = await fetchAdminEmployees({
            q: query.trim(),
            status: 'Active',
            page: 1,
            pageSize: 20,
          })
          if (!cancelled) {
            setMatches(
              (body.data.results || []).filter((row) => row.emp_id !== excludeId),
            )
          }
        } catch {
          if (!cancelled) setMatches([])
        } finally {
          if (!cancelled) setSearching(false)
        }
      },
      query.trim() ? 200 : 0,
    )
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [query, open, disabled, excludeId])

  function pick(employee) {
    onChange(employee)
    setQuery('')
    setOpen(false)
    setMatches([])
  }

  function clear() {
    onChange(null)
    setQuery('')
    setMatches([])
    setOpen(false)
  }

  return (
    <div ref={boxRef} className="relative">
      <label className="block" htmlFor={id}>
        <span className="text-sm font-medium text-ink-800">{label}</span>
      </label>
      {value ? (
        <div className="mt-1.5 flex items-center justify-between gap-2 rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink-950">
              {value.name}{' '}
              <span className="font-normal text-ink-500">({value.emp_id})</span>
            </p>
            <p className="truncate text-xs text-ink-500">
              {value.sub_department || value.department || 'No department'}
              {value.designation ? ` · ${value.designation}` : ''}
            </p>
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={clear}
            className="shrink-0 text-xs font-medium text-ink-600 hover:text-ink-950 disabled:opacity-50"
          >
            Change
          </button>
        </div>
      ) : (
        <>
          <input
            id={id}
            type="text"
            value={query}
            disabled={disabled}
            placeholder="Search name or employee ID…"
            autoComplete="off"
            onChange={(event) => {
              setQuery(event.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            className={`${INPUT_CLASS} ${disabled ? 'cursor-not-allowed bg-ink-50' : ''}`}
          />
          {open ? (
            <ul
              className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-ink-200 bg-paper-raised shadow-lg"
              role="listbox"
            >
              {searching ? (
                <li className="px-3 py-2 text-xs text-ink-500">Searching directory…</li>
              ) : matches.length ? (
                matches.map((employee) => (
                  <li key={employee.emp_id} role="option">
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-ink-50"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => pick(employee)}
                    >
                      <p className="truncate text-sm font-medium text-ink-950">
                        {employee.name}{' '}
                        <span className="font-normal text-ink-500">({employee.emp_id})</span>
                      </p>
                      <p className="truncate text-xs text-ink-500">
                        {employee.sub_department || employee.department || 'No department'}
                        {employee.designation ? ` · ${employee.designation}` : ''}
                      </p>
                    </button>
                  </li>
                ))
              ) : (
                <li className="px-3 py-2 text-xs text-ink-500">
                  {query.trim()
                    ? 'No matching employees.'
                    : 'Type a name or employee ID to search the directory.'}
                </li>
              )}
              {matches.length >= 20 ? (
                <li className="border-t border-ink-100 px-3 py-2 text-xs text-ink-500">
                  Type to search the rest of the directory.
                </li>
              ) : null}
            </ul>
          ) : null}
        </>
      )}
    </div>
  )
}
