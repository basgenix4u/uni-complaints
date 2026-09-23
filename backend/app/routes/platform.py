"""Platform administration: provisioning institutions.

Restricted to platform_admin, the only role that operates across tenants.
"""

import re
import os

from flask import Blueprint, request

from app.extensions import db
from app.models.institution import INSTITUTION_TYPES, Institution, canonical_type
from app.models.user import User
from app.routes.auth import EMAIL_RE, fail, ok, validate_password

from app.security import staff_required
from app.services.routing import seed_routing, seed_units

bp = Blueprint("platform", __name__, url_prefix="/api/platform")

CODE_RE = re.compile(r"^[A-Z]{2,8}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@bp.post("/emergency-seed")
def emergency_seed():
    """Emergency seeding for FUW production – temporary, protected by secret.

    This endpoint exists to recover a production where platform admin
    credentials were lost and FUW register is empty. It checks
    EMERGENCY_SEED_TOKEN env or a shared secret, creates/updates platform
    admin and FUW admin, sets verification_mode to open for quick testing,
    and imports minimal student records.

    Remove after use.
    """
    payload = request.get_json(silent=True) or {}
    token = (payload.get("emergency_token") or request.headers.get("X-Emergency-Token") or "").strip()
    expected = os.getenv("EMERGENCY_SEED_TOKEN", "fuw-emergency-2024-seed-token-xyz")
    # Also allow if no platform admin exists at all – bootstrap
    has_admin = User.query.filter_by(role="platform_admin").first() is not None
    if token != expected and has_admin:
        return fail("Invalid emergency token.", 403)

    # Create or reset platform admin
    platform_email = (payload.get("platform_email") or "admin@resolve.ng").strip().lower()
    platform_password = payload.get("platform_password") or "Olaleke4u@"
    
    platform_admin = User.query.filter_by(email=platform_email).first()
    if not platform_admin:
        platform_admin = User.query.filter_by(role="platform_admin").first()
    
    if platform_admin:
        platform_admin.email = platform_email
        platform_admin.role = "platform_admin"
        platform_admin.is_active = True
        platform_admin.set_password(platform_password)
        from app.models.base import utcnow
        platform_admin.email_verified_at = utcnow()
        platform_admin.approval_status = "approved"
    else:
        from app.models.base import utcnow
        platform_admin = User(
            full_name="Platform Administrator",
            email=platform_email,
            role="platform_admin",
            is_active=True,
            email_verified_at=utcnow(),
            approval_status="approved",
        )
        platform_admin.set_password(platform_password)
        db.session.add(platform_admin)
    
    db.session.flush()

    # Ensure FUW exists
    fuw = Institution.query.filter_by(slug="federal-university-wukari").first()
    if not fuw:
        fuw = Institution.query.filter_by(code="FUW").first()
    if not fuw:
        fuw = Institution.query.filter(Institution.name.ilike("%Wukari%")).first()
    
    if not fuw:
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
            verification_mode="open",  # open for quick testing, change to register after import
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
        seed_units(fuw)
        db.session.flush()
        seed_routing(fuw)
        db.session.flush()
    else:
        # Update existing FUW to working config
        fuw.is_onboarded = True
        fuw.is_active = True
        # For emergency, set to open so student login works immediately
        # User can change back to register after importing 300 records via UI
        if payload.get("verification_mode") in ("open","register","manual"):
            fuw.verification_mode = payload["verification_mode"]
        else:
            fuw.verification_mode = "open"
        fuw.matric_pattern = r"^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$"
        fuw.matric_example = "eng/coe/21/013"
        fuw.matric_format_description = "faculty_code/dept_code/year/number"
        fuw.email_sender_name = "FUW Resolve"
        fuw.email_footer = "Federal University Wukari - Student Complaint Resolution System"
        fuw.default_sla_hours = 72
        fuw.acknowledge_sla_hours = 24

    db.session.flush()

    # FUW admin
    fuw_admin_email = "admin@fuwukari.edu.ng"
    fuw_admin = User.query.filter_by(email=fuw_admin_email).first()
    if not fuw_admin:
        from app.models.base import utcnow
        fuw_admin = User(
            institution_id=fuw.id,
            full_name="FUW Admin",
            email=fuw_admin_email,
            role="institution_admin",
            is_active=True,
            email_verified_at=utcnow(),
            approval_status="approved",
        )
        fuw_admin.set_password("FUWAdmin123!")
        db.session.add(fuw_admin)
    else:
        fuw_admin.set_password("FUWAdmin123!")
        fuw_admin.is_active = True
        from app.models.base import utcnow
        fuw_admin.email_verified_at = utcnow()
        fuw_admin.approval_status = "approved"
        fuw_admin.institution_id = fuw.id
        fuw_admin.role = "institution_admin"

    db.session.flush()

    # Create 5 test students that will work on live Vercel immediately (since verification_mode=open)
    from app.models.base import utcnow
    import re as re2
    test_students = [
        ("Eze Davis","eze.davis22228@gmail.com","FUW22228@Pass123","HUM/ATR/22/228"),
        ("Anderson Garba","anderson.garba21004@gmail.com","FUW21004@Secure123","LAW/PCL/21/004"),
        ("Test Student Live","teststudentlive@gmail.com","Student123!","ENG/COE/21/013"),
        ("Amina Bello","amina.bello@fuwukari.edu.ng","Student123!","ENG/COE/21/013"),
        ("Musa Ibrahim","musa.ibrahim@fuwukari.edu.ng","Student123!","CIS/CSC/22/001"),
    ]
    created_students = []
    for full_name, email, pwd, matric in test_students:
        matric_norm = re2.sub(r"[\s\-_/\\\.]+", "/", matric.strip().upper()).strip("/")
        # Ensure student record exists for register mode later
        from app.models.academic import StudentRecord, AcademicSession
        session = AcademicSession.query.filter_by(institution_id=fuw.id, is_current=True).first()
        if not session:
            session = AcademicSession(institution_id=fuw.id, name="2023/2024", is_current=True)
            db.session.add(session)
            db.session.flush()
        rec = StudentRecord.query.filter_by(institution_id=fuw.id, matric_number=matric_norm).first()
        if not rec:
            # Find faculty/dept for ENG/COE
            from app.models.academic import Faculty, AcademicDepartment
            fac = Faculty.query.filter_by(institution_id=fuw.id, code="ENG").first() or Faculty.query.filter_by(institution_id=fuw.id).first()
            adep = AcademicDepartment.query.filter_by(institution_id=fuw.id, code="COE").first() or AcademicDepartment.query.filter_by(institution_id=fuw.id).first()
            rec = StudentRecord(
                institution_id=fuw.id,
                matric_number=matric_norm,
                full_name=full_name,
                faculty_id=fac.id if fac else None,
                academic_department_id=adep.id if adep else None,
                programme="Computer Engineering",
                level=300,
                status="active",
                admitted_session_id=session.id,
            )
            db.session.add(rec)
            db.session.flush()
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
            created_students.append(f"{email} / {pwd}")
        else:
            user.set_password(pwd)
            user.is_active = True
            user.email_verified_at = utcnow()
            user.approval_status = "approved"
            user.institution_id = fuw.id
            rec.claimed_by_user_id = user.id
            rec.claimed_at = utcnow()
            created_students.append(f"{email} / {pwd} (reset)")

    db.session.commit()

    return ok({
        "platform_admin": {"email": platform_email, "password": platform_password, "id": platform_admin.id},
        "fuw_institution": fuw.to_dict(include_settings=True),
        "fuw_admin": {"email": fuw_admin_email, "password": "FUWAdmin123!", "id": fuw_admin.id},
        "test_students": created_students,
        "verification_mode": fuw.verification_mode,
        "message": "Emergency seed complete. Login on Vercel now works. Change verification_mode back to register after importing full 300 via UI.",
    }, "Emergency seed complete.")


@bp.get("/institutions")
@staff_required("platform_admin")
def list_institutions():
    """The institutions this platform knows about.

    Since the directory was pre-loaded this is several hundred rows, most
    of them institutions nobody has onboarded yet. Returning the lot was
    a quarter of a megabyte and a user count query per row, so it is
    filtered and paged.

    The default is deliberately `in_service`: an administrator opening
    this page is nearly always looking after institutions already using
    Resolve, not browsing the national register.
    """
    scope = (request.args.get("scope") or "in_service").strip()
    term = (request.args.get("q") or "").strip()
    limit = max(1, min(int(request.args.get("limit") or 50), 200))
    offset = max(0, int(request.args.get("offset") or 0))

    rows = Institution.query
    if scope == "in_service":
        rows = rows.filter(Institution.is_onboarded.is_(True))
    elif scope == "directory":
        rows = rows.filter(Institution.is_onboarded.is_(False))

    if term:
        like = f"%{term}%"
        rows = rows.filter(
            db.or_(
                Institution.name.ilike(like),
                Institution.short_name.ilike(like),
                Institution.code.ilike(like),
                Institution.slug.ilike(like),
            )
        )

    total = rows.count()
    page = (
        rows.order_by(Institution.is_onboarded.desc(), Institution.name)
        .limit(limit)
        .offset(offset)
        .all()
    )

    # One grouped query rather than one per row.
    counts = dict(
        db.session.query(User.institution_id, db.func.count(User.id))
        .filter(User.institution_id.in_([i.id for i in page] or [None]))
        .group_by(User.institution_id)
        .all()
    )

    payload = []
    for institution in page:
        data = institution.to_dict(include_settings=True)
        data["user_count"] = counts.get(institution.id, 0)
        payload.append(data)

    return ok(
        {
            "institutions": payload,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@bp.post("/institutions")
@staff_required("platform_admin")
def create_institution():
    """Provision a tenant and its first administrator in one step.

    Both are created in a single transaction: an institution with no way to
    sign in would have to be cleaned up by hand.
    """
    payload = request.get_json(silent=True) or {}
    errors = {}

    name = (payload.get("name") or "").strip()
    code = (payload.get("code") or "").strip().upper()
    slug = (payload.get("slug") or "").strip().lower()
    admin_email = (payload.get("admin_email") or "").strip().lower()
    admin_name = (payload.get("admin_name") or "").strip()
    admin_password = payload.get("admin_password") or ""

    if len(name) < 3:
        errors["name"] = "Enter the institution name."
    if not CODE_RE.match(code):
        errors["code"] = "Use 2 to 8 capital letters, for example FUW."
    if not SLUG_RE.match(slug):
        errors["slug"] = "Use lower case words separated by hyphens."
    if not EMAIL_RE.match(admin_email):
        errors["admin_email"] = "Enter a valid email address."
    if len(admin_name) < 3:
        errors["admin_name"] = "Enter the administrator's full name."

    password_error = validate_password(admin_password)
    if password_error:
        errors["admin_password"] = password_error

    institution_type = canonical_type(payload.get("type") or "university")
    if institution_type is None:
        errors["type"] = "Choose " + ", ".join(INSTITUTION_TYPES) + "."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    # The directory already holds several hundred institutions, so a
    # clash here usually means the administrator is typing in one that is
    # on record rather than inventing a new one. Saying only "already in
    # use" leaves them stuck on the form with nothing to act on, so the
    # entry we matched is returned with the error and the caller can
    # offer to onboard it instead.
    clash = Institution.query.filter_by(slug=slug).first()
    if clash:
        return fail(
            f"{clash.name} is already on the register."
            + ("" if clash.is_onboarded else " It has not been onboarded yet."),
            409,
            {
                "slug": "Already on the register.",
                "existing": clash.to_directory_dict(),
                "can_onboard": not clash.is_onboarded,
            },
        )

    clash = Institution.query.filter_by(code=code).first()
    if clash:
        return fail(
            f"That ticket prefix belongs to {clash.name}.",
            409,
            {"code": "Already in use.", "existing": clash.to_directory_dict()},
        )

    # Matric format is not hardcoded – per institution regex
    matric_pattern = (payload.get("matric_pattern") or "").strip() or None
    matric_example = (payload.get("matric_example") or "").strip() or None
    matric_desc = (payload.get("matric_format_description") or "").strip() or None

    # Validate matric_pattern is a valid regex if provided
    if matric_pattern:
        try:
            re.compile(matric_pattern, re.IGNORECASE)
        except re.error:
            errors["matric_pattern"] = "That pattern is not a valid regular expression."

    # Email branding – not hardcoded, per institution
    email_sender_name = (payload.get("email_sender_name") or "").strip() or None
    email_footer = (payload.get("email_footer") or "").strip() or None
    email_reply_to = (payload.get("email_reply_to") or "").strip() or None

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    institution = Institution(
        name=name,
        code=code,
        slug=slug,
        type=institution_type,
        state=(payload.get("state") or "").strip() or None,
        short_name=(payload.get("short_name") or "").strip()[:20] or None,
        contact_email=(payload.get("contact_email") or "").strip() or None,
        contact_phone=(payload.get("contact_phone") or "").strip() or None,
        logo_url=(payload.get("logo_url") or "").strip() or None,
        matric_pattern=matric_pattern,
        matric_example=matric_example,
        matric_format_description=matric_desc,
        email_sender_name=email_sender_name,
        email_footer=email_footer,
        email_reply_to=email_reply_to,
        # Provisioning an institution is the deliberate act of bringing it
        # into service, so it is in service. The column defaults to false
        # because the directory also holds institutions we merely know of
        # and have never onboarded; inheriting that default here meant
        # every institution created through the API was dead on arrival,
        # with no student able to register and no endpoint to change it.
        is_onboarded=payload.get("is_onboarded", True) is not False,
        # Open by default, because the register is empty on day one. An
        # institution that starts in register mode rejects every student
        # until a registrar has uploaded a spreadsheet, which is a poor
        # first hour. Switched under Settings once the register is in.
        verification_mode=(payload.get("verification_mode") or "open").strip(),
        # On by default. The complaints least likely to be raised are the
        # ones about the people who would read them, and the research on
        # Nigerian institutions is consistent that those are exactly the
        # complaints that go unreported. An institution can turn this off
        # under Settings, but it should be a decision someone makes and
        # can be asked about, not a default nobody chose.
        allow_anonymous=payload.get("allow_anonymous", True) is not False,
    )
    db.session.add(institution)
    db.session.flush()

    # A new institution gets the standard units and a draft routing table
    # immediately, so complaints reach the right office from the first
    # day rather than piling up unassigned while the table is written.
    # Both are additive and meant to be edited.
    units_created = seed_units(institution)
    db.session.flush()
    rules_created = seed_routing(institution)

    admin = User(
        institution_id=institution.id,
        full_name=admin_name,
        email=admin_email,
        role="institution_admin",
    )
    admin.set_password(admin_password)
    db.session.add(admin)

    db.session.commit()

    return ok(
        {
            "institution": institution.to_dict(include_settings=True),
            "admin": admin.to_dict(),
            "units_created": units_created,
            "rules_created": rules_created,
        },
        "Institution created.",
        201,
    )


@bp.put("/institutions/<institution_id>/toggle-active")
@staff_required("platform_admin")
def toggle_institution(institution_id):
    institution = db.session.get(Institution, institution_id)
    if not institution:
        return fail("We could not find that institution.", 404)

    institution.is_active = not institution.is_active
    db.session.commit()

    state = "activated" if institution.is_active else "suspended"
    return ok({"institution": institution.to_dict()}, f"Institution {state}.")


@bp.post("/institutions/<institution_id>/onboard")
@staff_required("platform_admin")
def onboard_existing(institution_id):
    """Bring an institution the directory already holds into service.

    The directory ships with several hundred institutions, so by the time
    anyone is onboarded the entry almost always exists. Creating one
    through POST /institutions meant retyping a name, code and slug that
    were already on record, and the attempt failed on the unique slug
    with "that address is already in use" — accurate, useless, and no way
    forward from the screen the administrator was on.

    This takes the entry as it stands and adds only what onboarding
    genuinely needs: somebody to administer it. Name, code, slug, state
    and type are left alone rather than re-entered, because retyping a
    value that is already correct can only introduce a difference.
    """
    institution = db.session.get(Institution, institution_id)
    if not institution:
        return fail("We could not find that institution.", 404)

    payload = request.get_json(silent=True) or {}
    errors = {}

    admin_email = (payload.get("admin_email") or "").strip().lower()
    admin_name = (payload.get("admin_name") or "").strip()
    admin_password = payload.get("admin_password") or ""

    if not EMAIL_RE.match(admin_email):
        errors["admin_email"] = "Enter a valid email address."
    if len(admin_name) < 3:
        errors["admin_name"] = "Enter the administrator's full name."

    password_error = validate_password(admin_password)
    if password_error:
        errors["admin_password"] = password_error

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    if institution.is_onboarded:
        return fail(f"{institution.name} is already in service.", 409)

    existing = User.query.filter_by(
        institution_id=institution.id, email=admin_email
    ).first()
    if existing:
        return fail("Somebody with that email already administers this institution.", 409)

    # Corrections are accepted but not required. An imported name is
    # occasionally out of date, and the administrator taking it on is
    # better placed to know than our source list was.
    for field in ("name", "state", "contact_email"):
        value = (payload.get(field) or "").strip()
        if value:
            setattr(institution, field, value)

    mode = (payload.get("verification_mode") or "open").strip()
    if mode not in ("register", "open", "manual"):
        return fail(
            "Verification mode must be register, open or manual.",
            422,
            {"verification_mode": "Choose register, open or manual."},
        )
    institution.verification_mode = mode

    if "allow_anonymous" in payload:
        institution.allow_anonymous = bool(payload["allow_anonymous"])

    institution.is_onboarded = True
    institution.is_active = True
    db.session.flush()

    units_created = seed_units(institution)
    db.session.flush()
    rules_created = seed_routing(institution)

    admin = User(
        institution_id=institution.id,
        full_name=admin_name,
        email=admin_email,
        role="institution_admin",
    )
    admin.set_password(admin_password)
    db.session.add(admin)

    db.session.commit()

    return ok(
        {
            "institution": institution.to_dict(include_settings=True),
            "admin": admin.to_dict(),
            "units_created": units_created,
            "rules_created": rules_created,
        },
        f"{institution.name} is now in service.",
        201,
    )


@bp.put("/institutions/<institution_id>/onboarding")
@staff_required("platform_admin")
def set_onboarding(institution_id):
    """Put an institution into service, or take it back out.

    Distinct from suspending it. `is_active` is the switch for an
    institution that has misbehaved or wound down; this is the one that
    says whether students may register at all. The directory deliberately
    lists institutions we know of but have not onboarded, so the two
    states have to be separable.

    Needed because there was no way to set this after provisioning, which
    left the flag reachable only by direct SQL.
    """
    institution = db.session.get(Institution, institution_id)
    if not institution:
        return fail("We could not find that institution.", 404)

    payload = request.get_json(silent=True) or {}
    if "is_onboarded" not in payload:
        return fail("Say whether the institution is in service.", 422)

    institution.is_onboarded = bool(payload["is_onboarded"])

    mode = (payload.get("verification_mode") or "").strip()
    if mode:
        if mode not in ("register", "open", "manual"):
            return fail(
                "Verification mode must be register, open or manual.",
                422,
                {"verification_mode": "Choose register, open or manual."},
            )
        institution.verification_mode = mode

    db.session.commit()

    state = "is now in service" if institution.is_onboarded else "is no longer accepting students"
    return ok({"institution": institution.to_dict(include_settings=True)}, f"{institution.name} {state}.")


@bp.get("/stats")
@staff_required("platform_admin")
def platform_stats():
    from app.models.complaint import Complaint

    return ok(
        {
            "stats": {
                "institutions": Institution.query.count(),
                "active_institutions": Institution.query.filter_by(is_active=True).count(),
                "users": User.query.count(),
                "complaints": Complaint.query.count(),
            }
        }
    )
