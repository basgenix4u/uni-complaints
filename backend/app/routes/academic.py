"""Academic structure and the student register.

The tables and the import logic have existed since stage 1 with no way to
reach them over HTTP, which meant `verification_mode="register"` — the
documented default and the strongest way to verify a student — silently
degraded to manual review of every single registration. This module is
what makes that mode real.

Two hierarchies are kept apart deliberately. `Department` in
`institution.py` is administrative: Bursary, Registry, the units that
resolve complaints. `Faculty` and `AcademicDepartment` here are where a
student actually sits. A fee query goes to the former; a disputed grade
goes to the latter.

Now supports both CSV and XLSX (openpyxl) for structure and register
imports. Matric format is not hardcoded – each institution defines its
own pattern (e.g. FUW: eng/coe/21/013). Register files are archived to
Cloudinary when available (free tier 25GB, authenticated raw).
"""

import csv
import io

import structlog
from flask import Blueprint, g, request

from app.extensions import db, limiter
from app.models.academic import (
    ENROLMENT_STATUSES,
    AcademicDepartment,
    AcademicSession,
    Faculty,
    StudentRecord,
)
from app.models.institution import Institution
from app.models.register_import import RegisterImport
from app.routes.admin import slugify
from app.routes.auth import fail, ok
from app.security import staff_required, tenant_query
from app.services.register import MAX_ROWS, import_register, normalise_matric, parse_register_file

bp = Blueprint("academic", __name__, url_prefix="/api/academic")

# A register is the one upload that is legitimately large: 20,000 students
# at roughly 80 bytes a row. Held below the 6 MB request cap so the
# failure is a clear message rather than a truncated read.
MAX_REGISTER_BYTES = 4 * 1024 * 1024


# -- helpers for structure bulk (CSV+XLSX) -------------------------------

def _parse_structure_file(raw: bytes, filename: str = "") -> tuple[list[dict], list[str]]:
    """Parse faculty/department structure from CSV or XLSX.

    Returns (rows, problems). Each row is dict with faculty, department, code, etc.
    """
    name_lower = (filename or "").lower()
    is_xlsx = name_lower.endswith(".xlsx") or name_lower.endswith(".xls") or raw[:2] == b"PK"

    rows = []
    problems = []

    if is_xlsx:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                return [], ["That Excel file appears to be empty."]
            iter_rows = ws.iter_rows(values_only=True)
            try:
                header_row = next(iter_rows)
            except StopIteration:
                return [], ["That Excel file appears to be empty."]
            if not header_row:
                return [], ["That Excel file appears to be empty."]
            headers = [str(h).strip().lower().replace(" ", "_") if h else "" for h in header_row]
            for number, vals in enumerate(iter_rows, start=2):
                if not vals:
                    continue
                row = {}
                for idx, h in enumerate(headers):
                    if idx < len(vals):
                        v = vals[idx]
                        row[h] = str(v).strip() if v is not None else ""
                    else:
                        row[h] = ""
                if not any(row.values()):
                    continue
                rows.append(row)
            return rows, problems
        except ImportError:
            problems.append("XLSX support requires openpyxl. Install it or upload CSV.")
            # fall through to CSV
        except Exception as e:
            return [], [f"Could not read Excel file: {str(e)[:200]}"]

    # CSV path
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return [], ["We could not read that file. Save it as CSV and try again."]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["That file appears to be empty."]

    for raw_row in reader:
        row = {
            (k or "").strip().lower().replace(" ", "_"): (v or "").strip()
            for k, v in raw_row.items()
        }
        rows.append(row)

    return rows, problems


# -- sessions ---------------------------------------------------------


@bp.get("/sessions")
@staff_required("institution_admin")
def list_sessions():
    rows = (
        tenant_query(AcademicSession)
        .order_by(AcademicSession.is_current.desc(), AcademicSession.name.desc())
        .all()
    )
    return ok({"sessions": [s.to_dict() for s in rows]})


