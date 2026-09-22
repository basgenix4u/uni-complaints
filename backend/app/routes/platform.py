"""Platform administration: provisioning institutions.

Restricted to platform_admin, the only role that operates across tenants.
"""

import re

from flask import Blueprint, request

from app.extensions import db
from app.models.institution import Institution
from app.models.user import User
from app.routes.auth import EMAIL_RE, fail, ok, validate_password

from app.security import staff_required
from app.services.routing import seed_routing, seed_units

bp = Blueprint("platform", __name__, url_prefix="/api/platform")

CODE_RE = re.compile(r"^[A-Z]{2,8}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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

    institution = Institution(
        name=name,
        code=code,
        slug=slug,
        type=(payload.get("type") or "university").strip(),
        state=(payload.get("state") or "").strip() or None,
        contact_email=(payload.get("contact_email") or "").strip() or None,
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
