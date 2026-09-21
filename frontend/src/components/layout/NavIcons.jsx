const ICONS = {
  home: (
    <>
      <path d="M4.5 11.2 12 4.8l7.5 6.4" />
      <path d="M6.5 10.2V19a1.5 1.5 0 0 0 1.5 1.5h3.2v-5.2h2.6V20.5H16A1.5 1.5 0 0 0 17.5 19v-8.8" />
    </>
  ),
  dashboard: (
    <>
      <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.8" />
      <rect x="13" y="3.5" width="7.5" height="7.5" rx="1.8" />
      <rect x="3.5" y="13" width="7.5" height="7.5" rx="1.8" />
      <rect x="13" y="13" width="7.5" height="7.5" rx="1.8" />
    </>
  ),
  apply: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2.5" />
      <path d="M8 3.5v3M16 3.5v3M4 9.5h16" />
      <path d="M12 13v4M10 15h4" />
    </>
  ),
  leaves: (
    <>
      <rect x="6" y="4" width="13" height="16" rx="2" />
      <path d="M9 8.5h7M9 12h7M9 15.5h4.5" />
      <path d="M5 7v11.5A2.5 2.5 0 0 0 7.5 21H16" />
    </>
  ),
  approver: (
    <>
      <path d="M12 3.5 19.5 7v5.2c0 4.3-2.9 7.4-7.5 8.8-4.6-1.4-7.5-4.5-7.5-8.8V7L12 3.5Z" />
      <path d="m9 12 2.1 2.1L15.2 10" />
    </>
  ),
  approvals: (
    <>
      <path d="M4.5 13.5h15v6.2A1.8 1.8 0 0 1 17.7 21.5H6.3a1.8 1.8 0 0 1-1.8-1.8v-6.2Z" />
      <path d="M4.5 13.5 8 8.5h8l3.5 5" />
      <path d="M9.5 8.5 11 4.5h2l1.5 4" />
    </>
  ),
  directory: (
    <>
      <circle cx="9" cy="8" r="2.4" />
      <path d="M4.8 16.8c.4-2.4 2.1-3.7 4.2-3.7s3.8 1.3 4.2 3.7" />
      <circle cx="16" cy="8.4" r="2.1" />
      <path d="M15.2 13.2c1.8.2 3.2 1.4 3.6 3.4" />
    </>
  ),
  profile: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="9.2" r="2.4" />
      <path d="M7.4 17.2c.8-2.3 2.4-3.4 4.6-3.4s3.8 1.1 4.6 3.4" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 4.2v1.8M12 18v1.8M4.2 12h1.8M18 12h1.8M6.3 6.3l1.3 1.3M16.4 16.4l1.3 1.3M17.7 6.3l-1.3 1.3M7.6 16.4l-1.3 1.3" />
    </>
  ),
  analytics: (
    <>
      <path d="M4.5 19.5h15" />
      <rect x="6" y="11" width="3" height="8.5" rx="1" />
      <rect x="10.5" y="7" width="3" height="12.5" rx="1" />
      <rect x="15" y="9.5" width="3" height="10" rx="1" />
    </>
  ),
}

export default function NavIcon({ name, className = 'h-6 w-6' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={className}
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICONS[name] || ICONS.dashboard}
    </svg>
  )
}
