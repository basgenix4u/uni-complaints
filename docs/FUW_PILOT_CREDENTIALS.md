# FUW Pilot – Live Credentials for Admin Dashboard

**Live Preview URLs** (in this workspace):
- Frontend: Click **Website** preview → https://5173-...e2b.app (Vite)
- API: https://5000-...e2b.app/api/health

Both backend and frontend are running locally with full FUW data (300 students, 58 staff, 450 complaints).

---

## Admin Logins

### Platform Admin (sees all institutions)
- Email: `admin@resolve.ng`
- Password: `Admin123!`
- Can: list institutions, create institutions, view stats

### FUW Institution Admin (FUW dashboard)
- Email: `admin@fuwukari.edu.ng`
- Password: `FUWAdmin123!`
- Institution: Federal University Wukari (FUW) – slug `federal-university-wukari`
- Matric pattern: `^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$` example `eng/coe/21/013`
- Can: manage faculties, departments, offices, student register (CSV+XLSX), staff, complaints, email templates, SLA

---

## Staff Logins (58 staff, all password `Staff123!`)

Sample (all @fuwukari.edu.ng):

| Name | Email | Role | Department (Processing Unit) | Can Handle Confidential |
|---|---|---|---|---|
| Samuel James | samuel.james0@fuwukari.edu.ng | dean | Library | No |
| Khadija Okafor | khadija.okafor1@fuwukari.edu.ng | officer | Student Affairs | No |
| Blessing Nwachukwu | blessing.nwachukwu2@fuwukari.edu.ng | officer | SUG | No |
| John Miller | john.miller3@fuwukari.edu.ng | officer | Security | No |
| Patrick Rodriguez | patrick.rodriguez4@fuwukari.edu.ng | officer | SUG | No |
| Emeka Abdulalim | emeka.abdulalim5@fuwukari.edu.ng | officer | Academic Affairs | No |
| Zainab Mohammed | zainab.mohammed6@fuwukari.edu.ng | officer | Security | No |
| Abdulbasit Ahmad | abdulbasit.ahmad7@fuwukari.edu.ng | officer | Dean of Engineering | No |
| Maryam Rodriguez | maryam.rodriguez9@fuwukari.edu.ng | dean | Works & Maintenance | Yes |
| ... | ... | ... | ... | ... |

**All 58 staff**: see `FUW_Pilot_Dataset_300_Students.xlsx` sheet `Staff_Authorized` – password for all is `Staff123!`

**Heads**:
- Exams & Records head: check Staff_Authorized where department = Exams & Records and role = department_head
- Bursary head, Registry head, etc. – each office has at least one head (can_handle_confidential Yes)

**What staff can do**:
- Acknowledge complaints (within 24h * factor SLA)
- Route (94.7% correct first time via faculty_code/dept_code parsing)
- Respond (template with ticket/deadline/officer)
- Resolve (avg 2.31 days)
- View confidential (Harassment, Lecturer Conduct) only if authorized

---

## Student Logins (225 adopted of 300)

Sample from `Students_300` sheet – password from Excel column:

| Full Name | Login Email (personal) | Password (from Excel) | Matric | Faculty | Dept | Level |
|---|---|---|---|---|
| Eze Davis | eze.davis22228@gmail.com | FUW22228@Pass123 | hum/atr/22/228 | Humanities | African Traditional Religion | 500 |
| Anderson Garba | anderson.garba21004@gmail.com | FUW21004@Secure123 | law/pcl/21/004 | Law | Private and Commercial Law |  |
| Martinez Bello | martinez.bello20247@gmail.com | FUW20247@Secure123 | edu/ced/20/247 | Education | Chemistry Education |  |
| Bello Umar | bello.umar23083@gmail.com | FUW23083@Pass123 | edu/ped/23/083 | Education | Physics Education |  |
| Ahmed Abdulalim | ahmed.abdulalim21080@gmail.com | FUW21080@Student123 | hum/els/21/080 | Humanities | English and Literary Studies |  |
| Tunde Martinez | tunde.martinez22151@gmail.com | FUW22151@Student123 | ahs/pht/22/151 | Allied Health | Physiotherapy |  |
| ... | ... | ... | ... | ... | ... | ... |

