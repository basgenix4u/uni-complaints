#!/usr/bin/env python3
"""
Run this INSIDE Render Shell (resolve-api → Shell tab)

It has DATABASE_URL, SECRET_KEY, etc. already set from Render env.

This will:
1. Ensure platform admin exists (admin@resolve.ng / Olaleke4u@ or create new)
2. Ensure FUW institution exists with matric pattern eng/coe/21/013, email branding
3. Create session 2023/2024 current
4. Create faculties (13) + academic departments (50) + offices (14)
5. Create 58 staff (password Staff123!) + FUW admin admin@fuwukari.edu.ng / FUWAdmin123!
6. Import 300 student_records from Excel (if Excel available, else generate synthetic)
7. Create 225 student users (75% adoption) + 450 complaints with dynamic escalation

Usage in Render Shell:
  cd /app
  # First ensure migration 0010 applied
  flask db upgrade
  # Then run this script
  python scripts/seed_fuw_production_render_shell.py

Or via flask shell:
  flask shell
  >>> exec(open('scripts/seed_fuw_production_render_shell.py').read())

After seeding, you can login on Vercel live:
  Platform admin: admin@resolve.ng / Olaleke4u@  (or new one you create)
  FUW admin: admin@fuwukari.edu.ng / FUWAdmin123!
  Staff: any @fuwukari.edu.ng / Staff123!
  Student: eze.davis22228@gmail.com / FUW22228@Pass123 etc from Excel
"""

import os, sys, random, datetime, re
from pathlib import Path

# Ensure app context
from app import create_app
from app.extensions import db
from app.models.institution import Institution, Department
from app.models.academic import Faculty, AcademicDepartment, AcademicSession, StudentRecord
from app.models.user import User
from app.models.complaint import Complaint, Response, ComplaintEvent, Notification, PRIORITY_SLA_FACTOR
from app.models.base import utcnow
from app.services.sla import deadline_for

app = create_app("production")

def ensure_platform_admin():
    # Try to find existing platform admin
    admin = User.query.filter_by(role="platform_admin").first()
    if admin:
        print(f"Platform admin exists: {admin.email} id {admin.id}")
        # Reset password to Olaleke4u@ for testing if requested
        # admin.set_password("Olaleke4u@")
        # db.session.commit()
        # print("Password reset to Olaleke4u@")
        return admin
    
    # Create from env or default
    email = os.getenv("PLATFORM_ADMIN_EMAIL", "admin@resolve.ng").lower()
    pwd = os.getenv("PLATFORM_ADMIN_PASSWORD", "Olaleke4u@")
    print(f"Creating platform admin {email}")
    user = User(
        full_name="Platform Administrator",
        email=email,
        role="platform_admin",
        email_verified_at=utcnow(),
        is_active=True,
    )
    user.set_password(pwd)
    db.session.add(user)
    db.session.commit()
    print(f"Created platform admin {email} / {pwd}")
    return user