@bp.post("/sessions")
@staff_required("institution_admin")
def create_session():
    """Open an academic session.

    Admissions happen every year, so the register is not loaded once and
    forgotten. Tying each import to a session is what lets a later intake
    be added without destroying the previous one.
    """
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()

    if not 4 <= len(name) <= 20:
        return fail(
            "Enter the session as your institution writes it, for example 2025/2026.",
            422,
            {"name": "Enter the session, for example 2025/2026."},
        )

    if tenant_query(AcademicSession).filter(AcademicSession.name == name).first():
        return fail("That session already exists.", 409, {"name": "That session already exists."})

    make_current = bool(payload.get("is_current"))
    session = AcademicSession(
        institution_id=g.institution_id, name=name, is_current=make_current
    )

    if make_current:
        tenant_query(AcademicSession).update(
            {AcademicSession.is_current: False}, synchronize_session=False
        )
        session.is_current = True

    db.session.add(session)
    db.session.commit()
    return ok({"session": session.to_dict()}, "Session created.", 201)


@bp.put("/sessions/<session_id>/current")
@staff_required("institution_admin")
def set_current_session(session_id):
    session = tenant_query(AcademicSession).filter_by(id=session_id).first()
    if not session:
        return fail("We could not find that session.", 404)

    tenant_query(AcademicSession).update(
        {AcademicSession.is_current: False}, synchronize_session=False
    )
    session.is_current = True
    db.session.commit()

    return ok({"session": session.to_dict()}, f"{session.name} is now the current session.")


# -- faculties --------------------------------------------------------


@bp.get("/faculties")
@staff_required("officer")
def list_faculties():
    """The academic tree.

    Readable by any staff member because a complaint detail screen needs
    to name a student's faculty; only an administrator may change it.
    """
    rows = tenant_query(Faculty).order_by(Faculty.name).all()
    return ok({"faculties": [f.to_dict(include_departments=True) for f in rows]})


@bp.post("/faculties")
@staff_required("institution_admin")
def create_faculty():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()

    if not 2 <= len(name) <= 150:
        return fail("Enter the faculty name.", 422, {"name": "Enter the faculty name."})

    slug = slugify(payload.get("slug") or name)
    if not slug:
        return fail("That name cannot be used.", 422, {"name": "Use letters or numbers."})

    if tenant_query(Faculty).filter(Faculty.slug == slug).first():
        return fail("A faculty with that name already exists.", 409, {"name": "Already exists."})

    faculty = Faculty(
        institution_id=g.institution_id,
        name=name,
        slug=slug,
        code=(payload.get("code") or "").strip()[:20] or None,
    )
    db.session.add(faculty)
    db.session.commit()

    return ok({"faculty": faculty.to_dict()}, "Faculty added.", 201)


@bp.put("/faculties/<faculty_id>")
@staff_required("institution_admin")
def update_faculty(faculty_id):
    faculty = tenant_query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        return fail("We could not find that faculty.", 404)

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload["name"] or "").strip()
        if not 2 <= len(name) <= 150:
            return fail("Enter the faculty name.", 422, {"name": "Enter the faculty name."})
        faculty.name = name

    if "code" in payload:
        faculty.code = (payload["code"] or "").strip()[:20] or None

    if "is_active" in payload:
        faculty.is_active = bool(payload["is_active"])

    if "dean_user_id" in payload:
        from app.models.user import User

        dean_id = payload["dean_user_id"]
        if dean_id:
            dean = tenant_query(User).filter_by(id=dean_id).first()
            if not dean or dean.role != "dean":
                return fail("Choose somebody with the dean role.", 422)
            faculty.dean_user_id = dean.id
            dean.faculty_id = faculty.id
        else:
            faculty.dean_user_id = None

    db.session.commit()
    return ok({"faculty": faculty.to_dict()}, "Faculty updated.")


# -- academic departments ---------------------------------------------


@bp.post("/faculties/<faculty_id>/departments")
@staff_required("institution_admin")
def create_academic_department(faculty_id):
    faculty = tenant_query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        return fail("We could not find that faculty.", 404)

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()

    if not 2 <= len(name) <= 150:
        return fail("Enter the department name.", 422, {"name": "Enter the department name."})

    slug = slugify(payload.get("slug") or name)
    if tenant_query(AcademicDepartment).filter(AcademicDepartment.slug == slug).first():
        return fail(
            "A department with that name already exists.", 409, {"name": "Already exists."}
        )

    department = AcademicDepartment(
        institution_id=g.institution_id,
        faculty_id=faculty.id,
        name=name,
        slug=slug,
        code=(payload.get("code") or "").strip()[:20] or None,
    )
    db.session.add(department)
    db.session.commit()

    return ok({"department": department.to_dict()}, "Department added.", 201)


