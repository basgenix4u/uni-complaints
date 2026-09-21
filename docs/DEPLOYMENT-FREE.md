# Deploying free, permanently

Runs on the free tier of Render, Supabase, Cloudinary and Vercel, with no
card and no trial that expires. Escalation, email delivery and retention
all still work.

Read `docs/DEPLOYMENT.md` for the paid setup. This document only covers
what differs.

---

## Why Render asked you to pay

`render.yaml` requested `plan: starter` on every service. A blueprint that
names a paid plan makes Render ask for payment before it will deploy
anything.

Use `render.free.yaml` instead. It asks for one free web service and
nothing else.

---

## What the free tier removes, and what replaces it

| Missing | Consequence | Replacement |
|---|---|---|
| Cron jobs | Nothing escalates, no email sends, nothing is purged | A scheduled GitHub Actions workflow calls an endpoint |
| Redis | Rate limits cannot be shared between workers | One worker, counters in process. Enforced at boot |
| Always-on | Sleeps after 15 idle minutes, ~50s to wake | The scheduled request wakes it as a side effect |
| Disk | Wiped on deploy and on wake | Cloudinary, which you are using already |

Nothing is disabled or stubbed. The same jobs run, driven from outside.

---

## How scheduled work runs without cron

The application exposes `POST /api/tasks/all`, protected by a shared
secret. A GitHub Actions workflow calls it every fifteen minutes.

Scheduled workflows are free on public repositories, and this repository
is public, so the scheduler costs nothing.

The call wakes the service and does the work in one request, so waking is
not wasted effort.

### Why this is safe

- Without `TASK_TOKEN` configured, the endpoint returns **404** and does
  not exist. A deployment that forgets to set it is not left with an open
  trigger.
- A wrong token also returns 404, not 401, so probing cannot confirm the
  route is there.
- The token is compared in constant time, so the response timing does not
  leak it a character at a time.
- Only three task names are accepted. The name cannot reach other code.
- Every job is idempotent. GitHub delays scheduled runs under load, and a
  late or repeated run cannot escalate the same complaint twice.

---

## Setup

Parts 1, 2 and 4 of `docs/DEPLOYMENT.md` are unchanged: Supabase for the
database, Cloudinary for files, Vercel for the frontend. Only Render
differs, and the scheduler is new.

### Render, on the free plan

1. **New → Blueprint**, point at this repository.
2. Set the blueprint path to **`render.free.yaml`**.
3. Fill in the values it marks as required, exactly as in the paid guide.

`SECRET_KEY`, `JWT_SECRET_KEY` and `TASK_TOKEN` are generated for you.

**Copy the generated `TASK_TOKEN`.** You need it in the next step, and it
is the only value you have to move by hand.

> `WEB_CONCURRENCY` is pinned to `1` and must stay there. Without Redis
> the rate limit counters live in process memory, so a second worker would
> keep its own counter and multiply the login limit. The application
> refuses to start on any other combination, which is deliberate: a
> defeated rate limit does not announce itself.

### The scheduler

In the repository, **Settings → Secrets and variables → Actions → New
repository secret**, twice:

| Name | Value |
|---|---|
| `API_URL` | `https://resolve-api.onrender.com` — no trailing slash, no `/api` |
| `TASK_TOKEN` | The value Render generated |

> `API_URL` here is the host only. `VITE_API_URL` on Vercel ends in
> `/api`. They are different on purpose and mixing them up produces a 404
> that looks like a broken deployment.

Then **Actions → Scheduled tasks → Run workflow** to test it immediately
rather than waiting for the next quarter hour.

A successful run prints what it did:

```json
{
  "results": {
    "escalate": { "escalated": 1, "reminded": 0 },
    "send-queue": { "sent": 0, "failed": 0, "considered": 2 },
    "purge-expired": { "complaints_purged": 0 }
  },
  "success": true
}
```

---

## Living with a service that sleeps

After fifteen idle minutes the service stops. The next request takes
roughly fifty seconds while it starts again.

**In practice:** the scheduler runs every fifteen minutes, which is close
enough to the sleep threshold that the service is usually already awake
during the working day. The first person in each morning may wait, and
nobody after them will.

**What is unaffected:** nothing is lost while asleep. Email and texts sit
in a queue and send on the next run. Escalation is calculated from
timestamps, not from a timer, so a complaint that passed its deadline
overnight is escalated on the next run rather than missed.

**If the wait is unacceptable,** the smallest paid Render plan removes it.
Nothing else needs to change.

### A note on keep-alive pings

You will find advice to ping the service every few minutes to stop it
sleeping. Do not. Render's free tier includes a monthly quota of running
hours; pinging constantly spends it and the service stops for the rest of
the month. Waking it when there is work to do is the point.

---

## Limits worth knowing before you rely on this

| Service | Free allowance | What runs out first |
|---|---|---|
| Render | 750 instance hours a month | Fine for one sleeping service |
| Supabase | 500 MB database | **Paused after 7 days of no activity** |
| Cloudinary | ~25 GB storage and bandwidth | Generous for documents and photos |
| Vercel | 100 GB bandwidth | Not a concern for this |
| GitHub Actions | Free on public repositories | Not a concern |

> **The one that catches people out:** a Supabase project is paused after
> a week with no database activity, and a paused project refuses
> connections. The scheduler queries the database every fifteen minutes,
> which counts as activity, so keeping the workflow enabled also keeps the
> database alive. Disabling it for a fortnight will pause the project.

---

## Checking it works

```bash
# Awake and the database answers
curl https://resolve-api.onrender.com/api/ready

# The trigger is closed to anyone without the token
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  https://resolve-api.onrender.com/api/tasks/all
# 404

# And open to the scheduler
curl -X POST -H "X-Task-Token: <your token>" \
  https://resolve-api.onrender.com/api/tasks/all
```

Then confirm escalation end to end:

1. File a complaint as a student.
2. In Supabase, open the `complaints` table and set `resolve_due_at` to
   yesterday on that row.
3. **Actions → Scheduled tasks → Run workflow.**
4. The response shows `"escalated": 1`, and the student has a
   notification.

That is the promise on the receipt actually being kept, on a deployment
costing nothing.

---

## Moving to paid later

Switch the blueprint to `render.yaml`, add Redis, raise `WEB_CONCURRENCY`.
The scheduled workflow can stay or be deleted; the cron services in the
paid blueprint run the same commands. Nothing in the application changes.
