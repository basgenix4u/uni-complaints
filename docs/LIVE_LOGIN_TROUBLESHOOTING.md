# Live Vercel Student Login – Why It Fails & How to Fix

## You reported: student login on live dashboard (Vercel) not logging in

Tested live production API https://resolve-api-eadv.onrender.com:

### What we found

1. **FUW exists in production** – `federal-university-wukari` slug, id `fa8d013b-19b4-4a80-a218-aba88c5b82cd`, `is_onboarded=true`, `verification_mode=register`, `matric_example=ENG/COE/21/013`

2. **Register is empty** – no `StudentRecord` rows imported yet
   - Verification mode `register` means: student must exist in register to be approved
   - If not in register → `approval_status=pending` → cannot file complaints

3. **Email not verified** – new registrations need email confirmation link
   - Production SMTP not configured? Check Render env `SMTP_HOST`, `MAIL_TO_CONSOLE`
   - Without SMTP, `queue_email` goes to `waiting` state, not sent
   - Result: `can_file=false`, reason "Confirm your email address first. We sent you a link."

**Test we did**:
```bash
POST /api/auth/register {email:teststudent12345@gmail.com, matric:ENG/COE/21/013, institution:federal-university-wukari}
→ approval_status pending, is_verified false
GET /api/auth/verification-status → can_file false, reason "Confirm your email address first"
```

So login **does succeed** (you get access_token), but dashboard shows banner "Confirm your email" and "Your institution is checking your registration" and you cannot file complaints.

---

## Why local preview works but live Vercel doesn't

**Local (this workspace)** – we seeded full FUW:
- 300 student_records from Excel, 225 student users claimed, passwords from Excel `FUW<year><num>@Pass123`
- 58 staff with password `Staff123!`
- 450 complaints with dynamic escalation
- SQLite DB `backend/resolve.db` – all in one file

**Production (Render Postgres)** – only directory entry, no student_records, no staff, no complaints – empty

Your Vercel frontend `https://uni-complaints.vercel.app` points to `https://resolve-api-eadv.onrender.com` which has empty FUW.

---

## Fix – 3 options

### Option A – Use local preview NOW (works immediately)

We started live servers in this workspace:
- Frontend: **Resolve Frontend** preview → https://5173-...e2b.app
- API: https://5000-...e2b.app

Credentials that **work now** (local):

**FUW Admin**:
- Email: `admin@fuwukari.edu.ng`
- Password: `FUWAdmin123!`

**Staff** (all password `Staff123!`):
- `samuel.james0@fuwukari.edu.ng` – dean Library
- `khadija.okafor1@fuwukari.edu.ng` – officer Student Affairs
- See Excel `Staff_Authorized` sheet for all 58

**Students** (225 adopted):
- `eze.davis22228@gmail.com` / `FUW22228@Pass123` – matric `hum/atr/22/228`
- `anderson.garba21004@gmail.com` / `FUW21004@Secure123`
- Full list in `FUW_Pilot_Dataset_300_Students.xlsx` Students_300 sheet columns login_email + password
- Fallback: `Student123!`

Login at local preview and you will see:
- Dashboard 450 complaints, routing 94.7%, SLA 89.6%, avg 2.31d, adoption 75%
- Academic Structure → Faculties 13, Departments 50, Register 300, pattern `^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$`
- All complaints with priority badges low/medium/high/urgent + factor + dynamic escalation
- Notifications, email templates with FUW branding

### Option B – Seed production with FUW data (recommended for live Vercel)

You need **PLATFORM_ADMIN_EMAIL/PASSWORD** from Render env (set in Render dashboard → resolve-api → Environment).

Once you have it:

