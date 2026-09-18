"""Notification and audit helpers."""

from app.extensions import db
from app.models.complaint import ComplaintEvent, Notification

# Types worth interrupting someone by email. Routine acknowledgements stay
# in the application so people are not trained to ignore the messages.
EMAIL_WORTHY = {"escalation", "response", "resolved", "declined", "assignment"}


def notify(user_id: str, institution_id: str, title: str, message: str,
           complaint_id: str | None = None, type_: str = "status_change",
           email: bool | None = None) -> Notification:
    notification = Notification(
        user_id=user_id,
        institution_id=institution_id,
        complaint_id=complaint_id,
        title=title,
        message=message,
        type=type_,
    )
    db.session.add(notification)

    should_email = EMAIL_WORTHY.__contains__(type_) if email is None else email
    if should_email:
        from app.models.user import User
        from app.services.delivery import queue_email

        recipient = db.session.get(User, user_id)
        if recipient and recipient.email:
            queue_email(
                institution_id,
                recipient.email,
                title,
                f"{message}\n\nSign in to Resolve to read the full update.",
                user_id=user_id,
                complaint_id=complaint_id,
            )

    return notification


def record_event(complaint, actor_id: str | None, action: str,
                 from_value: str | None = None, to_value: str | None = None,
                 note: str | None = None) -> ComplaintEvent:
    """Append an immutable audit entry."""
    event = ComplaintEvent(
        complaint_id=complaint.id,
        institution_id=complaint.institution_id,
        actor_id=actor_id,
        action=action,
        from_value=from_value,
        to_value=to_value,
        note=note,
    )
    db.session.add(event)
    return event
