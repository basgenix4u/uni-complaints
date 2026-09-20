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
flask db upgrade              # builds the schema
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
cd backend && pytest                    # 152 tests
cd frontend && npm run lint && npm run build

# Browser journeys, desktop and mobile, against a running API
cd backend && RATELIMIT_ENABLED=false flask seed --demo && \
  RATELIMIT_ENABLED=false python run.py &
cd frontend && npm run test:e2e         # 52 journeys
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
| `flask purge-expired` | Delete complaints past the retention period | nightly |

Both are idempotent and safe to run concurrently with the web process.

---

## Security

| Concern | Approach |
| --- | --- |
| Tenant isolation | Every tenant table carries `institution_id`; queries are scoped by middleware, and fail closed if no tenant is bound |
| Authorisation | Role hierarchy enforced server side on every route, never in the client |
| Revoked access | Tokens are checked against the stored user each request, so deactivation takes effect immediately |
| Account enumeration | Login returns one message for both an unknown email and a wrong password |
| Brute force | Rate limits on registration, login and password reset |
| Account discovery | A reset request answers identically whether or not the address is registered, which for a complaints system also hides who has complained |
| Reset tokens | Only a hash is stored, they expire after an hour, are single use, and requesting a new one retires the old |
| Uploads | Allow-list of types, file signatures verified against the declared type, generated filenames, stored outside the served tree |
| File access | Served only through an authorised endpoint, so a guessed URL reveals nothing |
| Private notes | Filtered for students in the API, and students cannot set the flag |
| Spreadsheet exports | Values beginning with an equals sign are prefixed, so a title cannot execute when the file is opened |
| Image previews | Generated from pixel data only, which drops the location a photograph was taken |
| Transport | Security headers on every response; personal data is never cached |
| Secrets | Production refuses to start with development defaults |

---

## Working quickly

Control or Command with K opens a launcher from anywhere. Typing a ticket
number goes straight to that complaint; typing a page name jumps to it.
Someone working a queue of several hundred complaints spends more time
navigating than reading, and this removes the list, the filter and the
scroll.

Destinations are filtered by role, so a student is never offered a staff
page they would then be refused.

---

## Data protection

The Nigeria Data Protection Act 2023 applies from the first real record.
Complaints contain names, matric numbers and often allegations about named
staff, so the rights below are implemented in the software rather than
handled by hand.

| Right | How it works |
| --- | --- |
| Access and portability | *Your data → Download my data* returns everything held about the person as JSON |
| Erasure | Self-service with password confirmation, or by an administrator on a written request |
| Storage limitation | Each institution sets a retention period; `flask purge-expired` deletes closed complaints past it |
| Accountability | Every staff view of a complaint is recorded with who, when and from where |

**What erasure does.** Name, email, matric number, phone, uploaded files and
everything the person wrote are removed permanently. Complaints survive as
anonymous rows, because they are also the institution's record of what was
reported and decided. Nothing in them points back to the person afterwards.
This limit is stated in the interface before the user confirms, rather than
discovered later.

Student reads are deliberately not logged. Recording ordinary use would
bury the staff entries that matter.

Drafts of the privacy policy and the Record of Processing Activities are in
`docs/`. They describe what the software does accurately, and still need
review by a Nigerian data protection practitioner before publication.
Appointing a Data Protection Officer and assessing NDPC registration are
decisions for the controller, not tasks the software can do.

---

## Reporting

Department heads can export the complaint register, and administrators the
people register, as a spreadsheet. Institutions report to senates and
regulators on schedules no dashboard will match, so the underlying rows are
made available rather than adding a chart each term.

Image attachments get a downscaled preview so a queue can be worked through
without downloading anything. A 2400 by 1800 photograph becomes a 480 pixel
preview around 98 per cent smaller, which matters when the person triaging
is on mobile data. Previews are generated from pixel data alone, so the
location recorded by a phone camera is not carried over.

Previews need Pillow. Without it the application runs unchanged and simply
serves no previews.

---

## Deployment

```bash
cp .env.example .env     # fill in every value marked :?
docker compose up -d --build
```

Brings up PostgreSQL, Redis, the API, a worker for scheduled jobs, and a
daily database backup. Redis is not optional: rate limits are counted per
process, so in-memory counters multiply the login limit by the worker
count, and production refuses to start in that combination.

`docs/OPERATIONS.md` covers logs, backups, the restore drill, releases and
rollback.

### Observability

Every log line is JSON carrying a `request_id`, and every response returns
the same value in `X-Request-ID`. Error responses include it as
`reference`, so somebody reporting a problem can quote a value that finds
the exact request:

```bash
docker compose logs api | grep '"request_id": "a1b2c3d4"'
```

Passwords, tokens and authorisation headers are redacted before anything is
written. Set `SENTRY_DSN` to report unhandled errors; request bodies and
cookies are stripped first, since a body can contain someone's account of a
grievance.

The image runs as an unprivileged user, serves through gunicorn, and exposes `/api/ready` as a health check that confirms the database answers.

For the frontend, `npm run build` produces static files for any CDN or static host. Set `VITE_API_URL` to the API origin.

Schema changes are applied with `flask db upgrade`. The schema is never
created implicitly on start, so a deployment cannot quietly diverge from
what is in version control.

### Required configuration

| Variable | Notes |
| --- | --- |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | PostgreSQL in production; SQLite is for local work only |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |
| `UPLOAD_DIR` | Must be a persistent volume |
| `SMTP_*`, `MAIL_FROM` | Without these, messages queue rather than being discarded |
| `SMS_PROVIDER` | `termii`, `africastalking`, or `console` for local work |
| `APP_URL` | Where password reset links point |
| `RATELIMIT_STORAGE_URI` | Must be shared storage such as Redis when running more than one worker. Rate limits are counted per process, so in-memory counters multiply the limit by the worker count. Production refuses to start in that combination |

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
    services/     tickets, sla, storage, delivery, notifications,
                  sms, export, thumbnails
    security.py   role checks and tenant scoping
  tests/          152 tests
frontend/
  e2e/            52 browser journeys
  src/
    components/   ui primitives, complaint views
    pages/        auth, public, student, admin
    services/     API client
    styles/       design tokens
```

---

## Licence

[MIT](./LICENSE)
