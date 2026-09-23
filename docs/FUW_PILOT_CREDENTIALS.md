# FUW production pilot access notes

This file intentionally contains no passwords, access tokens, or student
credentials. Production secrets were rotated after live verification and
must be retained only in the team's secure secret manager.

## Production URLs

- Frontend: `https://uni-complaints.vercel.app`
- API: `https://resolve-api-eadv.onrender.com`
- Health: `https://resolve-api-eadv.onrender.com/api/health`

## Administrative identities

- `admin@resolve.ng` — platform administrator.
- `admin@fuwukari.edu.ng` — FUW institution administrator.

Use the secure out-of-band credential store for both identities. Do not put
replacement values in this repository, a spreadsheet, a chat transcript, or
an API command. The live login checks passed before the final credential
rotation; the new values were generated in memory and were not printed or
written to disk.

## Controlled pilot cohort

- Institution: Federal University Wukari (`federal-university-wukari`)
- Register workbook: `FUW_Pilot_Dataset_300_Students.xlsx`, sheet `Students_300`
- Cohort: `pilot_cohort_id = fuw-2026-register-v1`
- Provenance: `data_origin = pilot`
- Synthetic email suffix: `@pilot.resolve.invalid`
- Current session: `2025/2026`
- Matric example: `ENG/COE/21/013`

The cohort accounts are synthetic, verified, approved, and intended only for
the controlled pilot. The workbook's password column is sensitive and must
not be copied into documentation or logs.

## Production setup verification

- The multi-sheet workbook was dry-run, imported through the live admin API,
and dry-run again idempotently: 300 rows, 0 created, 0 updated, 300 skipped,
with no problems.
- All 300 imported records are linked to the current session and claimed by
the tagged pilot cohort.
- Pilot complaints were submitted through the live student complaint API;
complaint provenance is inherited from the authenticated pilot user.
- FUW routing, SLA, escalation, email-template fallback, and cleanup
selectors are documented in `docs/DEPLOYMENT-STATUS.md`.

## Cleanup warning

Never delete by institution alone and never truncate shared tables. Before a
later scoped cleanup, assert the expected counts and use the institution,
student role, cohort id, pilot provenance, and synthetic email suffix
selectors together. Delete pilot complaints before pilot users, release
claimed register rows, and leave FUW structure, staff/admin identities,
and operational student accounts untouched.
