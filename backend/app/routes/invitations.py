"""Staff invitations, individually and in bulk."""

import csv
import io

from flask import Blueprint, current_app, g, request

from app.extensions import db, limiter
from app.models.academic import Faculty
from app.models.institution import Department, Institution
from app.models.base import utcnow
from app.models.invitation import Invitation, hash_token
from app.models.user import INVITABLE_ROLES, ROLE_RANK, User
from app.routes.auth import EMAIL_RE, fail, ok, validate_password
from app.security import auth_required, staff_required, tenant_query
from app.services.delivery import queue_email

bp = Blueprint("invitations", __name__, url_prefix="/api/invitations")

MAX_BULK_ROWS = 500


def _can_grant(actor, role: str) -> bool:
    """Nobody may invite someone with more authority than their own."""
    return ROLE_RANK.get(role, 99) <= ROLE_RANK.get(actor.role, -1)


def _send(invitation: Invitation, raw_token: str, institution: Institution) -> None:
    base = (current_app.config.get("APP_URL") or "").rstrip("/")
    link = f"{base}/accept-invitation?token={raw_token}"
    role_label = invitation.role.replace("_", " ")

    queue_email(
        institution.id,
        invitation.email,
        f"You have been invited to {institution.name}",
        (
            f"Hello{' ' + invitation.full_name if invitation.full_name else ''},\n\n"
            f"You have been invited to handle student complaints at {institution.name} "
            f"as {role_label}.\n\n"
            f"Set your password using the link below. It expires in 14 days.\n\n"
            f"{link}\n\n"
            "If you were not expecting this, you can ignore the message."
        ),
        complaint_id=None,
    )


def _resolve_scope(actor, role: str, department_id, faculty_id):
    """Check the unit or faculty belongs to the caller's institution."""
    department = faculty = None

    if department_id:
        department = tenant_query(Department).filter(Department.id == department_id).first()
        if not department:
            return None, None, "We could not find that unit."

    if faculty_id:
        faculty = tenant_query(Faculty).filter(Faculty.id == faculty_id).first()
        if not faculty:
            return None, None, "We could not find that faculty."

    if role == "dean" and not faculty:
        return None, None, "Choose the faculty this dean is responsible for."
    if role in ("officer", "dept_head") and not department:
        return None, None, "Choose the unit this person will work in."

    # A unit head may only invite into their own unit.
    if actor.role == "dept_head" and department and department.id != actor.department_id:
        return None, None, "You can only invite people into your own unit."

    return department, faculty, None


@bp.post("")
@staff_required("dept_head")
@limiter.limit("60 per hour")
def create_invitation():
    actor = g.current_user
    payload = request.get_json(silent=True) or {}

    email = (payload.get("email") or "").strip().lower()
    role = (payload.get("role") or "officer").strip()
    errors = {}

    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if role not in INVITABLE_ROLES:
        errors["role"] = "Choose a valid role."
    elif not _can_grant(actor, role):
        errors["role"] = "You cannot invite someone with more access than your own."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    if tenant_query(User).filter(User.email == email).first():
        return fail("Someone with that email already has an account here.", 409)

    pending = tenant_query(Invitation).filter(
        Invitation.email == email, Invitation.status == "pending"
    ).first()
    if pending and pending.is_usable:
        return fail("That person already has an invitation waiting.", 409)

    department, faculty, problem = _resolve_scope(
        actor, role, payload.get("department_id"), payload.get("faculty_id")
    )
    if problem:
        return fail(problem, 422)

    institution = db.session.get(Institution, actor.institution_id)
    invitation, raw = Invitation.issue(
        institution,
        email=email,
        role=role,
        invited_by=actor,
        full_name=payload.get("full_name"),
        department_id=department.id if department else None,
        faculty_id=faculty.id if faculty else None,
    )
    db.session.flush()
    _send(invitation, raw, institution)
    db.session.commit()

    return ok({"invitation": invitation.to_dict()}, "Invitation sent.", 201)


