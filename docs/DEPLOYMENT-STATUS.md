# Deployment status

Last verified against production on 23 September 2026.

## What is live

| Piece | Where | State |
|---|---|---|
| Frontend | `https://uni-complaints.vercel.app` | Serving, API base correct |
| API | `https://resolve-api-eadv.onrender.com` | Healthy, CORS correct; live admin and student API flows verified |
| Database | Supabase `resolve` schema | At `0011_schema_security`; RLS enabled on all 22 application tables |

The browser path works end to end. Live production authentication was
verified for both administrator roles, and the deployed API accepted a
student login and complaint submission. The multi-sheet XLSX register
parser is deployed and selects the sheet containing `matric_number` and
`full_name` rather than assuming the active sheet.

## FUW production pilot state

The FUW tenant is configured with its current session, 14 faculties, 66
academic departments (including the workbook's `MBS` department), 91
processing units, 24 active routing rules, FUW matric validation, working
hours 08:00–17:00, a 72-hour default SLA, a 24-hour acknowledgement SLA,
and a 12-month retention setting. Email branding and all 15 event
fallback templates are present.

The single `FUW_Pilot_Dataset_300_Students.xlsx` workbook was first dry-run,
then imported through `POST /api/academic/register/import`; the final
repeat dry-run reported 300 rows, 0 created, 0 updated, 300 skipped, and
no problems. All 300 records are linked to the current session, academic
faculty/department, and a controlled pilot account.

The controlled cohort is identified by `pilot_cohort_id =
fuw-2026-register-v1`, `data_origin = pilot`, and the email suffix
`@pilot.resolve.invalid`. There are 300 such student users and 16
production complaints created through the live complaint API; all are
pilot-provenanced. The four pre-existing operational student accounts
remain outside that cohort.

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

## Remaining operational work

**No email provider.** `SMTP_HOST` is unset, so ordinary self-registration
cannot send a confirmation link. The controlled pilot accounts are
synthetic, explicitly verified, approved, and marked as pilot data; that
is why the production API workflow could be exercised without sending
mail. Configure SMTP before inviting real students. See
`EMAIL-SETUP.md`; Brevo is the recommendation.

**Staff response exercise.** The pilot complaints are submitted and
routed, including confidential cases, but staff acknowledgement,
responses, resolution, escalation, and satisfaction journeys still need
an authorised staff session if those metrics are required.

**Credential hygiene.** The two production administrator passwords were
rotated after verification; replacement values were generated in memory,
verified, and intentionally not recorded here. The shared Supabase
Management API token and GitHub fine-grained token require revocation and
reissue in their provider consoles/account security settings; the public
management APIs available to this workspace do not provide a safe
self-service rotation endpoint. Do not reuse the shared values.

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

## Scoped pilot cleanup selectors

Do not truncate or delete by institution alone. For this controlled cohort,
first assert the expected counts, then scope any later cleanup to:

- institution slug `federal-university-wukari`;
- student role;
- `pilot_cohort_id = fuw-2026-register-v1`;
- `data_origin = pilot`; and
- the controlled email suffix `@pilot.resolve.invalid`.

Delete pilot complaints before pilot users, release their claimed register
rows, then remove only the matching pilot register/user rows. Leave the FUW
structure, processing units, routing rules, templates, administrators, four
operational student accounts, and non-pilot data untouched. Re-run the
register dry-run after any scoped cleanup before re-registering.
