"""Institution administration: users, departments and settings."""

import re

from flask import Blueprint, g, request

from app.extensions import db
from app.models.institution import Department, Institution
from app.models.user import ROLE_RANK, STAFF_ROLES, User, normalise_phone
from app.routes.auth import EMAIL_RE, fail, ok, validate_password
from app.security import auth_required, staff_required, tenant_query

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    return SLUG_RE.sub("-", (value or "").strip().lower()).strip("-")


# -- users ------------------------------------------------------------


@bp.get("/users")
@staff_required("institution_admin")
def list_users():
    query = tenant_query(User)

    role = request.args.get("role")
    if role:
        query = query.filter(User.role == role)

    if request.args.get("staff") in ("1", "true"):
        query = query.filter(User.role.in_(STAFF_ROLES))

    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.matric_number.ilike(like),
            )
        )

    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 50)
    result = query.order_by(User.created_at.desc()).paginate(
        page=max(request.args.get("page", 1, type=int), 1), per_page=per_page, error_out=False
    )

    return ok(
        {
            "users": [u.to_dict() for u in result.items],
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


@bp.get("/users/<user_id>")
@staff_required("institution_admin")
def get_user(user_id):
    user = tenant_query(User).filter(User.id == user_id).first()
    if not user:
        return fail("We could not find that user.", 404)
    return ok({"user": user.to_dict()})


@bp.post("/staff")
@staff_required("institution_admin")
def create_staff():
    """Create a member of staff within the caller's institution."""
    actor = g.current_user
    payload = request.get_json(silent=True) or {}
    errors = {}

    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "officer").strip()

    if len(full_name) < 3:
        errors["full_name"] = "Enter their full name."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."

    password_error = validate_password(password)
    if password_error:
        errors["password"] = password_error

    if role not in STAFF_ROLES:
        errors["role"] = "Choose a valid staff role."
    # Nobody may create an account with more authority than their own.
    elif ROLE_RANK[role] > ROLE_RANK[actor.role]:
        errors["role"] = "You cannot create an account with more access than your own."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    if tenant_query(User).filter(User.email == email).first():
        return fail("Someone with that email already exists here.", 409)

    department = None
    if payload.get("department_id"):
        department = tenant_query(Department).filter(Department.id == payload["department_id"]).first()
        if not department:
            return fail("We could not find that department.", 422)

    member = User(
        institution_id=actor.institution_id,
        department_id=department.id if department else None,
        full_name=full_name,
        email=email,
        phone=normalise_phone(payload.get("phone")),
        role=role,
    )
    member.set_password(password)
    db.session.add(member)
    db.session.commit()

    return ok({"user": member.to_dict()}, "Staff account created.", 201)


@bp.put("/users/<user_id>/toggle-active")
@staff_required("institution_admin")
def toggle_active(user_id):
    actor = g.current_user
    user = tenant_query(User).filter(User.id == user_id).first()
    if not user:
        return fail("We could not find that user.", 404)

    if user.id == actor.id:
        return fail("You cannot deactivate your own account.", 409)
    if ROLE_RANK[user.role] > ROLE_RANK[actor.role]:
        return fail("You cannot change an account with more access than your own.", 403)

    user.is_active = not user.is_active
    db.session.commit()

    state = "activated" if user.is_active else "deactivated"
    return ok({"user": user.to_dict()}, f"Account {state}.")


@bp.put("/users/<user_id>/role")
@staff_required("institution_admin")
def change_role(user_id):
    actor = g.current_user
    user = tenant_query(User).filter(User.id == user_id).first()
    if not user:
        return fail("We could not find that user.", 404)

    role = (request.get_json(silent=True) or {}).get("role", "")
    if role not in ("student", *STAFF_ROLES):
        return fail("Choose a valid role.", 422)
    if ROLE_RANK[role] > ROLE_RANK[actor.role]:
        return fail("You cannot grant more access than your own.", 403)
    if user.id == actor.id:
        return fail("You cannot change your own role.", 409)

    user.role = role
    db.session.commit()
    return ok({"user": user.to_dict()}, "Role updated.")


# -- departments ------------------------------------------------------


@bp.get("/departments")
@auth_required()
def list_departments():
    rows = tenant_query(Department).order_by(Department.name).all()
    return ok({"departments": [d.to_dict() for d in rows]})


@bp.post("/departments")
@staff_required("institution_admin")
def create_department():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if len(name) < 2:
        return fail("Enter a department name.", 422, {"name": "Enter a department name."})

    slug = slugify(payload.get("slug") or name)
    if tenant_query(Department).filter(Department.slug == slug).first():
        return fail("A department with that name already exists.", 409)

    department = Department(
        institution_id=g.current_user.institution_id,
        name=name,
        slug=slug,
        description=(payload.get("description") or "").strip() or None,
        sla_hours=payload.get("sla_hours"),
    )
    db.session.add(department)
    db.session.commit()
    return ok({"department": department.to_dict()}, "Department created.", 201)


@bp.put("/departments/<department_id>")
@staff_required("institution_admin")
def update_department(department_id):
    department = tenant_query(Department).filter(Department.id == department_id).first()
    if not department:
        return fail("We could not find that department.", 404)

    payload = request.get_json(silent=True) or {}
    if "name" in payload:
        department.name = (payload["name"] or "").strip() or department.name
    if "description" in payload:
        department.description = (payload["description"] or "").strip() or None
    if "sla_hours" in payload:
        department.sla_hours = payload["sla_hours"]
    if "is_active" in payload:
        department.is_active = bool(payload["is_active"])

    db.session.commit()
    return ok({"department": department.to_dict()}, "Department updated.")


# -- institution settings ---------------------------------------------


@bp.get("/settings")
@staff_required("institution_admin")
def get_settings():
    institution = db.session.get(Institution, g.current_user.institution_id)
    if not institution:
        return fail("We could not find your institution.", 404)
    return ok({"institution": institution.to_dict(include_settings=True)})


@bp.put("/settings")
@staff_required("institution_admin")
def update_settings():
    institution = db.session.get(Institution, g.current_user.institution_id)
    if not institution:
        return fail("We could not find your institution.", 404)

    payload = request.get_json(silent=True) or {}

    for field in ("name", "state", "contact_email", "contact_phone", "logo_url"):
        if field in payload:
            setattr(institution, field, (payload[field] or "").strip() or None)

    for field in (
        "default_sla_hours",
        "acknowledge_sla_hours",
        "working_hours_start",
        "working_hours_end",
        "brand_hue",
    ):
        if field in payload and isinstance(payload[field], int):
            setattr(institution, field, payload[field])

    if "allow_anonymous" in payload:
        institution.allow_anonymous = bool(payload["allow_anonymous"])

    if institution.working_hours_start >= institution.working_hours_end:
        return fail("The working day must end after it starts.", 422)

    db.session.commit()
    return ok({"institution": institution.to_dict(include_settings=True)}, "Settings saved.")
