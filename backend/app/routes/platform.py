"""Platform administration: provisioning institutions.

Restricted to platform_admin, the only role that operates across tenants.
"""

import re

from flask import Blueprint, request

from app.extensions import db
from app.models.institution import Department, Institution
from app.models.user import User
from app.routes.auth import EMAIL_RE, fail, ok, validate_password

from app.security import staff_required

bp = Blueprint("platform", __name__, url_prefix="/api/platform")

CODE_RE = re.compile(r"^[A-Z]{2,8}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEFAULT_DEPARTMENTS = (
    ("Bursary", "bursary"),
    ("Registry", "registry"),
    ("Student Affairs", "student-affairs"),
    ("Works and Maintenance", "works"),
    ("Library", "library"),
    ("Security", "security"),
)


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
    )
    db.session.add(institution)
    db.session.flush()

    for department_name, department_slug in DEFAULT_DEPARTMENTS:
        db.session.add(
            Department(
                institution_id=institution.id, name=department_name, slug=department_slug
            )
        )

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
