# Operations

How to run, observe, back up and recover this service.

---

## Starting it

```bash
cp .env.example .env     # fill in every value marked :?
docker compose up -d --build
docker compose logs -f api
```

The API applies migrations before workers start, so a container can never
serve against a schema older than its code.

### Values that must be set

`SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`. Compose refuses to
start without them rather than falling back to a default.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Why Redis is required

Rate limits are counted per process. With more than one worker, in-memory
counters mean each worker allows the full limit, so ten login attempts
becomes ten times the worker count. Production **refuses to start** in that
combination. Redis gives the workers one shared counter.

---

## Watching it

### Logs

Every line is JSON and carries a `request_id`. Every response carries the
same value in `X-Request-ID`, and every error response includes it as
`reference`.

When somebody reports a problem, ask for the reference:

```bash
docker compose logs api | grep '"request_id": "a1b2c3d4"'
```

That returns every line for that one request: the route, the status, how
long it took, and the stack trace if it failed.

Passwords, tokens and authorisation headers are redacted before anything is
written. Health checks are excluded so they do not bury real traffic.

### Errors

Set `SENTRY_DSN` to report unhandled exceptions. Request bodies and cookies
are stripped before sending, because a body can contain someone's account
of a grievance and that must not leave the deployment.

Without a DSN, reporting is simply off.

### Is it alive

| Endpoint | Meaning |
|---|---|
| `/api/health` | The process is up |
| `/api/ready` | The database answers |

Use `/api/ready` for load balancer checks. A process that is up but cannot
reach the database should not receive traffic.

---

## Backups

A dump runs daily into `./backups`, keeping fourteen.

### Restoring — do this before you need it

An untested backup is a hope. Run this drill after the first deployment and
then quarterly.

```bash
# 1. A scratch database
docker compose exec db createdb -U resolve restore_test

# 2. Restore the most recent dump into it
gunzip -c backups/resolve-YYYYMMDD-HHMM.sql.gz \
  | docker compose exec -T db psql -U resolve -d restore_test

# 3. Confirm it holds what you expect
docker compose exec db psql -U resolve -d restore_test \
  -c "select count(*) from complaints; select max(created_at) from complaints;"

# 4. Clean up
docker compose exec db dropdb -U resolve restore_test
```

**Record the date you last completed this.** If the answer is "never", you
do not have backups.

### What is not covered

`pg_dump` captures the database only. **Uploaded files live in the
`uploads` volume and are not in the dump.** Back that up separately:

```bash
docker run --rm -v uni-complaints_uploads:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/uploads-$(date +%Y%m%d).tar.gz -C /data .
```

---

## Scheduled work

The worker container runs these. They are all idempotent and safe to run
again.

| Command | Frequency | Purpose |
|---|---|---|
| `flask send-queue` | 5 minutes | Deliver queued email and texts |
| `flask escalate` | 30 minutes | Raise complaints past their deadline |
| `flask purge-expired` | Nightly | Delete complaints past the retention period |

Run one by hand:

```bash
docker compose exec worker flask escalate
```

---

## Releasing

1. Merge to `main`. CI runs backend tests, the browser suite, lint and a
   security audit.
2. Tag the release and set `RELEASE` so errors can be attributed to a
   build.
3. `docker compose up -d --build api worker`
4. Watch `/api/ready` and the logs for a few minutes.

### Rolling back

```bash
docker compose down api worker
git checkout <previous-tag>
docker compose up -d --build api worker
```

**Migrations do not roll back automatically.** A revision that drops a
column cannot be undone by redeploying older code. Prefer additive changes:
add a column, deploy, backfill, and only remove the old one in a later
release once nothing reads it.

---

## Common problems

| Symptom | Cause | Action |
|---|---|---|
| API exits immediately with a `RuntimeError` about rate limiting | `memory://` with more than one worker | Set `RATELIMIT_STORAGE_URI` to Redis |
| API exits complaining about `SECRET_KEY` | A development default in production | Generate real values |
| Emails never arrive | No SMTP configured | Set `SMTP_*`. Messages stay queued rather than being lost, so nothing is missing once it is configured |
| Uploads vanish after deploy | Files written to the container filesystem | Confirm the `uploads` volume is mounted |
| Deadlines look wrong | Working hours or holidays misconfigured | Check the institution's working day in settings |

### Inspecting the delivery queue

```bash
docker compose exec api flask shell
>>> from app.models.message import OutboundMessage
>>> OutboundMessage.query.filter_by(status="pending").count()
>>> [m.error for m in OutboundMessage.query.filter_by(status="failed").limit(5)]
```

Nothing is discarded when a provider is missing or failing. Messages stay
queued and send once it works.

---

## Data protection duties

These recur and are the controller's responsibility:

- Confirm each institution has set a retention period. Zero means keep
  forever, which is a choice, not a default to leave unexamined.
- Review the complaint access log where misuse is suspected:
  `GET /api/privacy/complaints/<id>/access-log`.
- On a breach, notify the NDPC **within 72 hours**. See
  `docs/RECORD-OF-PROCESSING.md`.
- Erasure requests received on paper are actioned by an administrator
  through the people page.
