import { useState } from 'react'

function EyeIcon({ off }) {
  if (off) {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-4 w-4"
        aria-hidden="true"
      >
        <path d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395" />
        <path d="M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774" />
        <path d="M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
      </svg>
    )
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
      <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  )
}

export default function TextField({
  id,
  label,
  type = 'text',
  value,
  onChange,
  autoComplete,
  required = false,
  placeholder,
  error,
  disabled = false,
}) {
  const [passwordVisible, setPasswordVisible] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && passwordVisible ? 'text' : type

  return (
    <label className="block" htmlFor={id}>
      <span className="text-sm font-medium text-ink-800">{label}</span>
      <span className="relative mt-1.5 block">
        <input
          id={id}
          name={id}
          type={inputType}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required={required}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full rounded-lg border px-3 py-2.5 text-sm text-ink-950 outline-none transition-colors placeholder:text-ink-400 focus:border-ink-700 ${
            isPassword ? 'pr-10' : ''
          } ${disabled ? 'cursor-not-allowed bg-ink-50 text-ink-700' : 'bg-paper-raised'} ${
            error ? 'border-danger-600' : 'border-ink-300'
          }`}
        />
        {isPassword ? (
          <button
            type="button"
            disabled={disabled}
            onClick={(event) => {
              event.preventDefault()
              setPasswordVisible((visible) => !visible)
            }}
            className="absolute inset-y-0 right-0 flex items-center px-2.5 text-ink-500 transition-colors hover:text-ink-800 disabled:cursor-not-allowed disabled:text-ink-400"
            aria-label={passwordVisible ? 'Hide password' : 'Show password'}
            aria-pressed={passwordVisible}
            title={passwordVisible ? 'Hide password' : 'Show password'}
          >
            <EyeIcon off={passwordVisible} />
          </button>
        ) : null}
      </span>
      {error ? <span className="mt-1 block text-xs text-danger-700">{error}</span> : null}
    </label>
  )
}