**All 300**: see Excel Students_300 sheet – login_email + password columns

**If password from Excel fails, try `Student123!`** (fallback used in seeding)

**What students can do**:
- File complaints across 15 categories (Missing Result, Transcript, Course Registration, Fee Receipt, Hostel, Portal Access, Lecturer Conduct confidential, Harassment confidential, Water, Electricity, Library, Medical, Security, Admission, Scholarship)
- Track ticket FUW-XXXX-XXXX
- Respond when awaiting_student
- Rate satisfaction 1-5

---

## How UI Looks – What to Check

1. **Login as FUW admin** (`admin@fuwukari.edu.ng` / `FUWAdmin123!`):
   - Dashboard: total 450 complaints, routing 94.7%, SLA 89.6% working-hours, satisfaction 3.18, adoption 75%, uptime 98.5%, <2s load, 1800 notifications
   - Academic Structure → Faculties: 13 faculties with codes ENG, CIS, etc.
   - Academic Structure → Student Register: 300 records, matric pattern `^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$`, example `eng/coe/21/013`, CSV+XLSX upload, Cloudinary archive info
   - Admin → Departments: 14 processing units with SLA hours
   - Admin → Users: search by matric, see faculty/dept auto-filled from code
   - Complaints: filter by status, category, priority (low/medium/high/urgent with factor), overdue, confidential
   - Complaint Details: timeline showing created → acknowledged (within ack SLA) → in_progress → resolved in 2.31d avg, dynamic escalation factor displayed
   - Email Templates: `/api/email-templates` – per-institution branding sender FUW Resolve, footer, variables ticket/deadline/officer

2. **Login as Staff** (e.g. `samuel.james0@fuwukari.edu.ng` / `Staff123!`):
   - My assignments, acknowledge, respond with templated email (ticket FUW-..., deadline, officer name)
   - Confidential complaints only visible if department matches handling unit and can_handle_confidential Yes

3. **Login as Student** (e.g. `eze.davis22228@gmail.com` / `FUW22228@Pass123`):
   - Student Dashboard: file complaint, auto matric validation against FUW pattern, faculty/dept auto-filled
   - My complaints: see status moving, satisfaction rating
   - Notifications: escalation alerts showing dynamic factor "high priority escalated after 36h effective SLA (factor 0.5)"

4. **Dynamic Escalation Proof**:
   - Check complaint with priority urgent → effective SLA 18h (or 6h for 24h-base units) → calendar allowed 2d (or 0.66d) → if missed, escalated to Dean/VC
   - Table in `FUW_PILOT_SCREENSHOTS.html` shows low 2.0 144h 16d 100% compliance, medium 1.0 72h 8d 95.6%, high 0.5 36h 4d 88.5%, urgent 0.25 18h 2d 49% needs triage

---

## Production URLs (Render/Vercel) – also updated

- Frontend: https://uni-complaints.vercel.app
- API: https://resolve-api-eadv.onrender.com
- After Render finishes migration 0010, you can repeat same seeding via `scripts/register_fuw_pilot.py` with platform token, then login same credentials

---

## Cleanup After Pilot (for production)

```sql
DELETE FROM complaints WHERE data_origin='pilot';
DELETE FROM users WHERE data_origin='pilot';
-- Keep faculties/departments/offices, re-import fresh student register for production
```

Then re-register FUW clean.

---

## Files

- Dataset: `docs/FUW_Pilot_Dataset_300_Students.xlsx`
- Results: `docs/FUW_PILOT_RESULTS_450_Complaints.xlsx`
- Metrics JSON: `docs/FUW_PILOT_METRICS.json`
- Evaluation Report: `docs/FUW_PILOT_EVALUATION_REPORT.md`
- Screenshots HTML: `docs/FUW_PILOT_SCREENSHOTS.html`
- Hardening Notes: `docs/FUW_PILOT_HARDENING.md`
