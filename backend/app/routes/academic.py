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
from app.routes.admin import slugify
from app.routes.auth import fail, ok
from app.security import staff_required, tenant_query
from app.services.register import MAX_ROWS, import_register, normalise_matric

bp = Blueprint("academic", __name__, url_prefix="/api/academic")

# A register is the one upload that is legitimately large: 20,000 students
# at roughly 80 bytes a row. Held below the 6 MB request cap so the
# failure is a clear message rather than a truncated read.
MAX_REGISTER_BYTES = 4 * 1024 * 1024


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
        # Exactly one session is current. Cleared in the same transaction
        # as the new one is set, so there is no window with two or none.
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
            # A dean's remit is this faculty, so the link is set both ways.
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
    """Load the academic tree from a spreadsheet.

    A university has dozens of departments across a dozen faculties.
    Typing them one at a time is not a product, and the registry already
    holds this as a list.

    Expects `faculty` and `department` columns. Faculties are created as
    they are encountered, so one file describes the whole tree.
    """
    upload = request.files.get("file")
    if not upload:
        return fail("Choose a file to upload.", 422, {"file": "Choose a file to upload."})

    raw = upload.read(MAX_REGISTER_BYTES + 1)
    if len(raw) > MAX_REGISTER_BYTES:
        return fail("That file is too large. Split it and try again.", 413)

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return fail("We could not read that file. Save it as CSV and try again.", 422)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return fail("That file appears to be empty.", 422)

    headers = {(h or "").strip().lower().replace(" ", "_") for h in reader.fieldnames}
    if "faculty" not in headers:
        return fail("The file needs a faculty column.", 422)

    dry_run = (request.form.get("dry_run") or "").lower() in ("1", "true", "yes")

    faculties = {f.slug: f for f in tenant_query(Faculty).all()}
    departments = {d.slug for d in tenant_query(AcademicDepartment).all()}

    summary = {
        "faculties_created": 0,
        "departments_created": 0,
        "skipped": 0,
        "problems": [],
        "dry_run": dry_run,
    }

    for number, raw_row in enumerate(reader, start=2):
        row = {
            (k or "").strip().lower().replace(" ", "_"): (v or "").strip()
            for k, v in raw_row.items()
        }

        faculty_name = row.get("faculty", "")
        department_name = row.get("department", "")

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

        if faculty is None:
            faculty = Faculty(
                institution_id=g.institution_id, name=faculty_name[:150], slug=faculty_slug
            )
            if not dry_run:
                db.session.add(faculty)
                db.session.flush()
            faculties[faculty_slug] = faculty
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
                )
            )
        departments.add(department_slug)
        summary["departments_created"] += 1

    if dry_run:
        # Nothing was written, but flush() above may have staged rows.
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

    return ok(
        {
            "summary": {
                "total": total,
                "claimed": base.filter(StudentRecord.claimed_by_user_id.isnot(None)).count(),
                "active": base.filter(StudentRecord.status == "active").count(),
                "current_session": current.to_dict() if current else None,
                "verification_mode": institution.verification_mode,
                "advice": advice,
            }
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

    summary = import_register(institution, session, raw, dry_run=dry_run)

    if not dry_run:
        structlog.get_logger().info(
            "register_imported",
            institution_id=institution.id,
            actor_id=g.current_user.id,
            session=session.name,
            created=summary["created"],
            updated=summary["updated"],
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