@bp.put("/departments/<department_id>")
@staff_required("institution_admin")
def update_academic_department(department_id):
    department = tenant_query(AcademicDepartment).filter_by(id=department_id).first()
    if not department:
        return fail("We could not find that department.", 404)

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload["name"] or "").strip()
        if not 2 <= len(name) <= 150:
            return fail("Enter the department name.", 422, {"name": "Enter the department name."})
        department.name = name

    if "code" in payload:
        department.code = (payload["code"] or "").strip()[:20] or None

    if "is_active" in payload:
        department.is_active = bool(payload["is_active"])

    if "head_user_id" in payload:
        from app.models.user import User

        head_id = payload["head_user_id"]
        if head_id:
            head = tenant_query(User).filter_by(id=head_id).first()
            if not head or not head.is_staff:
                return fail("Choose a member of staff.", 422)
            department.head_user_id = head.id
        else:
            department.head_user_id = None

    db.session.commit()
    return ok({"department": department.to_dict()}, "Department updated.")


@bp.post("/structure/bulk")
@staff_required("institution_admin")
@limiter.limit("20 per hour")
def import_structure():
    """Load the academic tree from a spreadsheet (CSV or XLSX).

    A university has dozens of departments across a dozen faculties.
    Typing them one at a time is not a product, and the registry already
    holds this as a list.

    Expects `faculty` and `department` columns. Faculties are created as
    they are encountered, so one file describes the whole tree.
    Supports both CSV and XLSX – format is detected from filename or
    file magic. Matric format awareness: faculty_code and department_code
    columns are respected when present (e.g. FUW eng/coe/21/013).
    """
    upload = request.files.get("file")
    if not upload:
        return fail("Choose a file to upload.", 422, {"file": "Choose a file to upload."})

    raw = upload.read(MAX_REGISTER_BYTES + 1)
    if len(raw) > MAX_REGISTER_BYTES:
        return fail("That file is too large. Split it and try again.", 413)
    if not raw:
        return fail("That file is empty.", 422)

    filename = upload.filename or ""
    rows, problems = _parse_structure_file(raw, filename)

    if not rows and problems:
        return fail(problems[0], 422)

    headers = set()
    for r in rows:
        headers.update(r.keys())
    if "faculty" not in headers:
        return fail("The file needs a faculty column.", 422)

    dry_run = (request.form.get("dry_run") or "").lower() in ("1", "true", "yes")

    faculties = {f.slug: f for f in tenant_query(Faculty).all()}
    faculties_by_code = {(f.code or "").lower(): f for f in tenant_query(Faculty).all() if f.code}
    departments = {d.slug for d in tenant_query(AcademicDepartment).all()}

    summary = {
        "faculties_created": 0,
        "departments_created": 0,
        "skipped": 0,
        "problems": problems[:20],
        "dry_run": dry_run,
        "detected_type": "xlsx" if filename.lower().endswith((".xlsx", ".xls")) else "csv",
    }

    for number, row in enumerate(rows, start=2):
        faculty_name = row.get("faculty", "")
        department_name = row.get("department", "")
        faculty_code = row.get("faculty_code", "") or row.get("code", "")
        dept_code = row.get("department_code", "") or row.get("dept_code", "")

        if not faculty_name:
            summary["problems"].append(f"Row {number}: no faculty given.")
            continue

        if number > MAX_ROWS:
            summary["problems"].append(
                f"Only the first {MAX_ROWS} rows were read. Split the file."
            )
            break

        faculty_slug = slugify(faculty_name)
        faculty = faculties.get(faculty_slug)
        if faculty is None and faculty_code:
            faculty = faculties_by_code.get(faculty_code.lower())

        if faculty is None:
            faculty = Faculty(
                institution_id=g.institution_id,
                name=faculty_name[:150],
                slug=faculty_slug,
                code=faculty_code[:20] if faculty_code else None,
            )
            if not dry_run:
                db.session.add(faculty)
                db.session.flush()
            faculties[faculty_slug] = faculty
            if faculty_code:
                faculties_by_code[faculty_code.lower()] = faculty
            summary["faculties_created"] += 1

        if not department_name:
            continue

        department_slug = slugify(department_name)
        if department_slug in departments:
            summary["skipped"] += 1
            continue

        if not dry_run:
            db.session.add(
                AcademicDepartment(
                    institution_id=g.institution_id,
                    faculty_id=faculty.id,
                    name=department_name[:150],
                    slug=department_slug,
                    code=dept_code[:20] if dept_code else None,
                )
            )
        departments.add(department_slug)
        summary["departments_created"] += 1

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    summary["problems"] = summary["problems"][:50]
    return ok({"summary": summary}, "Checked." if dry_run else "Structure imported.")


