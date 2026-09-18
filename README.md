<div align="center">

# Resolve

**Complaint and case resolution for institutions**

Every complaint gets an owner, a clock, and an answer.

[![CI](https://github.com/basgenix4u/uni-complaints/actions/workflows/ci.yml/badge.svg)](https://github.com/basgenix4u/uni-complaints/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

</div>

---

## What this is

Complaints at most institutions arrive by paper, WhatsApp and physical queue, then disappear. There is no ticket, no named owner, no deadline and no record — so nothing can be chased, measured or escalated.

Resolve gives every complaint a ticket number, a department, a named officer and a response deadline, and escalates automatically when that deadline passes. Students track progress without phoning anyone. Administrators see what is overdue and who owns it.

It is **multi-tenant**: one deployment serves many institutions, each with its own departments, service levels, branding and users. No institution can see another's data.

## Who uses it

| Role | What they do |
| --- | --- |
| Student | Files complaints, tracks them, replies, rates the outcome |
| Officer | Works a queue, replies, moves complaints through their states |
| Department head | Assigns ownership, sees department performance |
| Institution admin | Manages staff, departments, service levels and settings |
| Platform admin | Provisions institutions across the deployment |

## How a complaint moves

```
submitted → acknowledged → in_progress → resolved → closed
                    ↘ awaiting_student ↗
                    ↘ declined
```

Transitions are validated on the server. Resolving requires an explanation and declining requires a reason, both of which the student sees. Every change is written to an append-only audit trail.

## Service levels

Deadlines count **working hours only**, skipping weekends and public holidays. A complaint filed at 18:00 on Friday against an eight hour target is due Monday at 16:00 — not Saturday at 02:00, which would have breached before anyone returned to work.

Priority scales the target: urgent is a quarter of the standard window, low is double.

When a deadline passes, `flask escalate` raises the complaint, notifies the student and department heads, and records it. The sweep is idempotent, so it is safe to run on a schedule.

---

## Running it locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # then set SECRET_KEY and JWT_SECRET_KEY
flask seed --demo             # creates an institution and sample accounts
python run.py                 # http://localhost:5000
```

`flask seed` creates the first platform administrator. This cannot be done through the API, because creating staff requires an existing administrator.

Demo accounts created by `--demo`:

| Email | Password | Role |
| --- | --- | --- |
| `admin@resolve.ng` | `ChangeMe123` | Platform admin |
| `admin@demo.edu.ng` | `Password123` | Institution admin |
| `amina@demo.edu.ng` | `Password123` | Student |

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

The dev server proxies `/api` to the backend, so no cross-origin setup is needed.

### Tests

```bash
cd backend && pytest                    # 89 tests
cd frontend && npm run lint && npm run build

# Browser journeys, desktop and mobile, against a running API
cd backend && RATELIMIT_ENABLED=false flask seed --demo && \
  RATELIMIT_ENABLED=false python run.py &
cd frontend && npm run test:e2e         # 34 journeys
```

The browser suite signs in once per role through the API and replays the
session, rather than driving the login form repeatedly. Logging in on every
test would exhaust the rate limit, which is a protection worth keeping.

---

## Scheduled commands

| Command | Purpose | Suggested interval |
| --- | --- | --- |
| `flask escalate` | Escalate complaints past their deadline | every 30 minutes |
| `flask send-queue` | Deliver queued email and texts | every 5 minutes |

Both are idempotent and safe to run concurrently with the web process.

---

## Security

| Concern | Approach |
| --- | --- |
| Tenant isolation | Every tenant table carries `institution_id`; queries are scoped by middleware, and fail closed if no tenant is bound |
| Authorisation | Role hierarchy enforced server side on every route, never in the client |
| Revoked access | Tokens are checked against the stored user each request, so deactivation takes effect immediately |
| Account enumeration | Login returns one message for both an unknown email and a wrong password |
| Brute force | Rate limits on registration, login and password change |
| Uploads | Allow-list of types, file signatures verified against the declared type, generated filenames, stored outside the served tree |
| File access | Served only through an authorised endpoint, so a guessed URL reveals nothing |
| Private notes | Filtered for students in the API, and students cannot set the flag |
| Transport | Security headers on every response; personal data is never cached |
| Secrets | Production refuses to start with development defaults |

---

## Deployment

```bash
docker build -t resolve-api ./backend
docker run -p 5000:5000 --env-file backend/.env resolve-api
```

The image runs as an unprivileged user, serves through gunicorn, and exposes `/api/ready` as a health check that confirms the database answers.

For the frontend, `npm run build` produces static files for any CDN or static host. Set `VITE_API_URL` to the API origin.

### Required configuration

| Variable | Notes |
| --- | --- |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | PostgreSQL in production; SQLite is for local work only |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |
| `UPLOAD_DIR` | Must be a persistent volume |
| `SMTP_*`, `MAIL_FROM` | Without these, messages queue rather than being discarded |
| `SMS_PROVIDER` | `termii`, `africastalking`, or `console` for local work |

---

## Design

The interface is built to a written specification covering colour, type, spacing, motion, voice and accessibility.

Two decisions worth calling out:

**Status is never colour alone.** Simulating deuteranopia, "in progress" amber and "declined" red measure 1.19 contrast against each other, and "submitted" blue against "closed" slate measures 1.20 — effectively identical. A colour-blind student could not tell *being worked on* from *rejected*. Every status renders an icon and a text label, enforced by the component's API.

**Dates are written day-first with a named month.** A numeric date is read differently in Nigeria and the United States, and that ambiguity is unacceptable on a response deadline.

All text meets WCAG 2.2 AA. The primary action measures 6.45:1.

---

## Project layout

```
backend/
  app/
    models/       institution, user, complaint, attachment, message
    routes/       auth, complaints, attachments, dashboard,
                  notifications, admin, platform
    services/     tickets, sla, storage, delivery, notifications
    security.py   role checks and tenant scoping
  tests/          89 tests
frontend/
  e2e/            34 browser journeys
  src/
    components/   ui primitives, complaint views
    pages/        auth, public, student, admin
    services/     API client
    styles/       design tokens
```

---

## Licence

[MIT](./LICENSE)
