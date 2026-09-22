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
    rows = Institution.query.order_by(Institution.created_at.desc()).all()
    payload = []
    for institution in rows:
        data = institution.to_dict(include_settings=True)
        data["user_count"] = User.query.filter_by(institution_id=institution.id).count()
        payload.append(data)
    return ok({"institutions": payload})


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

    if Institution.query.filter_by(code=code).first():
        return fail("That code is already in use.", 409)
    if Institution.query.filter_by(slug=slug).first():
        return fail("That address is already in use.", 409)

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
