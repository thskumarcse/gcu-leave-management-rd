# GCU Leave Management — Backend

Django + Django REST Framework backend for the Girijananda Chowdhury
University Leave Management System.

## Status: complete

Employee master data, JWT login (employee ID, default password `gcu@123`,
forced change), leave apply/list, faculty HOD → VC and staff Approver 1 → VC
chains, approver dashboard, in-app notifications, and `/api/v1/admin/`
(employees, leave types, approvers, reports, audit) are in place.

There is no self-serve registration. Keep import files in `data/`.

## Stack

- Django 6.1
- Django REST Framework
- djangorestframework-simplejwt (installed, wired up fully in Phase 3)
- django-cors-headers
- SQLite (default), designed to swap to PostgreSQL later without a redesign
- python-dotenv for `.env` loading

## Project structure

```
backend/
├── manage.py
├── config/
│   ├── settings.py     # env-driven: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS, DRF, JWT
│   ├── urls.py          # mounts /admin/ and /api/v1/
│   └── api_urls.py       # /api/v1/ route aggregator — one include() per app
├── apps/
│   ├── core/              # health, dashboard, admin APIs
│   ├── employees/          # Employee model + import_employees
│   ├── accounts/            # JWT login, forced password change, is_admin
│   ├── leaves/                # leave types, applications, import_emp_leaves
│   ├── approvals/              # HOD / Approver 1 / VC chains
│   └── notifications/           # in-app notifications
├── data/
│   ├── employee.csv
│   └── emp_leaves.xls
├── requirements.txt
├── .env.example
└── db.sqlite3               # created by `migrate`, not committed
```

## Setup (Windows)

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000`. `CORS_ALLOWED_ORIGINS` in `.env`
must include the frontend's origin (`http://127.0.0.1:5173` by default —
already set in `.env.example`).

## Configuration

All configuration is read from environment variables (via `.env` in
development), never hard-coded:

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | long random string |
| `DEBUG` | Debug mode toggle | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DATABASE_URL` | Reserved for the future Postgres switch (unused while on SQLite) | *(blank)* |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins | `http://127.0.0.1:5173` |
| `DEFAULT_EMPLOYEE_PASSWORD` | First-login password | `gcu@123` |
| `VC_EMP_ID` | Employee ID used as Vice-Chancellor | `GCU020004` |

## API response format

Every endpoint returns a consistent envelope:

```json
{ "success": true, "message": "...", "data": { ... } }
{ "success": false, "message": "...", "errors": { "field": ["..."] } }
```

`GET /api/v1/health/` is the first example of this and is unauthenticated
(`AllowAny`) — every other endpoint requires a valid JWT by default
(`DEFAULT_PERMISSION_CLASSES = IsAuthenticated` plus a forced password
change). Login, token refresh, and change-password are the exceptions.
There is no public registration endpoint.

## First-time setup after migrate

```bat
python manage.py import_employees
python manage.py import_emp_leaves
python manage.py seed_data
python manage.py test
```

`seed_data` runs `sync_approvers --route-pending`: HODs from designations,
staff Approver 1 per department, VC from `VC_EMP_ID`, admin access for the
VC, and routing of unrouted pending leave (without sending notifications).

Faculty leave waits on the department HOD, then the VC. Staff leave waits
on Approver 1, then the VC. Casual leave may be First Half, Second Half, or
Full day (0.5 / 1+ days). Date of application is stored as `requested_on`
and is always today — it is not chosen on the form.

## Verifying Phase 1

```bat
python manage.py check
python manage.py migrate
python manage.py runserver
```

Then, in a browser or via curl:

```bash
curl http://127.0.0.1:8000/api/v1/health/
```

Expected:

```json
{"success": true, "message": "GCU Leave Management API is running.", "data": {"status": "ok", "service": "gcu-leave-management-backend", "debug": true}}
```

With the frontend's `npm run dev` running at the same time, `http://127.0.0.1:5173`
should show **Connected** with this same payload.

## Employee master data (Phase 2)

`Employee` (`apps/employees/models.py`) is the master record for everyone at
the university — separate from login accounts, which come in Phase 3.
`emp_id` and `email` are unique; `designation_type` is `FACULTY` or `STAFF`;
`status` is `Active` or `Inactive`.

### Importing the CSV

```bat
python manage.py import_employees
```

Reads `data/employee.csv` by default (`--file path\to\other.csv` to use a
different file). The import logic lives in `apps/employees/services.py`,
not the management command itself, so it can be reused later (e.g. from an
admin-triggered API endpoint) without duplicating validation rules.

For each row it validates:
- all required columns are present in the file at all (fails the whole
  import with a clear error if not — e.g. a missing `designation_type`
  column)
- required fields aren't blank
- `dob` and `joining_date` parse as `YYYY-MM-DD`
- `designation_type` is `FACULTY` or `STAFF`
- `status` is `Active` or `Inactive`
- `email` isn't already used by a *different* `emp_id`

Rows matching an existing `emp_id` are **updated in place**
(`update_or_create`), never duplicated — re-running the command on the same
file is safe and idempotent. A row with a duplicate `emp_id` *within the
same file* is skipped (first occurrence wins). Any row that fails
validation is skipped with a reason; valid rows in the same file still
import. The command prints a summary (`Imported (new)` / `Updated` /
`Skipped`) plus the reason for every skipped row, and exits non-zero if the
CSV file is missing or malformed at the column level.

### Verifying Phase 2

```bat
python manage.py migrate
python manage.py import_employees
python manage.py test apps.employees
```

The test suite (`apps/employees/tests.py`) covers: importing new rows,
re-importing without creating duplicates, an invalid `designation_type`,
an invalid date, a duplicate `emp_id` within one file, an email reused
across two different `emp_id`s, and that three repeated imports of the same
file still leave exactly the original row count.

You can also browse the imported data at `/admin/` after creating a
superuser (`python manage.py createsuperuser` — available now since
`django.contrib.auth` is part of Django's default apps; a dedicated `User`
model tied to `Employee` arrives in Phase 3).