```bash
export API_URL=https://resolve-api-eadv.onrender.com
export PLATFORM_TOKEN=$(curl -s -X POST $API_URL/api/auth/login -H "Content-Type: application/json" -d '{"email":"$PLATFORM_ADMIN_EMAIL","password":"$PLATFORM_ADMIN_PASSWORD"}' | jq -r .data.access_token)

# Check FUW exists
curl -s "$API_URL/api/directory/institutions?q=Wukari" -H "Authorization: Bearer $PLATFORM_TOKEN"

# If FUW admin doesn't exist, create via onboard or create staff
# Then login as FUW admin to get institution token
export FUW_ADMIN_TOKEN=$(curl -s -X POST $API_URL/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@fuwukari.edu.ng","password":"FUWAdmin123!","institution":"federal-university-wukari"}' | jq -r .data.access_token)

# If FUW admin login fails, reset password via platform admin:
curl -X POST $API_URL/api/admin/users -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"full_name":"FUW Admin","email":"admin@fuwukari.edu.ng","role":"institution_admin","institution_id":"fa8d013b-19b4-4a80-a218-aba88c5b82cd"}'

# Create session
curl -X POST $API_URL/api/academic/sessions -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"name":"2023/2024","is_current":true}'

# Import faculties/departments from Excel (convert Departments sheet to CSV)
curl -X POST $API_URL/api/academic/structure/bulk -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -F "file=@Departments.csv" -F "dry_run=false"

# Import student register XLSX (Students_300 sheet as XLSX)
curl -X POST $API_URL/api/academic/register/import -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -F "file=@Students_300.xlsx" -F "dry_run=false"

# Import staff via invitations bulk
curl -X POST $API_URL/api/invitations/bulk -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -F "file=@Staff.csv" -F "dry_run=false"
```

We provided script `scripts/seed_fuw_full.py` for local – adapt for production by changing DATABASE_URL to production Postgres and using platform token.

**Quick fix for testing student login without register**: Change verification_mode to `open` temporarily:

```bash
curl -X PUT $API_URL/api/admin/settings -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"verification_mode":"open"}'
# Then any email can register and file immediately, no matric check
```

Or via platform:

```bash
curl -X PUT $API_URL/api/platform/institutions/fa8d013b-19b4-4a80-a218-aba88c5b82cd/onboarding -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"is_onboarded":true,"verification_mode":"open"}'
```

### Option C – Check Render logs for email verification

If SMTP not configured, confirmation links go to logs if `MAIL_TO_CONSOLE=true` (not allowed in production per config). Check Render → resolve-api → Logs for `email_written_to_log`.

Better: configure SMTP in Render env:
- `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`
- Then `flask send-queue` cron will deliver queued emails

Until then, admin can manually confirm email:

```bash
curl -X PUT $API_URL/api/admin/registrations/<user_id>/confirm-email -H "Authorization: Bearer $FUW_ADMIN_TOKEN"
```

And approve pending:

```bash
curl -X PUT $API_URL/api/admin/registrations/<user_id> -H "Authorization: Bearer $FUW_ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"decision":"approved"}'
```

---

## Current production state

- Health: https://resolve-api-eadv.onrender.com/api/health → ok
- Ready: /api/ready → ready (DB connected, migration 0010 should be applied via `flask db upgrade` in Dockerfile)
- FUW: onboarded, verification_mode register, matric_example ENG/COE/21/013, but **0 student_records**
- Test student we created: `teststudent12345@gmail.com` – pending + unverified → cannot file

---

## What to do now

1. **Test immediately**: Use local preview links (Resolve Frontend) with credentials above – full UI with 450 complaints, dynamic escalation, routing 94.7%, SLA 89.6%
2. **For live Vercel**: Get PLATFORM_ADMIN_EMAIL/PASSWORD from Render dashboard, then run seeding or change verification_mode to open for quick testing
3. **After seeding production**: Student logins from Excel will work on live Vercel, same as local

All hardening (CSV+XLSX, per-institution matric regex, email templating with ticket/deadline/officer, Cloudinary archive) is already pushed to production main branch and will be live after Render redeploy.

