# Deployment status

What is actually deployed, what is not, and what was learned doing it.
Updated when the state changes, not when the intention does.

---

## Database — done

The `resolve` schema in the **ALIMS Project** Supabase instance
(`eu-central-1`, `ACTIVE_HEALTHY`) is at the current head.

| | Before | After |
|---|---|---|
| Migration version | `0001_initial` | `0006_manual_confirmation` |
| Tables in `resolve` | 12 | 20 |
| Tables in `public` (ALIMS) | 38 | **38** |

The `public` count is the number that matters. This database belongs to
another live application, and a schema-isolation mistake here damages
someone else's system, not ours.

### How it was applied

1. Rendered the SQL offline first with
   `flask db upgrade 0001_initial:head --sql` under `DB_SCHEMA=resolve`,
   and read all 258 lines before running any of them.
2. Checked three things in the rendered output: every statement
   qualified with `resolve.`, no `DROP`/`TRUNCATE`/`DELETE`, and every
   `REFERENCES` pointing inside the schema.
3. Wrapped the whole thing in `BEGIN`/`COMMIT` — the rendered SQL has no
   transaction control of its own, and a half-applied schema is the
   state that is genuinely hard to recover from.
4. Verified the `public` table count was unchanged before and after.

### What went wrong, and was fixed

**Row level security was not carried by the migrations.** The original
twelve tables had RLS enabled by hand when the schema was first created.
Alembic revisions create tables; they know nothing about RLS or grants.
So the eight new tables arrived with RLS off, sitting beside twelve with
it on.

Not immediately exploitable — `anon` and `authenticated` hold no grants
on the schema, and it is not in PostgREST's exposed list — but it is
defence in depth that was deliberately chosen once and then silently
lost. Fixed, and `backend/scripts/harden_schema.sql` now exists so it is
re-asserted after every future migration rather than remembered.

### Verified against the live database

- All 11 columns the newest code depends on are present.
- The full academic chain inserts and joins correctly: institution →
  session → faculty → department → student record. Run inside a
  transaction and rolled back, so the database was left exactly as
  found (0 institutions, 0 records, 1 platform admin).
- RLS on all 20 tables; zero grants to `anon` or `authenticated`.

---

## Application — not deployed

The API and frontend are not running anywhere. Everything below is
prepared and unverified in production.

### What is ready

- `render.yaml` and `render.free.yaml` for the API.
- `frontend/vercel.json`, root directory `frontend`.
- `.github/workflows/scheduled-tasks.yml` for the jobs, since the free
  tier has no scheduler.
- CI runs the full suite against PostgreSQL 16 in both schema modes, so
  the code is known to work on the database it will actually meet.

### What is blocking

**The pooler password.** It is shown once when a Supabase project is
created and cannot be read back through the Management API. Without it
the application cannot connect, and no amount of schema verification
substitutes for running the thing.

Retrieve it from Supabase (Project Settings → Database → reset the
password if it was not kept), then it goes into Render as
`DATABASE_URL`:

```
postgresql://postgres.<ref>:<password>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
```

Port **5432**, session mode — not 6543. Render runs a long-lived
container, so transaction pooling buys nothing and breaks prepared
statements.

### Environment variables Render needs

| Variable | Value | Why |
|---|---|---|
| `DATABASE_URL` | pooler string above | |
| `DB_SCHEMA` | `resolve` | **Without this every table lands in `public` and collides with ALIMS** |
| `SECRET_KEY`, `JWT_SECRET_KEY` | generated | Production refuses to boot with defaults |
| `APP_URL` | the Vercel URL | Every confirmation and invitation link is built from it |
| `SMTP_*`, `MAIL_FROM` | see EMAIL-SETUP.md | No provider means nobody can confirm an address |
| `WEB_CONCURRENCY` | `1` | Free tier has no Redis, so rate limits are per process |
| `RATELIMIT_STORAGE_URI` | `memory://` | Only valid because concurrency is 1 |
| `TASK_TOKEN` | generated | Shared secret for the scheduled-job trigger |

`VITE_API_URL` on Vercel must end in `/api`.

---

## Honest assessment

The database is deployed and verified. The application is not, and
"schema is correct" is a weaker claim than "the product works" — the
first has been demonstrated, the second has not.

Nothing here has been used by a real student, a real registrar or a real
complaints officer. Every routing default, SLA figure and CSV column
assumption remains a guess until one of them looks at it.