@bp.post("/bulk")
@staff_required("institution_admin")
@limiter.limit("10 per hour")
def bulk_invite():
    """Invite many people from a spreadsheet.

    An institution has hundreds of staff. Adding them one at a time is
    not a product, and typing each password was never acceptable.
    """
    actor = g.current_user
    upload = request.files.get("file")
    if not upload:
        return fail("Choose a file to upload.", 422, {"file": "Choose a file to upload."})

    dry_run = (request.form.get("dry_run") or "").lower() in ("1", "true", "yes")

    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return fail("We could not read that file. Save it as CSV and try again.", 422)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return fail("That file appears to be empty.", 422)

    headers = {(h or "").strip().lower().replace(" ", "_") for h in reader.fieldnames}
    if "email" not in headers:
        return fail("The file needs an email column.", 422)

    institution = db.session.get(Institution, actor.institution_id)
    units = {d.slug: d for d in tenant_query(Department).all()}
    units.update({d.name.strip().lower(): d for d in tenant_query(Department).all()})
    faculties = {f.name.strip().lower(): f for f in tenant_query(Faculty).all()}

    existing = {u.email for u in tenant_query(User).all()}
    pending = {
        i.email
        for i in tenant_query(Invitation).filter(Invitation.status == "pending").all()
    }

    summary = {"invited": 0, "skipped": 0, "problems": [], "dry_run": dry_run}
    queued: list[tuple[Invitation, str]] = []

    for number, raw_row in enumerate(reader, start=2):
        row = {
            (k or "").strip().lower().replace(" ", "_"): (v or "").strip()
            for k, v in raw_row.items()
        }

        email = row.get("email", "").lower()
        role = (row.get("role") or "officer").lower().replace(" ", "_")

        if not EMAIL_RE.match(email):
            summary["problems"].append(f"Row {number}: '{email}' is not a valid email.")
            summary["skipped"] += 1
            continue

        if email in existing or email in pending:
            summary["problems"].append(f"Row {number}: {email} already has an account or invitation.")
            summary["skipped"] += 1
            continue

        if role not in INVITABLE_ROLES:
            summary["problems"].append(f"Row {number}: '{role}' is not a role that can be invited.")
            summary["skipped"] += 1
            continue

        if not _can_grant(actor, role):
            summary["problems"].append(
                f"Row {number}: you cannot invite a {role.replace('_', ' ')}."
            )
            summary["skipped"] += 1
            continue

        unit_name = (row.get("unit") or row.get("department") or "").strip().lower()
        department = units.get(unit_name) if unit_name else None
        if unit_name and not department:
            summary["problems"].append(f"Row {number}: no unit named '{unit_name}'.")
            summary["skipped"] += 1
            continue

        faculty_name = (row.get("faculty") or "").strip().lower()
        faculty = faculties.get(faculty_name) if faculty_name else None
        if faculty_name and not faculty:
            summary["problems"].append(f"Row {number}: no faculty named '{faculty_name}'.")
            summary["skipped"] += 1
            continue

        if role == "dean" and not faculty:
            summary["problems"].append(f"Row {number}: a dean needs a faculty.")
            summary["skipped"] += 1
            continue
        if role in ("officer", "dept_head") and not department:
            summary["problems"].append(f"Row {number}: {email} needs a unit.")
            summary["skipped"] += 1
            continue

        if not dry_run:
            invitation, token = Invitation.issue(
                institution,
                email=email,
                role=role,
                invited_by=actor,
                full_name=row.get("full_name") or row.get("name"),
                department_id=department.id if department else None,
                faculty_id=faculty.id if faculty else None,
            )
            queued.append((invitation, token))

        # Recorded even on a dry run, so a duplicate inside the file is
        # reported rather than silently invited twice.
        pending.add(email)
        summary["invited"] += 1

        if summary["invited"] >= MAX_BULK_ROWS:
            summary["problems"].append(
                f"Stopped at {MAX_BULK_ROWS} invitations. Split the file and upload again."
            )
            break

    if not dry_run and queued:
        db.session.flush()
        for invitation, token in queued:
            _send(invitation, token, institution)
        db.session.commit()

    summary["problems"] = summary["problems"][:50]
    return ok({"summary": summary}, "Invitations prepared." if dry_run else "Invitations sent.")


@bp.get("")
@staff_required("dept_head")
def list_invitations():
    query = tenant_query(Invitation)

    status = request.args.get("status")
    if status:
        query = query.filter(Invitation.status == status)

    # A unit head sees only their own unit's invitations.
    actor = g.current_user
    if actor.role == "dept_head":
        query = query.filter(Invitation.department_id == actor.department_id)

    rows = query.order_by(Invitation.created_at.desc()).limit(200).all()
    return ok({"invitations": [i.to_dict() for i in rows]})


