# Setting up the API on Render

Your frontend is already live at
**https://uni-complaints.vercel.app**. It has no backend yet, so every
`/api/*` call falls through to the single-page app and returns HTML
instead of JSON. Signing in cannot work until this is done.

The exact values to paste are in `/home/user/deploy/render-env.txt`,
generated with your database password and verified to connect. That file
is never committed.

---

## 1. Create the service

Render → **New** → **Web Service** → connect `basgenix4u/uni-complaints`.

| Field | Value |
|---|---|
| Name | `resolve-api` |
| Region | **Frankfurt** — the database is in `eu-central-1`; anywhere else adds latency to every query |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn -c gunicorn.conf.py run:app` |
| Instance Type | Free |

## 2. Environment variables

Paste the contents of `render-env.txt` into **Environment**. Render
accepts a bulk paste of `KEY=value` lines.

Four of them decide whether this works at all:

- **`DATABASE_URL`** — session pooler, port **5432**. Not 6543: Render
  runs a long-lived container, so transaction pooling buys nothing and
  breaks prepared statements. The password is percent-encoded because it
  contains `@`, which would otherwise be read as the host separator.
- **`DB_SCHEMA=resolve`** — without it every table is created in
  `public` and collides with the ALIMS application already in that
  database. This is the single most damaging thing to get wrong.
- **`APP_URL`** — every confirmation and invitation link is built from
  it. Wrong value, and every student is sent somewhere that does not
  exist.
- **`WEB_CONCURRENCY=1`** — the free tier has no Redis, so rate limits
  are counted per process. Production refuses to boot with
  `memory://` and a higher count, which is deliberate.

## 3. First deploy

The schema is already at `0006_manual_confirmation`, so there is nothing
to migrate. Once the service is live, create the first administrator
from the Render **Shell**:

```bash
flask seed
```

Not `--demo`. That creates a fictional university, which has no place in
a real deployment. The password is `PLATFORM_ADMIN_PASSWORD` from the
environment file.

## 4. Point the frontend at it

Vercel → Project → Settings → Environment Variables:

```
VITE_API_URL=https://resolve-api.onrender.com/api
```

**The `/api` suffix is required.** Redeploy afterwards — Vite inlines
environment variables at build time, so an existing build will not pick
it up.

## 5. Check it worked

```bash
curl https://resolve-api.onrender.com/api/health
```

Expect `{"status":"ok"}` as JSON. If you get HTML, you are still hitting
Vercel rather than Render.

Then from the browser, sign in at the Vercel site with the platform
administrator. If the network tab shows requests going to
`onrender.com`, the two halves are joined.

## 6. Scheduled jobs

The free tier has no cron. `.github/workflows/scheduled-tasks.yml` calls
the API every 15 minutes instead. Add two repository secrets under
**Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `API_URL` | `https://resolve-api.onrender.com` — host only, no `/api` |
| `TASK_TOKEN` | the `TASK_TOKEN` from the environment file |

These drive escalation, email delivery and the ignored-complaint report.
They also keep the Supabase project awake, which otherwise pauses after
seven days of inactivity.

---

## What will still not work

**Email.** `SMTP_HOST` is blank in the generated file because you have
no provider yet. Until one is configured:

- Nobody can confirm their address, so **nobody can file a complaint**.
- Messages are held in the queue rather than lost, and send in full once
  SMTP is set.
- An administrator can confirm an address by hand under **Registrations**
  as a stopgap.

`docs/EMAIL-SETUP.md` covers this. Brevo gives 300 a day free and works
from Nigeria without a US entity; budget twenty minutes including the
DNS records, which decide whether the mail arrives at all.

## The free tier, honestly

The service sleeps after fifteen minutes idle and takes thirty to fifty
seconds to wake. The first student of the morning waits that long. The
scheduled jobs keep it warmer than it would otherwise be, but they do
not prevent it.

That is tolerable for a pilot and not for a launch. The paid tier is
seven dollars a month and removes it.
