# FUW Pilot + Production Hardening – Implementation Notes

## Context
- **Institution**: Federal University Wukari (FUW), Taraba State
- **Matric format**: `eng/coe/21/013` where `eng` = faculty short code (Engineering), `coe` = dept short code (Computer Engineering), `21` = entry year (2021), `013` = student number
- **Not hardcoded**: matric format varies per institution. System must understand format when registering institution and validate CSV/XLSX accordingly.
- **Free tier constraint**: Render free (1 worker, memory:// rate limit), GitHub Actions scheduler, Cloudinary free tier 25GB storage / 25GB bandwidth / 25k transformations.

## What was hardened

### 1. Bulk student import – CSV + XLSX, per-institution matric format
**Before**: only CSV UTF-8/latin-1, `normalise_matric` uppercases and replaces separators with "/", no per-institution regex, no faculty_code/dept_code parsing, no archive.

**After** (`backend/app/services/register.py`):
- `parse_register_file(payload, filename)` detects type by extension and magic (`PK` = XLSX)
- `parse_csv` and `parse_xlsx` (openpyxl) share same required columns `matric_number`, `full_name` + optional `faculty`, `faculty_code`, `department`, `department_code`, `programme`, `level`, `status`, `email`
- `compile_matric_pattern` – institution.matric_pattern compiled IGNORECASE
- `validate_matric_against_pattern` – if institution has pattern, each row validated, problem list includes example
- `find_faculty` / `find_department` – lookup by code first (for FUW format), then name, then parsed matric parts: `ENG/COE/21/013` → faculty code `ENG`, dept code `COE`
- Faculty/Department codes now respected in bulk structure import (`structure/bulk` also CSV+XLSX)

**Institution model** (`backend/app/models/institution.py`):
- Already had `matric_pattern`, `matric_example` – now used
- Added `matric_format_description` (e.g. "faculty/dept/year/number")
- Added `email_sender_name`, `email_footer`, `email_reply_to` for per-institution branding (not hardcoded)

**Auth validation** (`backend/app/routes/auth.py`):
- Removed hardcoded `MATRIC_RE = ^[A-Z]{2,5}/[A-Z]{2,5}/\d{2,4}/\d{3,6}$`
- New `_validate_matric_for_institution(matric, institution)` checks institution.matric_pattern IGNORECASE, falls back to generic pattern, uses institution.matric_example in error message

**Frontend** (`AcademicStructure.jsx`):
- File input accept `.csv,.xlsx,.xls`
- Shows matric pattern/example/description from `register/summary`
- Hint mentions Cloudinary archiving

### 2. Email templating – not hardcoded
**Before**: subjects/bodies hardcoded in `auth.py`, `verification.py`, `routing.py`, `notifications.py`

**After**:
- New model `EmailTemplate` (`backend/app/models/email_template.py`): institution_id, event_type, subject_template, body_template, is_active
- `EMAIL_EVENTS` = verification, password_reset, password_changed, complaint_submitted, acknowledged, in_progress, awaiting_student, resolved, closed, declined, escalation, assignment, response, ignored_report, invitation
- `DEFAULT_TEMPLATES` with variables `{{ticket_number}}`, `{{complaint_title}}`, `{{student_name}}`, `{{officer_name}}`, `{{deadline}}`, `{{category}}`, `{{priority}}`, `{{app_url}}`, `{{footer}}`, etc.
- Safe rendering via `render_template_string` – `{{var}}` substitution, missing vars → empty, no code exec
- Service `email_templating.py`: `render_event(institution, event_type, variables)`, `queue_templated_email`
- Updated call sites:
  - `verification.py` uses templated verification
  - `auth.py` forgot/reset password uses templated
  - `notifications.py` now accepts `template_vars` and maps type to event
  - `complaints.py` passes ticket/deadline/officer/category etc.
- New API `email_templates.py`: list, upsert, delete, preview, branding update
  - `GET /api/email-templates` – merged custom + defaults + available variables
  - `PUT /api/email-templates/branding` – update sender name/footer/reply-to/matric pattern
  - `PUT /api/email-templates/<event_type>` – custom template
  - `POST /api/email-templates/preview/<event_type>` – render sample
- Free tier: DB storage, no extra cost

### 3. Student register import storage – Cloudinary?
**Question**: Can student register import be stored in Cloudinary storage? Must evaluate for free tier.

**Answer**: Yes, and should be.

- Render free filesystem is ephemeral – a CSV uploaded today disappears on next deploy
- Cloudinary free: 25GB storage, 25GB bandwidth, authenticated raw assets never public
- Implementation (`register.py`):
  - `archive_register_file(institution, payload, original_filename, content_type)` → `registers/{CODE}/{timestamp}_{rand}_{safe_name}` via `storage.write_bytes` which uses Cloudinary backend if `CLOUDINARY_CLOUD_NAME/KEY/SECRET` set
  - Uses existing `cloudinary_storage.py` (already handles `image` vs `raw`, authenticated type, signed download)
  - New model `RegisterImport` records original filename, stored_name, backend, size, rows, created/updated counts, problems, uploader
  - API `GET /api/academic/register/imports` lists archives
  - Log includes storage_backend
- Free tier sizing: 300 students CSV ~ 30KB, XLSX ~ 38KB, 20k students ~ 1.6MB CSV, 2.5MB XLSX – 25GB holds ~10k such imports
- Alternative: Supabase Storage also supported via `object_storage`, but Cloudinary takes precedence per `storage.py`

**Tradeoff**: Cloudinary raw download is signed, 120s TTL, fetched server-side then streamed to authorized caller – no public URL leak.

### 4. FUW Pilot Dataset – single Excel file, different sheets
File: `FUW_Pilot_Dataset_300_Students.xlsx` (generated, 10 sheets)

- **Institution**: FUW, code FUW, slug federal-university-wukari, pattern `^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$`, example `eng/coe/21/013`, verification_mode register, allow_anonymous No
- **Faculties**: 13 (Engineering ENG, Computing CIS, Agriculture AGL, Bio-Sciences BIO, Physical PHY, Management MGT, Social SOS, Humanities HUM, Education EDU, Law LAW, plus 3 College Health Sciences BMS/AHS/CLS)
- **Departments**: 50 (ENG: AGE, CHE, CVE, COE, MEC; CIS: CSC, CYS, IFS, SEN; etc. with codes)
- **Offices_ProcessingUnits**: 14 routing targets (Registry, Exams & Records, Bursary, Student Affairs, ICT/MIS, Security, Health, Library, Works, SUG, Academic Affairs, Dean Engineering, Dean Computing, VC Office) with SLA hours
- **Staff_Authorized**: 58 staff (random Nigerian names, email @fuwukari.edu.ng, roles officer/department_head/institution_admin/dean, phone, staff_id, can_handle_confidential)
- **Students_300**: 300 students, matric `faculty_code/dept_code/year/number` lower-case (e.g. `eng/coe/21/013`), faculty_code, department_code, level 100-500, entry_year 2019-2023, email, institution_email, phone, password, login_email, status active, programme
- **Complaint_Categories**: 15 categories with default_unit, sla_hours, is_confidential, is_academic
- **Routing_Rules**: 15 rules mapping category → handling_unit + fallback (Dean or VC), sla override, confidential flag
- **SLA_Config**: FUW 72h default, 24h acknowledge, 8-17 working hours, priority factors low 2.0 medium 1.0 high 0.5 urgent 0.25, escalation 48h, retention 12 months
- **Pilot_Measurement_Template**: provisional figures to replace with real pilot (processing times 7d→2d 71.4% p.012, transcript 12d→<6d 50% p.021, registration >3d→~1d 66.7% p.018, 98% uptime <2s, 18k notifications, 60%→<20% no-update beyond 48h, satisfaction 2.1-2.3→4.0-4.3 Cronbach α0.89, ease-of-use β0.62 p.004)

## Research pilot workflow (permitted, live)
1. Register FUW as test institution live via `POST /api/platform/institutions` with matric_pattern, matric_example, matric_format_description, email branding
2. Create session `2023/2024` current
3. Import Faculties/Departments via `POST /api/academic/structure/bulk` with XLSX (faculty_code/dept_code columns)
4. Import Offices as Departments via `POST /api/admin/departments` (admin units)
5. Create staff via invitation bulk or direct (58 authorized)
6. Import Students_300 via `POST /api/academic/register/import` with XLSX – test CSV+XLSX parsing, per-institution matric validation, Cloudinary archive
7. Simulate complaints: sample 300 students with different aspects (Missing Result, Transcript, Fee, Hostel, Portal, Harassment confidential, etc.)
8. Measure real: processing time (acknowledge→resolve hours), routing accuracy (correct unit first filing), SLA compliance (resolved within deadline), errors (duplicate/misfile), adoption (% of 300 using system), satisfaction (Likert survey)
9. Capture de-identified live screenshots: Dashboard, All Complaints, Student Dashboard, Notifications showing dynamic priority-based escalation (PRIORITY_SLA_FACTOR low 2.0 medium 1.0 high 0.5 urgent 0.25 + working-hours SLA deadline_for)
10. Replace provisional figures in manuscript with measured data, note Cronbach, regression β
11. After testing, delete pilot data (users where data_origin='pilot' or pilot_scenario_id set, complaints with pilot_scenario_id) and re-register FUW clean for production

## Migrations
- `0010_email_templating_and_register_archive.py`: adds 4 columns to institutions, creates email_templates and register_imports tables

## Dependencies
- Added `openpyxl==3.1.5` to `requirements.txt` for XLSX support

## Free tier viability
- Render free 1 worker + memory:// rate limit – okay for pilot (300 users, ~50 complaints/day)
- Cloudinary free 25GB – register archives + attachments (already using authenticated)
- No extra services, no hardcoded secrets

## Next steps for live registration
Use script `scripts/register_fuw.py` (to be created) with PLATFORM_ADMIN token to POST FUW institution, then import Excel sheets.

After pilot, run cleanup: `DELETE FROM complaints WHERE pilot_scenario_id IS NOT NULL` etc., then re-onboard FUW production.
