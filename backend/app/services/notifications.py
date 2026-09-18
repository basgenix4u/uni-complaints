"""Notification and audit helpers."""

from app.extensions import db
from app.models.complaint import ComplaintEvent, Notification


def notify(user_id: str, institution_id: str, title: str, message: str,
           complaint_id: str | None = None, type_: str = "status_change") -> Notification:
    notification = Notification(
        user_id=user_id,
        institution_id=institution_id,
        complaint_id=complaint_id,
        title=title,
        message=message,
        type=type_,
    )
    db.session.add(notification)
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