# -- the student register ---------------------------------------------


@bp.get("/register")
@staff_required("institution_admin")
def list_register():
    """Browse the register.

    Paginated and searchable because this is tens of thousands of rows,
    and the question asked of it is almost always about one student.
    """
    query = tenant_query(StudentRecord)

    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        normalised = normalise_matric(search)
        query = query.filter(
            db.or_(
                StudentRecord.full_name.ilike(like),
                StudentRecord.matric_number.ilike(f"%{normalised}%"),
            )
        )

    status = request.args.get("status")
    if status in ENROLMENT_STATUSES:
        query = query.filter(StudentRecord.status == status)

    claimed = request.args.get("claimed")
    if claimed == "1":
        query = query.filter(StudentRecord.claimed_by_user_id.isnot(None))
    elif claimed == "0":
        query = query.filter(StudentRecord.claimed_by_user_id.is_(None))

    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    result = query.order_by(StudentRecord.matric_number).paginate(
        page=max(request.args.get("page", 1, type=int), 1), per_page=per_page, error_out=False
    )

    return ok(
        {
            "records": [r.to_dict() for r in result.items],
            "pagination": {
                "page": result.page,
                "per_page": result.per_page,
                "total_items": result.total,
                "total_pages": result.pages or 1,
                "has_next": result.has_next,
                "has_prev": result.has_prev,
            },
        }
    )


@bp.get("/register/summary")
@staff_required("institution_admin")
def register_summary():
    """Whether the register is usable, and how far it has been taken up."""
    base = tenant_query(StudentRecord)
    total = base.count()

    current = tenant_query(AcademicSession).filter(AcademicSession.is_current.is_(True)).first()
    institution = db.session.get(Institution, g.institution_id)

    advice = None
    if (institution.verification_mode or "") == "register":
        if not current:
            advice = (
                "No session is open, so a register cannot be imported. Open the current "
                "session first."
            )
        elif total == 0:
            advice = (
                "This institution verifies students against the register, and the register "
                "is empty. Every registration will wait for manual approval until it is "
                "imported."
            )

    # Include matric pattern info
    return ok(
        {
            "summary": {
                "total": total,
                "claimed": base.filter(StudentRecord.claimed_by_user_id.isnot(None)).count(),
                "active": base.filter(StudentRecord.status == "active").count(),
                "current_session": current.to_dict() if current else None,
                "verification_mode": institution.verification_mode,
                "matric_pattern": institution.matric_pattern,
                "matric_example": institution.matric_example,
                "matric_format_description": institution.matric_format_description,
                "advice": advice,
            }
        }
    )


@bp.get("/register/imports")
@staff_required("institution_admin")
def list_register_imports():
    """List archived register imports (Cloudinary or local)."""
    query = tenant_query(RegisterImport).order_by(RegisterImport.created_at.desc())
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    result = query.paginate(
        page=max(request.args.get("page", 1, type=int), 1), per_page=per_page, error_out=False
    )
    return ok(
        {
            "imports": [r.to_dict() for r in result.items],
            "pagination": {
                "page": result.page,
                "per_page": result.per_page,
                "total_items": result.total,
                "total_pages": result.pages or 1,
            },
        }
    )


