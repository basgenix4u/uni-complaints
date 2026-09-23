"""Authentication endpoints."""

import re

from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required

from app.extensions import db, limiter
from app.models.base import utcnow
from app.models.institution import Institution
from app.models.reset import PasswordReset, hash_token
from app.models.user import User, normalise_matric, normalise_phone
from app.security import auth_required, load_current_user
from app.services.delivery import queue_email
from app.services.register import find_for_registration
from app.services.verification import (
    decide_registration,
    resend_verification,
    send_verification,
    verify_token,
)

try:
    from app.services.email_templating import queue_templated_email
except ImportError:
    queue_templated_email = None

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Fallback pattern when institution has no custom pattern. Still not hardcoded
# as the only rule – per-institution pattern takes precedence.
FALLBACK_MATRIC_RE = re.compile(r"^[A-Z]{2,5}/[A-Z]{2,5}/\d{2,4}/\d{3,6}$")


def _validate_matric_for_institution(matric: str, institution) -> str | None:
    """Validate matric against institution's pattern if present.

    Returns error message or None if valid.
    Matric format is not hardcoded: each institution defines its own.
    """
    if not matric:
        return None
    pattern_str = getattr(institution, "matric_pattern", None) if institution else None
    example = getattr(institution, "matric_example", None) if institution else None
    if pattern_str:
        try:
            pat = re.compile(pattern_str, re.IGNORECASE)
            if pat.match(matric):
                return None
            # Also try normalised? matric already normalised upper
            return f"Check the format, for example {example or 'ENG/COE/21/013'}."
        except re.error:
            # Invalid regex in DB – fall back
            pass
    # Fallback
    if FALLBACK_MATRIC_RE.match(matric):
        return None
    return f"Check the format, for example {example or 'ENG/COE/21/013'}."


def ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data or {}}), status