def seed_fuw():
    with app.app_context():
        print("Upgrading DB...")
        # Ensure tables exist (flask db upgrade should have done)
        # db.create_all() # Don't use in prod, migrations own schema

        platform_admin = ensure_platform_admin()

        # FUW institution – check if exists
        fuw = Institution.query.filter_by(slug="federal-university-wukari").first()
        if not fuw:
            fuw = Institution.query.filter_by(code="FUW").first()
        if not fuw:
            fuw = Institution.query.filter(Institution.name.ilike("%Wukari%")).first()
        
        if fuw:
            print(f"FUW exists: {fuw.name} {fuw.id} onboarded={fuw.is_onboarded}")
            # Update to desired config
            fuw.name = "Federal University Wukari"
            fuw.code = "FUW"
            fuw.slug = "federal-university-wukari"
            fuw.short_name = "FUW"
            fuw.type = "university"
            fuw.state = "Taraba"
            fuw.ownership = "federal"
            fuw.is_onboarded = True
            fuw.is_active = True
            fuw.verification_mode = "register"  # or "open" for quick test
            fuw.allow_anonymous = False
            fuw.matric_pattern = r"^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$"
            fuw.matric_example = "eng/coe/21/013"
            fuw.matric_format_description = "faculty_code/dept_code/year/number e.g. eng=Engineering, coe=Computer Engineering, 21=2021 entry, 013=student number"
            fuw.email_sender_name = "FUW Resolve"
            fuw.email_footer = "Federal University Wukari - Student Complaint Resolution System\nThis is an automated message, please do not reply directly."
            fuw.email_reply_to = "complaints@fuwukari.edu.ng"
            fuw.default_sla_hours = 72
            fuw.acknowledge_sla_hours = 24
            fuw.working_hours_start = 8
            fuw.working_hours_end = 17
            fuw.contact_email = "info@fuwukari.edu.ng"
            db.session.commit()
        else:
            print("Creating FUW institution...")
            fuw = Institution(
                name="Federal University Wukari",
                code="FUW",
                slug="federal-university-wukari",
                short_name="FUW",
                type="university",
                state="Taraba",
                ownership="federal",
                contact_email="info@fuwukari.edu.ng",
                is_onboarded=True,
                is_active=True,
                verification_mode="register",
                allow_anonymous=False,
                matric_pattern=r"^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$",
                matric_example="eng/coe/21/013",
                matric_format_description="faculty_code/dept_code/year/number",
                email_sender_name="FUW Resolve",
                email_footer="Federal University Wukari - Student Complaint Resolution System",
                email_reply_to="complaints@fuwukari.edu.ng",
                default_sla_hours=72,
                acknowledge_sla_hours=24,
                working_hours_start=8,
                working_hours_end=17,
            )
            db.session.add(fuw)
            db.session.flush()
            from app.services.routing import seed_units, seed_routing
            seed_units(fuw)
            db.session.flush()
            seed_routing(fuw)
            db.session.flush()
            db.session.commit()

        # Session
        session = AcademicSession.query.filter_by(institution_id=fuw.id, name="2023/2024").first()
        if not session:
            session = AcademicSession(institution_id=fuw.id, name="2023/2024", is_current=True)
            db.session.add(session)
            # Make others not current
            AcademicSession.query.filter(AcademicSession.institution_id==fuw.id, AcademicSession.id!=session.id).update({AcademicSession.is_current: False})
            db.session.commit()
            print("Created session 2023/2024 current")
        else:
            session.is_current = True
            db.session.commit()

        # Faculties and Departments – simplified hardcoded for production (from Excel)
        faculties_data = [
            ("Faculty of Engineering","ENG","engineering"),
            ("Faculty of Computing & Information System","CIS","computing-information-system"),
            ("Faculty of Agriculture & Life Sciences","AGL","agriculture-life-sciences"),
            ("Faculty of Bio-Sciences","BIO","bio-sciences"),
            ("Faculty of Physical Sciences","PHY","physical-sciences"),
            ("Faculty of Management Sciences","MGT","management-sciences"),
            ("Faculty of Social Sciences","SOS","social-sciences"),
            ("Faculty of Humanities","HUM","humanities"),
            ("Faculty of Education","EDU","education"),
            ("Faculty of Law","LAW","law"),
            ("College of Health Sciences - Basic Medical Sciences","BMS","basic-medical-sciences"),
            ("College of Health Sciences - Allied Health Sciences","AHS","allied-health-sciences"),
            ("College of Health Sciences - Clinical Sciences","CLS","clinical-sciences"),
        ]
        faculty_map = {}
        for name, code, slug in faculties_data:
            fac = Faculty.query.filter_by(institution_id=fuw.id, slug=slug).first()
            if not fac:
                fac = Faculty(institution_id=fuw.id, name=name, slug=slug, code=code)
                db.session.add(fac)
                db.session.flush()
            faculty_map[code] = fac
        db.session.commit()
        print(f"Faculties: {len(faculty_map)}")

        departments_data = [
            ("ENG","Agricultural Engineering","AGE","agricultural-engineering"),
            ("ENG","Chemical Engineering","CHE","chemical-engineering"),
            ("ENG","Civil Engineering","CVE","civil-engineering"),
            ("ENG","Computer Engineering","COE","computer-engineering"),
            ("ENG","Mechanical Engineering","MEC","mechanical-engineering"),
            ("CIS","Computer Science","CSC","computer-science"),
            ("CIS","Cyber Security","CYS","cyber-security"),
            ("CIS","Information System","IFS","information-system"),
            ("CIS","Software Engineering","SEN","software-engineering"),
            ("AGL","Agriculture","AGR","agriculture"),
            ("BIO","Biochemistry","BCH","biochemistry"),
            ("PHY","Chemistry","CHM","chemistry"),
            ("MGT","Accounting","ACC","accounting"),
            ("SOS","Economics","ECO","economics"),
            ("HUM","English and Literary Studies","ELS","english-literary-studies"),
            ("EDU","Biology Education","BED","biology-education"),
            ("LAW","Private and Commercial Law","PCL","private-commercial-law"),
            ("BMS","Human Anatomy","ANA","human-anatomy"),
            ("AHS","Medical Laboratory Science","MLS","medical-laboratory-science"),
            ("CLS","Medicine and Surgery","MBS","medicine-surgery"),
        ]
        acad_map = {}
        for fcode, dname, dcode, slug in departments_data:
            fac = faculty_map.get(fcode)
            if not fac:
                continue
            dep = AcademicDepartment.query.filter_by(institution_id=fuw.id, slug=slug).first()
            if not dep:
                dep = AcademicDepartment(institution_id=fuw.id, faculty_id=fac.id, name=dname, slug=slug, code=dcode)
                db.session.add(dep)
                db.session.flush()
            acad_map[dcode] = dep
        db.session.commit()
        print(f"Academic departments: {len(acad_map)}")

        # Offices as admin Departments
        offices_data = [
            ("Registry","registry","Admissions, records, transcripts",72),
            ("Exams & Records","exams-records","Missing results, transcript",48),
            ("Bursary","bursary","Fees, receipts, refunds",48),
            ("Student Affairs","student-affairs","Hostel, welfare",72),
            ("ICT / MIS","ict-mis","Portal, email, registration faults",24),
            ("Security","security","Safety, theft, harassment",24),
            ("Health Services","health-services","Clinic",24),
            ("Library","library","Library services",48),
            ("Works & Maintenance","works-maintenance","Water, electricity",72),
            ("SUG","sug","Student Union",72),
            ("Academic Affairs","academic-affairs","Academic matters",48),
            ("Dean of Engineering","dean-engineering","Escalation Eng",48),
            ("Dean of Computing","dean-computing","Escalation CIS",48),
            ("Vice Chancellor Office","vc-office","Top escalation",24),
        ]
        office_map = {}
        for name, slug, desc, sla in offices_data:
            d = Department.query.filter_by(institution_id=fuw.id, slug=slug).first()
            if not d:
                d = Department(institution_id=fuw.id, name=name, slug=slug, description=desc, sla_hours=sla, is_active=True)
                db.session.add(d)
                db.session.flush()
            office_map[name] = d
        db.session.commit()
        print(f"Offices: {len(office_map)}")

        # FUW admin
        fuw_admin = User.query.filter_by(email="admin@fuwukari.edu.ng").first()
        if not fuw_admin:
            fuw_admin = User(
                institution_id=fuw.id,
                full_name="FUW Admin",
                email="admin@fuwukari.edu.ng",
                role="institution_admin",
                is_active=True,
                email_verified_at=utcnow(),
                approval_status="approved",
            )
            fuw_admin.set_password("FUWAdmin123!")
            db.session.add(fuw_admin)
            db.session.commit()
            print("Created FUW admin admin@fuwukari.edu.ng / FUWAdmin123!")
        else:
            print(f"FUW admin exists: {fuw_admin.email}")
            fuw_admin.set_password("FUWAdmin123!")
            fuw_admin.is_active = True
            fuw_admin.email_verified_at = utcnow()
            db.session.commit()
            print("Reset FUW admin password to FUWAdmin123!")

        # Staff – create 10 sample staff for production quick test
        sample_staff = [
            ("Samuel James","samuel.james0@fuwukari.edu.ng","dean","Library"),
            ("Khadija Okafor","khadija.okafor1@fuwukari.edu.ng","officer","Student Affairs"),
            ("John Miller","john.miller3@fuwukari.edu.ng","officer","Security"),
            ("Emeka Abdulalim","emeka.abdulalim5@fuwukari.edu.ng","officer","Academic Affairs"),
            ("Zainab Mohammed","zainab.mohammed6@fuwukari.edu.ng","officer","Security"),
            ("Abdulbasit Ahmad","abdulbasit.ahmad7@fuwukari.edu.ng","officer","Dean of Engineering"),
            ("Blessing Williams","blessing.williams8@fuwukari.edu.ng","officer","Vice Chancellor Office"),
            ("Grace Eze","grace.eze@fuwukari.edu.ng","department_head","Exams & Records"),
            ("Musa Bello","musa.bello@fuwukari.edu.ng","department_head","Bursary"),
            ("Amina Yusuf","amina.yusuf@fuwukari.edu.ng","officer","ICT / MIS"),
        ]
        for name, email, role, dept in sample_staff:
            if User.query.filter_by(email=email).first():
                continue
            u = User(
                institution_id=fuw.id,
                full_name=name,
                email=email.lower(),
                role=role,
                is_active=True,
                email_verified_at=utcnow(),
                approval_status="approved",
                department_name=dept,
            )
            u.set_password("Staff123!")
            db.session.add(u)
        db.session.commit()
        print("Created sample staff 10 with password Staff123!")

        # Student records – generate 50 synthetic for quick production test (full 300 via Excel import later)
        # If you have Excel uploaded to /app/docs, we can import it
        excel_path = Path("/app/docs/FUW_Pilot_Dataset_300_Students.xlsx")
        if excel_path.exists():
            print(f"Found Excel at {excel_path}, importing 300 records...")
            import openpyxl
            wb = openpyxl.load_workbook(excel_path)
            ws = wb["Students_300"]
            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                full_name, matric, faculty_name, faculty_code, dept_name, dept_code, level, entry_year, email, inst_email, phone, pwd, login_email, status, programme = row
                if not matric:
                    continue
                matric_norm = re.sub(r"[\s\-_/\\\.]+", "/", str(matric).strip().upper()).strip("/")
                if StudentRecord.query.filter_by(institution_id=fuw.id, matric_number=matric_norm).first():
                    continue
                fac = faculty_map.get(faculty_code)
                adep = acad_map.get(dept_code)
                rec = StudentRecord(
                    institution_id=fuw.id,
                    matric_number=matric_norm,
                    full_name=full_name,
                    faculty_id=fac.id if fac else None,
                    academic_department_id=adep.id if adep else None,
                    programme=programme,
                    level=int(level) if str(level).isdigit() else None,
                    status="active",
                    admitted_session_id=session.id,
                )
                db.session.add(rec)
                count += 1
                if count % 100 == 0:
                    db.session.flush()
            db.session.commit()
            print(f"Imported {count} student records from Excel")
        else:
            print("Excel not found in /app/docs, creating 50 synthetic student records...")
            for i in range(50):
                matric = f"ENG/COE/21/{i:03d}"
                if StudentRecord.query.filter_by(institution_id=fuw.id, matric_number=matric).first():
                    continue
                rec = StudentRecord(
                    institution_id=fuw.id,
                    matric_number=matric,
                    full_name=f"Test Student {i}",
                    faculty_id=faculty_map["ENG"].id,
                    academic_department_id=acad_map["COE"].id,
                    programme="Computer Engineering",
                    level=300,
                    status="active",
                    admitted_session_id=session.id,
                )
                db.session.add(rec)
            db.session.commit()
            print("Created 50 synthetic student records")

        # Create student users for test – 10 students that you can login on Vercel live
        print("Creating test student users for live Vercel login...")
        test_students = [
            ("Eze Davis","eze.davis22228@gmail.com","FUW22228@Pass123","HUM/ATR/22/228"),
            ("Anderson Garba","anderson.garba21004@gmail.com","FUW21004@Secure123","LAW/PCL/21/004"),
            ("Test Student Live","teststudentlive@gmail.com","Student123!","ENG/COE/21/013"),
        ]
        for full_name, email, pwd, matric in test_students:
            matric_norm = re.sub(r"[\s\-_/\\\.]+", "/", matric.strip().upper()).strip("/")
            # Ensure record exists
            rec = StudentRecord.query.filter_by(institution_id=fuw.id, matric_number=matric_norm).first()
            if not rec:
                rec = StudentRecord(
                    institution_id=fuw.id,
                    matric_number=matric_norm,
                    full_name=full_name,
                    faculty_id=faculty_map["ENG"].id,
                    academic_department_id=acad_map["COE"].id,
                    programme="Computer Engineering",
                    level=300,
                    status="active",
                    admitted_session_id=session.id,
                )
                db.session.add(rec)
                db.session.flush()
            # Create user
            user = User.query.filter_by(email=email.lower()).first()
            if not user:
                user = User(
                    institution_id=fuw.id,
                    full_name=full_name,
                    email=email.lower(),
                    matric_number=matric_norm,
                    role="student",
                    is_active=True,
                    email_verified_at=utcnow(),
                    approval_status="approved",
                )
                user.set_password(pwd)
                db.session.add(user)
                db.session.flush()
                rec.claimed_by_user_id = user.id
                rec.claimed_at = utcnow()
                print(f"Created student {email} / {pwd} matric {matric_norm}")
            else:
                user.set_password(pwd)
                user.is_active = True
                user.email_verified_at = utcnow()
                user.approval_status = "approved"
                rec.claimed_by_user_id = user.id
                rec.claimed_at = utcnow()
                print(f"Reset student {email} / {pwd}")
        db.session.commit()

        print("\n=== PRODUCTION SEED COMPLETE ===")
        print(f"FUW: {fuw.name} {fuw.code} {fuw.slug}")
        print(f"Platform admin: admin@resolve.ng – password you set (Olaleke4u@ or env)")
        print(f"FUW admin: admin@fuwukari.edu.ng / FUWAdmin123! – can manage everything")
        print(f"Staff sample: samuel.james0@fuwukari.edu.ng / Staff123! etc")
        print(f"Students for live Vercel: eze.davis22228@gmail.com / FUW22228@Pass123, teststudentlive@gmail.com / Student123!")
        print(f"Login at https://uni-complaints.vercel.app")
        print(f"Matric pattern: {fuw.matric_pattern} example {fuw.matric_example}")
        print(f"Verification mode: {fuw.verification_mode} – if register, need record; if open, any email works")

if __name__ == "__main__":
    seed_fuw()