@bp.post("/register/import")
@staff_required("institution_admin")
@limiter.limit("20 per hour")
def import_student_register():
    """Load the student register for a session.

    A dry run is the expected first call: an administrator should see
    what a file will do before it does it, and a register import touches
    every student's ability to sign up.

    Now accepts CSV and XLSX, validates against institution's matric_pattern,
    and archives the file to Cloudinary (free tier) when enabled.
    """
    upload = request.files.get("file")
    if not upload:
        return fail("Choose a file to upload.", 422, {"file": "Choose a file to upload."})

    raw = upload.read(MAX_REGISTER_BYTES + 1)
    if len(raw) > MAX_REGISTER_BYTES:
        return fail(
            "That file is too large. Split it into smaller files and import each.", 413
        )
    if not raw:
        return fail("That file is empty.", 422)

    session_id = (request.form.get("session_id") or "").strip()
    if session_id:
        session = tenant_query(AcademicSession).filter_by(id=session_id).first()
    else:
        session = (
            tenant_query(AcademicSession)
            .filter(AcademicSession.is_current.is_(True))
            .first()
        )

    if not session:
        return fail(
            "Open the current academic session before importing a register.",
            422,
            {"session_id": "No session chosen, and none is marked current."},
        )

    dry_run = (request.form.get("dry_run") or "").lower() in ("1", "true", "yes")
    institution = db.session.get(Institution, g.institution_id)

    filename = upload.filename or f"register_{session.name}.csv"

    summary = import_register(
        institution,
        session,
        raw,
        dry_run=dry_run,
        filename=filename,
        uploaded_by=g.current_user,
    )

    if not dry_run:
        structlog.get_logger().info(
            "register_imported",
            institution_id=institution.id,
            actor_id=g.current_user.id,
            session=session.name,
            created=summary["created"],
            updated=summary["updated"],
            storage_backend=summary.get("storage_backend", "local"),
            detected_type=summary.get("detected_type", "csv"),
        )

    return ok({"summary": summary}, "Checked." if dry_run else "Register imported.")


@bp.put("/register/<record_id>")
@staff_required("institution_admin")
def update_record(record_id):
    """Correct one row.

    A register is never perfectly accurate, and a student blocked by a
    typo in their own matriculation number should not have to wait for
    the next import.
    """
    record = tenant_query(StudentRecord).filter_by(id=record_id).first()
    if not record:
        return fail("We could not find that record.", 404)

    payload = request.get_json(silent=True) or {}

    if "full_name" in payload:
        name = (payload["full_name"] or "").strip()
        if len(name) < 2:
            return fail("Enter the student's name.", 422, {"full_name": "Enter the name."})
        record.full_name = name[:150]

    if "status" in payload:
        status = (payload["status"] or "").strip()
        if status not in ENROLMENT_STATUSES:
            return fail(
                f"Choose one of: {', '.join(ENROLMENT_STATUSES)}.", 422, {"status": "Invalid."}
            )
        record.status = status

    if "level" in payload:
        level = payload["level"]
        if level is not None and (not isinstance(level, int) or not 0 < level <= 12):
            return fail("Level should be a number such as 100 or 200.", 422)
        record.level = level

    if "academic_department_id" in payload:
        department_id = payload["academic_department_id"]
        if department_id:
            department = (
                tenant_query(AcademicDepartment).filter_by(id=department_id).first()
            )
            if not department:
                return fail("We could not find that department.", 422)
            record.academic_department_id = department.id
            record.faculty_id = department.faculty_id
        else:
            record.academic_department_id = None

    db.session.commit()
    return ok({"record": record.to_dict()}, "Record updated.")


@bp.delete("/register/<record_id>")
@staff_required("institution_admin")
def release_record(record_id):
    """Unlink an account from a register row.

    Not a delete: the row stays. This is the remedy when the wrong person
    claimed a matriculation number, and it has to exist because the claim
    is otherwise permanent and the real student is locked out for good.
    """
    record = tenant_query(StudentRecord).filter_by(id=record_id).first()
    if not record:
        return fail("We could not find that record.", 404)

    if record.claimed_by_user_id is None:
        return fail("Nobody has claimed that record.", 409)

    released = record.claimed_by_user_id
    record.claimed_by_user_id = None
    record.claimed_at = None
    db.session.commit()

    structlog.get_logger().warning(
        "register_claim_released",
        institution_id=g.institution_id,
        actor_id=g.current_user.id,
        record_id=record.id,
        released_user_id=released,
    )

    return ok({"record": record.to_dict()}, "Released. The student can register again.")
