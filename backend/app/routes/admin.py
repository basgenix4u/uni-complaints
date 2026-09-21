"""Institution administration: users, departments and settings."""

import re

from flask import Blueprint, current_app, g, request

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

    approval = request.args.get("approval")
    if approval:
        query = query.filter(User.approval_status == approval)

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


# -- registrations awaiting review ------------------------------------


@bp.get("/registrations")
@staff_required("institution_admin")
def pending_registrations():
    """Students waiting to be confirmed as students.

    These are people the register could not vouch for, or everyone, at an
    institution that reviews each registration by hand. Each one is
    somebody locked out until a person looks, so the list carries what is
    needed to decide rather than making the administrator go and find it.
    """
    from app.models.academic import StudentRecord
    from app.services.register import normalise_matric

    # Anyone who cannot yet file, for either reason. Listing only the
    # ones awaiting approval would hide the students stuck behind an
    # unconfirmed address, which is exactly the group that needs help
    # when email is not working.
    rows = (
        tenant_query(User)
        .filter(
            User.role == "student",
            db.or_(
                User.approval_status == "pending",
                User.email_verified_at.is_(None),
            ),
        )
        .order_by(User.created_at)
        .limit(500)
        .all()
    )

    payload = []
    for person in rows:
        entry = person.to_dict()

        # Someone who has simply not opened the link is not a
        # registration to judge; they need the address confirming, which
        # is a different action.
        if person.approval_status == "approved" and not person.is_verified:
            entry["reason"] = "Waiting on them to confirm their email address."
            entry["awaiting_email_only"] = True
            payload.append(entry)
            continue

        # Why the automatic check did not settle it, so the administrator
        # is not left guessing.
        if not person.matric_number:
            entry["reason"] = "No matric number given."
        else:
            match = StudentRecord.query.filter_by(
                institution_id=person.institution_id,
                matric_number=normalise_matric(person.matric_number),
            ).first()
            if match is None:
                entry["reason"] = "Not found in the student register."
            elif match.claimed_by_user_id and match.claimed_by_user_id != person.id:
                entry["reason"] = "That register entry is already claimed."
            elif match.status != "active":
                entry["reason"] = f"The register lists them as {match.status}."
            else:
                entry["reason"] = "Your institution reviews every registration."
            entry["register_match"] = match.to_dict() if match else None

        payload.append(entry)

    return ok({"registrations": payload, "count": len(payload)})


@bp.get("/delivery-health")
@staff_required("institution_admin")
def delivery_health():
    """Whether outbound email is actually working.

    Verification depends entirely on email, so an institution that
    cannot send any is one where nobody can finish registering. Without
    this the first sign of that is students reporting they are stuck,
    which is far too late.
    """
    from app.models.message import OutboundMessage

    configured = bool(current_app.config.get("SMTP_HOST"))
    console = bool(current_app.config.get("MAIL_TO_CONSOLE"))

    base = OutboundMessage.query.filter_by(
        institution_id=g.institution_id, channel="email"
    )
    waiting = base.filter_by(status="pending").count()
    failed = base.filter_by(status="failed").count()

    if configured:
        state, advice = "ok", None
    elif console:
        state, advice = "console", (
            "Email is being written to the application log instead of sent. Fine for "
            "testing; configure SMTP_HOST before real students use this."
        )
    else:
        state, advice = "not_configured", (
            "No email provider is set up, so confirmation links cannot reach anyone. "
            "Messages are held rather than discarded and will send once SMTP_HOST is "
            "configured. Until then, confirm registrations by hand."
        )

    return ok(
        {
            "email": {
                "state": state,
                "advice": advice,
                "queued": waiting,
                "failed": failed,
                "sms_configured": bool(current_app.config.get("SMS_PROVIDER")),
            }
        }
    )


@bp.put("/registrations/<user_id>/confirm-email")
@staff_required("institution_admin")
def confirm_email_manually(user_id):
    """Mark an address confirmed without the emailed link.

    The escape hatch for the case where email itself is the problem: a
    deployment with no SMTP provider yet, a link that never arrived, or a
    student whose address bounces. Without this, verification is a door
    with no key and the institution cannot let anybody in.

    Deliberately restricted to an administrator and written to the audit
    trail, because it is an assertion that somebody checked by other
    means rather than proof the address works.
    """
    person = tenant_query(User).filter_by(id=user_id).first()
    if not person:
        return fail("We could not find that person.", 404)

    if person.is_verified:
        return ok({"user": person.to_dict()}, "That address was already confirmed.")

    import structlog

    from app.models.base import utcnow
    from app.models.verification import EmailVerification

    person.email_verified_at = utcnow()
    person.email_verified_by_id = g.current_user.id

    # Outstanding links are retired: the address is settled, and leaving
    # a live token behind serves no purpose.
    EmailVerification.query.filter_by(user_id=person.id, used_at=None).update(
        {EmailVerification.used_at: utcnow()}, synchronize_session=False
    )
    db.session.commit()

    structlog.get_logger().info(
        "email_confirmed_manually",
        actor_id=g.current_user.id,
        subject_id=person.id,
        institution_id=person.institution_id,
    )

    return ok({"user": person.to_dict()}, "Address confirmed.")


@bp.put("/registrations/<user_id>")
@staff_required("institution_admin")
def decide_registration_route(user_id):
    """Approve or reject a registration.

    Approving links the account to its register entry where there is one,
    so the student inherits their faculty and department rather than
    keeping whatever they typed.
    """
    person = tenant_query(User).filter_by(id=user_id).first()
    if not person or person.role != "student":
        return fail("We could not find that registration.", 404)

    decision = ((request.get_json(silent=True) or {}).get("decision") or "").strip()
    if decision not in ("approved", "rejected"):
        return fail("Choose whether to approve or reject.", 422)

    from app.models.academic import StudentRecord
    from app.services.delivery import queue_email
    from app.services.register import normalise_matric

    person.approval_status = decision

    if decision == "approved" and person.matric_number:
        match = StudentRecord.query.filter_by(
            institution_id=person.institution_id,
            matric_number=normalise_matric(person.matric_number),
        ).first()
        if match and match.can_register:
            match.claim(person)
            person.faculty_id = match.faculty_id
            if match.academic_department:
                person.department_name = match.academic_department.name

    institution = db.session.get(Institution, person.institution_id)
    if decision == "approved":
        subject = "Your account has been approved"
        body = (
            f"Hello {person.full_name},\n\n"
            f"{institution.name if institution else 'Your institution'} has confirmed your "
            "registration. You can sign in and file a complaint now."
        )
    else:
        subject = "We could not confirm your registration"
        body = (
            f"Hello {person.full_name},\n\n"
            f"{institution.name if institution else 'Your institution'} could not confirm "
            "you are a student there. If you believe this is a mistake, contact the "
            "registry with your matric number."
        )

    queue_email(person.institution_id, person.email, subject, body, user_id=person.id)
    db.session.commit()

    return ok({"user": person.to_dict()}, f"Registration {decision}.")


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