def fail(message, status=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def issue_tokens(user):
    claims = {"role": user.role, "institution_id": user.institution_id}
    return (
        create_access_token(identity=user.id, additional_claims=claims),
        create_refresh_token(identity=user.id, additional_claims=claims),
    )


def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Use at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Include at least one capital letter."
    if not re.search(r"[a-z]", password):
        return "Include at least one small letter."
    if not re.search(r"\d", password):
        return "Include at least one number."
    return None


@bp.post("/register")
@limiter.limit("5 per hour")
def register():
    payload = request.get_json(silent=True) or {}
    errors = {}

    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    institution_slug = (payload.get("institution") or "").strip().lower()
    matric = normalise_matric(payload.get("matric_number"))

    if len(full_name) < 3:
        errors["full_name"] = "Enter your full name."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."

    password_error = validate_password(password)
    if password_error:
        errors["password"] = password_error

    institution = Institution.query.filter_by(slug=institution_slug, is_active=True).first()
    if not institution:
        errors["institution"] = "We could not find that institution."
    elif not institution.is_onboarded:
        # A student from a university that has not signed up cannot be
        # given an account: there would be nobody on the other end to
        # answer them. Their interest is worth recording instead.
        return fail(
            f"{institution.name} is not using Resolve yet. Ask us to invite them, "
            "and we will tell you when they are.",
            409,
            {"institution": "Not using Resolve yet.", "can_register_interest": True},
        )

    # A matriculation number is only demanded where it will actually be
    # checked. Requiring one an institution cannot verify is an obstacle
    # that proves nothing.
    needs_matric = bool(institution and institution.verification_mode == "register")
    if needs_matric and not matric:
        errors["matric_number"] = "Enter your matric number so we can check the student register."
    if matric:
        matric_error = _validate_matric_for_institution(matric, institution)
        if matric_error:
            errors["matric_number"] = matric_error

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    if User.query.filter_by(institution_id=institution.id, email=email).first():
        return fail("An account with that email already exists. Try signing in instead.", 409)

    if matric and User.query.filter_by(institution_id=institution.id, matric_number=matric).first():
        return fail("That matric number is already registered.", 409)

    record = find_for_registration(institution, matric) if matric else None
    if record and record.claimed_by_user_id:
        # Somebody has already registered against this entry. Refused
        # rather than queued, because one of the two is not who they say
        # they are and an administrator cannot tell which from a form.
        return fail(
            "That matric number is already registered. If this is yours, contact your "
            "institution.",
            409,
        )

    user = User(
        institution_id=institution.id,
        full_name=full_name,
        email=email,
        matric_number=matric,
        faculty=(payload.get("faculty") or "").strip() or None,
        department_name=(payload.get("department") or "").strip() or None,
        phone=normalise_phone(payload.get("phone")),
        role="student",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    user.approval_status = decide_registration(institution, user, record)
    send_verification(user, institution)
    db.session.commit()

    if user.approval_status == "pending":
        message = (
            "Account created. Confirm your email, and your institution will check your "
            "registration before you can file a complaint."
        )
    else:
        message = "Account created. Confirm your email to start filing complaints."

    access, refresh = issue_tokens(user)
    return ok(
        {
            "user": user.to_dict(),
            "institution": institution.to_dict(),
            "access_token": access,
            "refresh_token": refresh,
            "verification_required": True,
        },
        message,
        201,
    )


@bp.post("/login")
@limiter.limit("10 per 15 minutes")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    institution_slug = (payload.get("institution") or "").strip().lower()

    query = User.query.filter_by(email=email)
    if institution_slug:
        institution = Institution.query.filter_by(slug=institution_slug).first()
        if not institution:
            return fail("That email and password do not match.", 401)
        query = query.filter_by(institution_id=institution.id)

    user = query.first()

    # The same message is returned whether the account exists or the password
    # is wrong, so the endpoint cannot be used to enumerate accounts.
    if not user or not user.check_password(password):
        return fail("That email and password do not match. Check for typos, or reset your password.", 401)

    if not user.is_active:
        return fail("This account has been deactivated. Contact your institution.", 403)

    user.record_login()
    db.session.commit()

    access, refresh = issue_tokens(user)
    return ok(
        {
            "user": user.to_dict(),
            "institution": user.institution.to_dict() if user.institution else None,
            "access_token": access,
            "refresh_token": refresh,
        },
        "Signed in.",
    )


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user = load_current_user()
    if not user:
        return fail("Your session has expired. Please sign in again.", 401)
    access, _ = issue_tokens(user)
    return ok({"access_token": access}, "Session refreshed.")


@bp.get("/me")
@auth_required()
def me():
    user = g.current_user
    return ok(
        {
            "user": user.to_dict(),
            "institution": user.institution.to_dict() if user.institution else None,
        }
    )


@bp.put("/profile")
@auth_required()
def update_profile():
    user = g.current_user
    payload = request.get_json(silent=True) or {}

    if "full_name" in payload:
        name = (payload["full_name"] or "").strip()
        if len(name) < 3:
            return fail("Enter your full name.", 422, {"full_name": "Enter your full name."})
        user.full_name = name

    if "phone" in payload:
        user.phone = normalise_phone(payload["phone"])
    if "faculty" in payload:
        user.faculty = (payload["faculty"] or "").strip() or None
    if "department" in payload:
        user.department_name = (payload["department"] or "").strip() or None

    db.session.commit()
    return ok({"user": user.to_dict()}, "Profile updated.")


@bp.post("/change-password")
@auth_required()
@limiter.limit("5 per hour")
def change_password():
    user = g.current_user
    payload = request.get_json(silent=True) or {}

    if not user.check_password(payload.get("current_password") or ""):
        return fail("Your current password is not correct.", 401)

    new_password = payload.get("new_password") or ""
    error = validate_password(new_password)
    if error:
        return fail(error, 422, {"new_password": error})

    user.set_password(new_password)
    db.session.commit()
    return ok(message="Password changed.")


@bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    """Start a password reset.

    Always reports success. Saying whether an address is registered would
    turn this into a way to discover who holds an account, which for a
    complaints system also reveals who has complained.
    """
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    confirmation = (
        "If that email belongs to an account, a reset link is on its way. "
        "It expires in an hour."
    )

    if not EMAIL_RE.match(email):
        return ok(message=confirmation)

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user:
        return ok(message=confirmation)

    # Any earlier unused token stops working, so a forwarded old email
    # cannot be replayed.
    PasswordReset.query.filter_by(user_id=user.id, used_at=None).update(
        {PasswordReset.used_at: utcnow()}, synchronize_session=False
    )

    _, raw_token = PasswordReset.issue(user, request.remote_addr)

    base = current_app.config.get("APP_URL", "").rstrip("/")
    link = f"{base}/reset-password?token={raw_token}"

    # Templated email – per-institution branding
    if queue_templated_email and user.institution:
        try:
            queue_templated_email(
                user.institution,
                user.email,
                "password_reset",
                {
                    "student_name": user.full_name,
                    "recipient_name": user.full_name,
                    "token": raw_token,
                    "link": link,
                    "app_url": base,
                },
                user_id=user.id,
            )
        except Exception:
            queue_email(
                user.institution_id,
                user.email,
                "Reset your password",
                (
                    f"Hello {user.full_name},\n\n"
                    f"Use the link below to choose a new password. It expires in an hour.\n\n"
                    f"{link}\n\n"
                    "If you did not ask for this, you can ignore this message and your "
                    "password stays as it is."
                ),
                user_id=user.id,
            )
    else:
        queue_email(
            user.institution_id,
            user.email,
            "Reset your password",
            (
                f"Hello {user.full_name},\n\n"
                f"Use the link below to choose a new password. It expires in an hour.\n\n"
                f"{link}\n\n"
                "If you did not ask for this, you can ignore this message and your "
                "password stays as it is."
            ),
            user_id=user.id,
        )
    db.session.commit()

    return ok(message=confirmation)


@bp.post("/reset-password")
@limiter.limit("10 per hour")
def reset_password():
    """Complete a password reset."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    new_password = payload.get("password") or ""

    error = validate_password(new_password)
    if error:
        return fail(error, 422, {"password": error})

    record = PasswordReset.query.filter_by(token_hash=hash_token(token)).first()
    if not record or not record.is_usable:
        return fail(
            "That reset link has expired or has already been used. Ask for a new one.", 400
        )

    user = db.session.get(User, record.user_id)
    if not user or not user.is_active:
        return fail("That account is no longer active.", 400)

    user.set_password(new_password)
    record.consume()

    # Other outstanding tokens are retired too, so a second email cannot be
    # used after the password has changed.
    PasswordReset.query.filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used_at.is_(None),
    ).update({PasswordReset.used_at: utcnow()}, synchronize_session=False)

    if queue_templated_email and user.institution:
        try:
            queue_templated_email(
                user.institution,
                user.email,
                "password_changed",
                {
                    "student_name": user.full_name,
                    "recipient_name": user.full_name,
                    "institution_name": user.institution.name if user.institution else "",
                },
                user_id=user.id,
            )
        except Exception:
            queue_email(
                user.institution_id,
                user.email,
                "Your password was changed",
                (
                    f"Hello {user.full_name},\n\n"
                    "Your password has just been changed. If this was not you, contact your "
                    "institution immediately."
                ),
                user_id=user.id,
            )
    else:
        queue_email(
            user.institution_id,
            user.email,
            "Your password was changed",
            (
                f"Hello {user.full_name},\n\n"
                "Your password has just been changed. If this was not you, contact your "
                "institution immediately."
            ),
            user_id=user.id,
        )
    db.session.commit()

    return ok(message="Your password has been changed. You can sign in with it now.")


@bp.post("/verify-email")
@limiter.limit("20 per hour")
def verify_email():
    """Confirm an address from the emailed link."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return fail("That link is incomplete. Use the one from the email.", 400)

    user, error = verify_token(token)
    if error:
        return fail(error, 400)

    if user.approval_status == "pending":
        return ok(
            {"user": user.to_dict(), "approval_status": "pending"},
            "Email confirmed. Your institution is now checking your registration.",
        )

    return ok(
        {"user": user.to_dict(), "approval_status": user.approval_status},
        "Email confirmed. You can file a complaint now.",
    )


@bp.post("/resend-verification")
@limiter.limit("5 per hour")
def resend_verification_email():
    """Send the confirmation link again.

    Answers the same way whether or not the address is on file, so it
    cannot be used to discover who holds an account.
    """
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()

    confirmation = (
        "If that address needs confirming, a new link is on its way. "
        "Check the spam folder too."
    )

    if not EMAIL_RE.match(email):
        return ok(message=confirmation)

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user:
        return ok(message=confirmation)

    sent, detail = resend_verification(user, user.institution)
    # A genuine rate limit is worth saying out loud: it tells the person
    # to wait rather than to keep pressing.
    return ok(message=detail if not sent else confirmation)


@bp.get("/verification-status")
@auth_required()
def verification_status():
    """Where this account stands, for the banner in the interface."""
    user = g.current_user
    allowed, reason = user.can_file_complaints

    return ok(
        {
            "email": user.email,
            "is_verified": user.is_verified,
            "approval_status": user.approval_status,
            "can_file": allowed,
            "reason": reason,
        }
    )
