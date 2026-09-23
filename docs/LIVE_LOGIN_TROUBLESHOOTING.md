# Live login troubleshooting

This note replaces the earlier credential-bearing troubleshooting record.
Do not store or copy production passwords, JWTs, database credentials, or
student password columns into documentation.

## Current production endpoints

- Frontend: `https://uni-complaints.vercel.app`
- API: `https://resolve-api-eadv.onrender.com`
- Health: `https://resolve-api-eadv.onrender.com/api/health`

## Current FUW state

- Tenant slug: `federal-university-wukari`
- Verification mode: `register`
- Current session: `2025/2026`
- Register: 300 imported and claimed pilot records
- Controlled pilot accounts: 300, tagged with
  `pilot_cohort_id=fuw-2026-register-v1` and `data_origin=pilot`
- Pilot complaints: submitted through the live complaint API and inherited
  pilot provenance

Both administrative roles and a controlled pilot student login were verified
against the live API before the final credential rotation. The replacement
admin secrets were generated in memory, verified, and intentionally not
printed or persisted in this repository.

## If a real student cannot file

1. Confirm that the student exists in the current register for the correct
   institution and matriculation format.
2. Confirm the account's email is verified and approval is `approved`.
3. Check SMTP/provider configuration before inviting real students. The
   controlled synthetic cohort is not a substitute for production email
   delivery.
4. Check CORS and the API base URL from the deployed frontend; the frontend
   must use the `/api` suffix and the exact Vercel origin must be allowed.
5. Use the authenticated production API response and server logs without
   copying tokens or personal data into a ticket or document.

For the current audit, deployment history, and safe cleanup selectors, see
`docs/DEPLOYMENT-STATUS.md`.