@bp.post("/<invitation_id>/resend")
@staff_required("dept_head")
@limiter.limit("30 per hour")
def resend(invitation_id):
    """Send the invitation again.

    A new token is issued rather than resending the old one, so a message
    forwarded to the wrong person stops working.
    """
    actor = g.current_user
    invitation = tenant_query(Invitation).filter(Invitation.id == invitation_id).first()

    if not invitation:
        return fail("We could not find that invitation.", 404)
    if invitation.status != "pending":
        return fail("That invitation has already been used or withdrawn.", 409)
    if actor.role == "dept_head" and invitation.department_id != actor.department_id:
        return fail("That invitation belongs to another unit.", 403)

    import secrets

    from app.models.base import utcnow
    from app.models.invitation import TOKEN_BYTES, TOKEN_LIFETIME

    raw = secrets.token_urlsafe(TOKEN_BYTES)
    invitation.token_hash = hash_token(raw)
    invitation.expires_at = utcnow() + TOKEN_LIFETIME
    invitation.sent_count += 1
    invitation.last_sent_at = utcnow()

    institution = db.session.get(Institution, invitation.institution_id)
    _send(invitation, raw, institution)
    db.session.commit()

    return ok({"invitation": invitation.to_dict()}, "Invitation sent again.")


@bp.delete("/<invitation_id>")
@staff_required("dept_head")
def revoke(invitation_id):
    actor = g.current_user
    invitation = tenant_query(Invitation).filter(Invitation.id == invitation_id).first()

    if not invitation:
        return fail("We could not find that invitation.", 404)
    if invitation.status == "accepted":
        return fail("That person has already joined. Deactivate the account instead.", 409)
    if actor.role == "dept_head" and invitation.department_id != actor.department_id:
        return fail("That invitation belongs to another unit.", 403)

    invitation.revoke()
    db.session.commit()
    return ok(message="Invitation withdrawn.")


# Accepting is public: the recipient has no account yet. The token is the
# only credential, which is why it is single use and expires.
public_bp = Blueprint("invitation_public", __name__, url_prefix="/api/invitations")


@public_bp.get("/preview")
@limiter.limit("30 per hour")
def preview():
    """Describe an invitation so the page can be rendered before accepting."""
    token = (request.args.get("token") or "").strip()
    invitation = Invitation.query.filter_by(token_hash=hash_token(token)).first()

    if not invitation or not invitation.is_usable:
        return fail("That invitation has expired or has already been used.", 404)

    institution = db.session.get(Institution, invitation.institution_id)
    return ok(
        {
            "email": invitation.email,
            "full_name": invitation.full_name,
            "role": invitation.role,
            "institution": institution.name if institution else None,
            "department": invitation.department.name if invitation.department else None,
            "faculty": invitation.faculty.name if invitation.faculty else None,
        }
    )


@public_bp.post("/accept")
@limiter.limit("10 per hour")
def accept():
    """Create the account from an invitation.

    The role, unit and institution all come from the invitation, never
    from the request, so a recipient cannot grant themselves more access
    than they were offered.
    """
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip()

    invitation = Invitation.query.filter_by(token_hash=hash_token(token)).first()
    if not invitation or not invitation.is_usable:
        return fail("That invitation has expired or has already been used.", 400)

    error = validate_password(password)
    if error:
        return fail(error, 422, {"password": error})

    name = full_name or invitation.full_name
    if not name or len(name) < 3:
        return fail("Enter your full name.", 422, {"full_name": "Enter your full name."})

    # Guards the window between issuing and accepting, during which the
    # person may have been added another way.
    if User.query.filter_by(
        institution_id=invitation.institution_id, email=invitation.email
    ).first():
        invitation.revoke()
        db.session.commit()
        return fail("An account with that email already exists. Try signing in.", 409)

    user = User(
        institution_id=invitation.institution_id,
        department_id=invitation.department_id,
        faculty_id=invitation.faculty_id,
        full_name=name[:150],
        email=invitation.email,
        role=invitation.role,
        # Accepting an invitation proves the address: the link only ever
        # went there. Sending a second email to confirm what has just
        # been demonstrated would be theatre.
        email_verified_at=utcnow(),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    invitation.accept(user)
    db.session.commit()

    return ok({"user": user.to_dict()}, "Your account is ready. You can sign in now.", 201)
