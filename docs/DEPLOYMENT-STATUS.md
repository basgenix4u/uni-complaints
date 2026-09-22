# Deployment status

Last verified against production on 22 September 2026.

## What is live

| Piece | Where | State |
|---|---|---|
| Frontend | `https://uni-complaints.vercel.app` | Serving, API base correct |
| API | `https://resolve-api-eadv.onrender.com` | Healthy, CORS correct |
| Database | Supabase `resolve` schema | At `0006_manual_confirmation` |

The browser path works end to end. A login made with the deployed
frontend's origin returns a token, the preflight on `/api/auth/login`
answers with the right headers, and the public directory loads.

## The two faults that were blocking it

Both are fixed and verified against production, not merely committed.

**`VITE_API_URL` had no `/api` suffix.** Vite inlines the value at build
time, so the deployed bundle posted to `/auth/login` and Vercel's SPA
rewrite returned the index page. Fixed in the dashboard and redeployed;
the current bundle carries `https://resolve-api-eadv.onrender.com/api`.

**`CORS_ORIGINS` was set to a URL, not an origin.** The value ended in a
trailing slash. A browser sends `scheme://host` with no path, so the
allowlist matched nothing and every response left without an
`Access-Control-Allow-Origin` header. Nothing failed anywhere: the API
answered every health check and the logs were clean. The only symptom
was a site that could not log in.

Origins are now normalised when parsed, and production refuses to boot
when the allowlist is missing or points only at localhost. Silent
misconfiguration was the whole problem; a failed deploy is better.

## What still blocks a real pilot

**No email provider.** `SMTP_HOST` is unset, so no confirmation link is
ever sent, and filing a complaint requires a confirmed address. There is
a manual escape hatch — an institution admin can confirm an address at
`PUT /api/admin/registrations/<id>/confirm-email` — and it works, but it
does not scale past a handful of people. See `EMAIL-SETUP.md`; Brevo is
the recommendation.

**Nobody has used it.** No student, registrar or complaints officer has
touched this. Every verification so far is our own.

**The database password should be rotated.** It was shared over a chat
transcript.

## Verifying it yourself

Health, and whether the browser origin is allowed:

```bash
curl -sD- -o /dev/null \
  -H "Origin: https://uni-complaints.vercel.app" \
  https://resolve-api-eadv.onrender.com/api/health
```

An `access-control-allow-origin` header naming that exact origin means
the browser path is intact. Its absence means the site cannot log in,
whatever the status code says.

The free tier sleeps after fifteen minutes idle, so the first request
after a quiet period takes thirty to fifty seconds. That is the platform,
not a fault.

## Onboarding an institution

Sign in at `/login` as the platform administrator, then:

```
POST /api/platform/institutions
{
  "name": "...", "code": "FUW", "slug": "federal-university-wukari",
  "admin_name": "...", "admin_email": "...", "admin_password": "..."
}
```

`code` is two to eight capitals; `slug` is lower case with hyphens. The
call creates the institution, its first administrator, the standard
units and a draft routing table, and marks it onboarded so students can
register immediately. Anonymous complaints are on unless you pass
`allow_anonymous: false`.

Students register against the slug, not the id. Until an email provider
is configured, each new account needs its address confirming by hand
before it can file anything.
