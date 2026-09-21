"""Email verification, and deciding whether a registration stands.

Two separate questions, deliberately kept apart:

  Is this address yours?      answered by a link sent to it
  Are you a student here?     answered by the institution's register,
                              or by an administrator, or not at all

An institution that has uploaded its register can answer the second
automatically. One that has not still needs the first, because an
unverified address is the weaker problem but it is still a problem.
"""

from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models.base import as_aware, utcnow
from app.models.verification import EmailVerification
from app.services.delivery import queue_email

# A person who did not receive the first email will press the button
# again immediately. Anything shorter than this is a way to have us send
# mail on demand to an arbitrary address.
RESEND_INTERVAL = timedelta(minutes=2)

MAX_SENDS = 5


def send_verification(user, institution=None) -> EmailVerification | None:
    """Issue a token and queue the email.

    Any earlier unused token is retired, so a forwarded old message
    cannot be replayed once a newer one exists.
    """
    EmailVerification.query.filter_by(user_id=user.id, used_at=None).update(
        {EmailVerification.used_at: utcnow()}, synchronize_session=False
    )

    record, raw = EmailVerification.issue(user)

    base = (current_app.config.get("APP_URL") or "").rstrip("/")
    link = f"{base}/verify-email?token={raw}"
    where = f" at {institution.name}" if institution else ""

    queue_email(
        user.institution_id,
        user.email,
        "Confirm your email address",
        (
            f"Hello {user.full_name},\n\n"
            f"Confirm this address to finish setting up your Resolve account{where}.\n\n"
            f"{link}\n\n"
            "The link works for three days. If you did not create an account, "
            "ignore this message and nothing further will happen."
        ),
        user_id=user.id,
    )

    return record


def resend_verification(user, institution=None) -> tuple[bool, str]:
    """Send the link again, within limits.

    Returns (sent, message). The message is shown to the person, so it
    never distinguishes an unknown address from a known one.
    """
    if user.is_verified:
        return False, "That address is already confirmed. You can sign in."

    recent = (
        EmailVerification.query.filter_by(user_id=user.id)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if recent:
        last = as_aware(recent.last_sent_at or recent.created_at)
        if last and utcnow() - last < RESEND_INTERVAL:
            return False, "We sent one a moment ago. Check your inbox, and the spam folder."
        if (recent.sent_count or 0) >= MAX_SENDS:
            return False, (
                "We have sent several already. Check your spam folder, or contact "
                "your institution if none have arrived."
            )

    record = send_verification(user, institution)
    if recent and record:
        record.sent_count = (recent.sent_count or 1) + 1

    db.session.commit()
    return True, "A new link is on its way."


def verify_token(raw_token: str):
    """Consume a token. Returns (user, error message)."""
    from app.models.user import User
    from app.models.verification import hash_token

    record = EmailVerification.query.filter_by(token_hash=hash_token(raw_token)).first()

    if not record or not record.is_usable:
        return None, "That link has expired or has already been used. Ask for a new one."

    user = db.session.get(User, record.user_id)
    if not user or not user.is_active:
        return None, "That account is no longer active."

    # The address may have been changed after the token was issued.
    # Confirming the old one would prove nothing about the new.
    if record.email != user.email:
        return None, "That link was for a different address. Ask for a new one."

    if user.is_verified:
        record.consume()
        db.session.commit()
        return user, None

    user.email_verified_at = utcnow()
    record.consume()
    db.session.commit()

    return user, None


def decide_registration(institution, user, record=None) -> str:
    """Work out whether a new account is approved, or needs a person.

    The institution's verification mode decides:

      register  matched against the uploaded register. A match is
                approved outright and inherits faculty, department and
                level; no match waits for an administrator rather than
                being refused, because registers are never complete and
                a genuine student should not be turned away by a
                spreadsheet that is a week out of date.
      manual    every registration is reviewed.
      open      anybody with a confirmed address, which is what an
                institution without a usable register has to fall back on.
    """
    mode = institution.verification_mode or "register"

    if mode == "open":
        return "approved"

    if mode == "manual":
        return "pending"

    if record and record.can_register:
        record.claim(user)
        user.faculty_id = record.faculty_id
        if record.faculty:
            user.faculty = record.faculty.name
        if record.academic_department:
            user.department_name = record.academic_department.name
        return "approved"

    return "pending"
