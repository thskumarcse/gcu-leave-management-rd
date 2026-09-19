# GCU Leave Management — Frontend

React + Vite + Tailwind CSS frontend for the Girijananda Chowdhury University
Leave Management System.

## Status: complete

Employees sign in with their employee ID (no registration). After the
forced password change they can apply for leave (including casual leave
half-days), track balances, and — if they are an HOD, Approver 1, VC, or
admin — use the approvals inbox, approver dashboard, notifications bell,
and admin pages. Admins also get **Settings** (`/settings`) to assign
roles and set leave-type values.

## Stack

- React 19 + Vite
- Tailwind CSS v4 (via `@tailwindcss/vite`, no separate `tailwind.config.js`
  needed — tokens live in `src/styles/index.css` under `@theme`)
- React Router
- Axios
- Recharts (approver dashboard and admin reports)

## Project structure

```
src/
├── components/
│   ├── common/       # Button, Card, Badge, LoadingSpinner
│   ├── layout/        # BrandHeader, NotificationBell
│   ├── forms/          # TextField, TextArea
│   ├── tables/         # Table
│   └── dashboard/       # StatCard
├── layouts/            # AppShell (role-aware)
├── pages/
│   ├── auth/            # Login, ChangePassword
│   ├── employee/        # Directory, profile, apply/list leave
│   ├── approvals/       # Inbox + approver dashboard
│   └── admin/           # Settings, employees, leave types, approvers, reports, audit
├── services/            # apiClient and one file per API area
├── context/              # auth context
├── utils/
├── routes/               # RequireAuth, RequireAdmin, RequireApprover
├── assets/
└── styles/index.css      # Tailwind import + design tokens
```

## Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app runs at `http://127.0.0.1:5173`. It expects the backend at the URL in
`.env` (`VITE_API_BASE_URL`, defaults to `http://127.0.0.1:8000/api/v1`).

## Design system

Colour, type and layout tokens are defined once in `src/styles/index.css`:

- **Ink navy** (`ink-950` → `ink-50`) — institutional colour, used for the
  header, primary text and primary actions.
- **Paper** — a cool off-white background, not pure white or warm cream.
- **Convocation gold** (`gold-*`) — the single accent colour; reserved for
  emphasis, not decoration.
- **Status colours** (`success-*`, `danger-*`, `warn-*`) — muted, used for
  leave/approval status badges.
- **Type** — `Source Serif 4` for headings (`font-display`), `Inter` for
  body/UI text.

Reusable primitives live in `src/components/common/` (`Card`, `Badge`,
`Button`, `LoadingSpinner`).

## Verifying

1. Start the backend (see `backend/README.md`) so `GET /api/v1/health/`
   responds.
2. Run `npm run dev` here.
3. Open `http://127.0.0.1:5173`, sign in with an employee ID and `gcu@123`,
   change the password, then apply for leave, open Approvals (if you have a
   role), and Admin (if `is_admin`).
