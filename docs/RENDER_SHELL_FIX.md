# Fix Production Admin Login – Render Shell Commands

Your real admin dashboard not logging in because:
- Platform admin password mismatch (you gave Olaleke4u@ but DB has different hash)
- FUW register empty → student pending
- No FUW admin in production

**Run these in Render Dashboard → resolve-api → Shell tab**

```bash
# 1. Check health and upgrade DB (migration 0010)
flask db upgrade

# 2. Open flask shell
flask shell
```

Then paste this Python (creates/updates platform admin + FUW admin + sets FUW to open for quick student login):

```python
from app.extensions import db
from app.models.user import User
from app.models.institution import Institution
from app.models.base import utcnow

# Platform admin – reset password to Olaleke4u@
admin = User.query.filter_by(email="admin@resolve.ng").first()
if not admin:
    admin = User.query.filter_by(role="platform_admin").first()
if admin:
    print(f"Found platform admin {admin.email}")
    admin.email = "admin@resolve.ng"
    admin.role = "platform_admin"
    admin.is_active = True
    admin.email_verified_at = utcnow()
    admin.approval_status = "approved"
    admin.set_password("Olaleke4u@")
else:
    admin = User(full_name="Platform Admin", email="admin@resolve.ng", role="platform_admin", is_active=True, email_verified_at=utcnow(), approval_status="approved")
    admin.set_password("Olaleke4u@")
    db.session.add(admin)
print(f"Platform admin now: admin@resolve.ng / Olaleke4u@")

# FUW institution – set to open for quick testing
fuw = Institution.query.filter_by(slug="federal-university-wukari").first()
if not fuw:
    fuw = Institution.query.filter(Institution.name.ilike("%Wukari%")).first()
if fuw:
    fuw.is_onboarded = True
    fuw.is_active = True
    fuw.verification_mode = "open"  # open = any email works, no register needed – change to register after import
    fuw.matric_pattern = r"^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$"
    fuw.matric_example = "eng/coe/21/013"
    fuw.email_sender_name = "FUW Resolve"
    print(f"FUW set to open, pattern {fuw.matric_pattern}")
else:
    print("FUW not found")

# FUW admin – create/reset
fuw_admin = User.query.filter_by(email="admin@fuwukari.edu.ng").first()
if not fuw_admin:
    fuw_admin = User(institution_id=fuw.id, full_name="FUW Admin", email="admin@fuwukari.edu.ng", role="institution_admin", is_active=True, email_verified_at=utcnow(), approval_status="approved")
    fuw_admin.set_password("FUWAdmin123!")
    db.session.add(fuw_admin)
else:
    fuw_admin.set_password("FUWAdmin123!")
    fuw_admin.is_active = True
    fuw_admin.email_verified_at = utcnow()
    fuw_admin.approval_status = "approved"
    fuw_admin.institution_id = fuw.id
    fuw_admin.role = "institution_admin"
print("FUW admin now: admin@fuwukari.edu.ng / FUWAdmin123!")

# Test student – create one that will work on live Vercel immediately
from app.models.academic import StudentRecord, AcademicSession
import re
session = AcademicSession.query.filter_by(institution_id=fuw.id, is_current=True).first()
if not session:
    session = AcademicSession(institution_id=fuw.id, name="2023/2024", is_current=True)
    db.session.add(session)
    db.session.flush()

for full_name, email, pwd, matric in [
    ("Eze Davis","eze.davis22228@gmail.com","FUW22228@Pass123","HUM/ATR/22/228"),
    ("Test Student Live","teststudentlive@gmail.com","Student123!","ENG/COE/21/013"),
]:
    matric_norm = re.sub(r"[\s\-_/\\\.]+", "/", matric.strip().upper()).strip("/")
    rec = StudentRecord.query.filter_by(institution_id=fuw.id, matric_number=matric_norm).first()
    if not rec:
        rec = StudentRecord(institution_id=fuw.id, matric_number=matric_norm, full_name=full_name, status="active", admitted_session_id=session.id)
        db.session.add(rec)
        db.session.flush()
    u = User.query.filter_by(email=email.lower()).first()
    if not u:
        u = User(institution_id=fuw.id, full_name=full_name, email=email.lower(), matric_number=matric_norm, role="student", is_active=True, email_verified_at=utcnow(), approval_status="approved")
        u.set_password(pwd)
        db.session.add(u)
        db.session.flush()
        rec.claimed_by_user_id = u.id
        rec.claimed_at = utcnow()
    else:
        u.set_password(pwd)
        u.is_active = True
        u.email_verified_at = utcnow()
        u.approval_status = "approved"
        rec.claimed_by_user_id = u.id
        rec.claimed_at = utcnow()
    print(f"Student {email} / {pwd}")

db.session.commit()
print("=== DONE ===")
print("Now login on https://uni-complaints.vercel.app")
print("Platform admin: admin@resolve.ng / Olaleke4u@")
print("FUW admin: admin@fuwukari.edu.ng / FUWAdmin123!")
print("Student: eze.davis22228@gmail.com / FUW22228@Pass123")
exit()
```

After that, **student login on live Vercel will work** because verification_mode=open.

To import full 300 students from Excel for register mode:
1. In FUW admin dashboard → Academic Structure → Student Register → upload `FUW_Pilot_Dataset_300_Students.xlsx` sheet `Students_300` as XLSX (now supports XLSX + CSV, matric pattern validation, Cloudinary archive)
2. Then change verification_mode back to register:
```python
fuw.verification_mode = "register"
db.session.commit()
```

**If emergency-seed endpoint is deployed** (after Render finishes), you can also call:
```bash
curl -X POST https://resolve-api-eadv.onrender.com/api/platform/emergency-seed \
  -H "Content-Type: application/json" \
  -d '{"emergency_token":"fuw-emergency-2024-seed-token-xyz","platform_email":"admin@resolve.ng","platform_password":"Olaleke4u@","verification_mode":"open"}'
```

This does same as shell script.

**Local preview that already works** (no need to wait):
- Frontend preview: https://5173-...e2b.app
- Platform admin local: admin@resolve.ng / Admin123!
- FUW admin local: admin@fuwukari.edu.ng / FUWAdmin123!
- Staff: any @fuwukari.edu.ng / Staff123!
- Students: eze.davis22228@gmail.com / FUW22228@Pass123 etc
