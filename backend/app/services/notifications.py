"""Notification and audit helpers.

Now uses per-institution email templating – not hardcoded – with variables
ticket, deadline, officer, etc. Falls back to simple queue if templating
unavailable.
"""

from app.extensions import db
from app.models.complaint import ComplaintEvent, Notification

# Types worth interrupting someone by email. Routine acknowledgements stay
# in the application so people are not trained to ignore the messages.
EMAIL_WORTHY = {"escalation", "response", "resolved", "declined", "assignment", "status_change"}

# Map internal notification type to email template event
TYPE_TO_EVENT = {
    "escalation": "complaint_escalation",
    "response": "response",
    "resolved": "complaint_resolved",
    "declined": "complaint_declined",
    "assignment": "assignment",
    "status_change": "response",
    "acknowledged": "complaint_acknowledged",
    "in_progress": "complaint_in_progress",
    "awaiting_student": "complaint_awaiting_student",
    "closed": "complaint_closed",
}


def notify(user_id: str, institution_id: str, title: str, message: str,
           complaint_id: str | None = None, type_: str = "status_change",
           email: bool | None = None,
           template_vars: dict | None = None) -> Notification:
    """Create a notification and optionally queue an email.

    template_vars – extra variables for templated email (ticket, deadline,
    officer_name, etc.). If not provided, a simple email is sent.
    """
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
        from app.models.institution import Institution
        from app.models.user import User
        from app.services.delivery import queue_email

        recipient = db.session.get(User, user_id)
        institution = db.session.get(Institution, institution_id) if institution_id else None

        if recipient and recipient.email:
            # Try templated email if we have vars and institution
            if template_vars and institution:
                try:
                    from app.services.email_templating import queue_templated_email
                    event_type = TYPE_TO_EVENT.get(type_, "response")
                    # Merge title/message into vars for fallback
                    merged = dict(template_vars)
                    merged.setdefault("message", message)
                    merged.setdefault("recipient_name", recipient.full_name)
                    merged.setdefault("student_name", recipient.full_name)
                    queue_templated_email(
                        institution,
                        recipient.email,
                        event_type,
                        merged,
                        user_id=user_id,
                        complaint_id=complaint_id,
                    )
                    return notification
                except Exception:
                    pass  # fallback to simple

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
