"""Data subject rights.

Implements the rights the Nigeria Data Protection Act 2023 gives a person
over their own data: access and portability under section 39, erasure
under section 37, and storage limitation under section 24.

The hard part is erasure. A complaint is not only personal data about the
student who filed it; it is also the institution's record of what was
reported, what was decided, and by whom. Deleting the row outright would
destroy a disciplinary record and break the audit trail that makes the
system trustworthy in the first place.

The approach taken here severs the link between the person and the record
rather than deleting the record. Identifying fields are overwritten, the
free text the person wrote is removed, and the complaint survives as an
anonymous row. That erases the personal data while leaving the institution
its own account of its decisions.
"""

from datetime import timedelta

from app.extensions import db
from app.models.attachment import Attachment
from app.models.base import as_aware, new_uuid, utcnow
from app.models.complaint import Complaint, ComplaintEvent, Notification, Response
from app.models.message import OutboundMessage
from app.models.reset import PasswordReset
from app.models.user import User
from app.services import storage


def export_user_data(user: User) -> dict:
    """Everything held about one person, in a portable form.

    Section 39 asks for a structured, commonly used, machine readable
    format. JSON satisfies that and stays readable by a person.
    """
    complaints = Complaint.query.filter_by(student_id=user.id).all()
    written = Response.query.filter_by(author_id=user.id).all()
    notifications = Notification.query.filter_by(user_id=user.id).all()
    attachments = Attachment.query.filter_by(uploaded_by_id=user.id).all()
    messages = OutboundMessage.query.filter_by(user_id=user.id).all()

    return {
        "exported_at": utcnow().isoformat(),
        "notice": (
            "This file contains the personal data held about you. Internal "
            "staff notes are the institution's own deliberation rather than "
            "personal data about you, and are not included."
        ),
        "account": {
            "full_name": user.full_name,
            "email": user.email,
            "matric_number": user.matric_number,
            "faculty": user.faculty,
            "department": user.department_name,
            "phone": user.phone,
            "role": user.role,
            "registered_at": user.created_at.isoformat() if user.created_at else None,
            "last_signed_in": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "institution": user.institution.name if user.institution else None,
        "complaints": [
            {
                "ticket_number": complaint.ticket_number,
                "title": complaint.title,
                "description": complaint.description,
                "category": complaint.category,
                "priority": complaint.priority,
                "status": complaint.status,
                "filed_at": complaint.created_at.isoformat() if complaint.created_at else None,
                "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
                "resolution_note": complaint.resolution_note,
                "decline_reason": complaint.decline_reason,
                "satisfaction_rating": complaint.satisfaction_rating,
                "messages": [
                    {
                        "message": reply.message,
                        "from": reply.author.full_name if reply.author else None,
                        "sent_at": reply.created_at.isoformat() if reply.created_at else None,
                    }
                    for reply in complaint.responses
                    if not reply.is_internal
                ],
            }
            for complaint in complaints
        ],
        "messages_you_wrote": [
            {
                "message": reply.message,
                "written_at": reply.created_at.isoformat() if reply.created_at else None,
            }
            for reply in written
            if not reply.is_internal
        ],
        "notifications": [
            {
                "title": item.title,
                "message": item.message,
                "received_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in notifications
        ],
        "files_you_uploaded": [
            {
                "name": attachment.original_name,
                "size_bytes": attachment.size_bytes,
                "uploaded_at": attachment.created_at.isoformat() if attachment.created_at else None,
            }
            for attachment in attachments
        ],
        "messages_sent_to_you": [
            {
                "channel": message.channel,
                "subject": message.subject,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
            }
            for message in messages
        ],
    }


def erase_user(user: User, reason: str = "requested by the data subject") -> dict:
    """Sever a person from their records.

    Returns a summary suitable for a compliance log.
    """
    if user.role == "platform_admin":
        raise ValueError("A platform administrator cannot be erased through this route.")

    summary = {
        "erased_at": utcnow().isoformat(),
        "reason": reason,
        "complaints_anonymised": 0,
        "messages_redacted": 0,
        "attachments_destroyed": 0,
        "notifications_deleted": 0,
    }

    # Files carry the highest risk: a photograph or a scanned document
    # identifies someone regardless of the row it hangs off.
    for attachment in Attachment.query.filter_by(uploaded_by_id=user.id).all():
        storage.delete(attachment.stored_name)
        if attachment.thumbnail_name:
            storage.delete(attachment.thumbnail_name)
        db.session.delete(attachment)
        summary["attachments_destroyed"] += 1

    for complaint in Complaint.query.filter_by(student_id=user.id).all():
        complaint.is_anonymous = True
        # The person's own account of events belongs to them, so it goes.
        # What the institution recorded about its handling stays.
        complaint.title = "Withdrawn at the request of the complainant"
        complaint.description = (
            "The complainant asked for their personal data to be erased. The "
            "outcome is retained as an institutional record; the original "
            "account of events has been removed."
        )
        summary["complaints_anonymised"] += 1

    for reply in Response.query.filter_by(author_id=user.id).all():
        if reply.is_internal:
            continue
        reply.message = "[Removed at the request of the author]"
        reply.author_id = None
        summary["messages_redacted"] += 1

    # Notifications duplicate what was already delivered and hold no
    # institutional value, so they go entirely.
    summary["notifications_deleted"] = Notification.query.filter_by(user_id=user.id).delete(
        synchronize_session=False
    )

    OutboundMessage.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    PasswordReset.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    # Audit entries survive but stop pointing at a person. Deleting them
    # would break the record of who decided what.
    ComplaintEvent.query.filter_by(actor_id=user.id).update(
        {ComplaintEvent.actor_id: None}, synchronize_session=False
    )

    # A unique meaningless value in every identifying column. A shared
    # constant would collide on the unique index at the second erasure.
    token = new_uuid()[:8]
    user.full_name = "Erased account"
    user.email = f"erased+{token}@invalid"
    user.matric_number = None
    user.phone = None
    user.faculty = None
    user.department_name = None
    user.is_active = False
    user.erased_at = utcnow()
    user.set_password(new_uuid())

    db.session.commit()
    return summary


def purge_expired_data(institution) -> dict:
    """Delete records past an institution's retention period.

    Storage limitation means personal data is not kept indefinitely. Only
    closed and declined complaints are eligible: an open one is still in
    use however old it is.
    """
    months = institution.retention_months or 0
    if months <= 0:
        return {"skipped": "retention is not configured", "complaints_purged": 0}

    cutoff = utcnow() - timedelta(days=months * 30)
    summary = {
        "cutoff": cutoff.isoformat(),
        "complaints_purged": 0,
        "attachments_destroyed": 0,
    }

    candidates = (
        Complaint.query.filter(
            Complaint.institution_id == institution.id,
            Complaint.status.in_(("closed", "declined")),
        )
        .limit(500)
        .all()
    )

    for complaint in candidates:
        closed = as_aware(complaint.closed_at or complaint.updated_at)
        if not closed or closed > cutoff:
            continue

        for attachment in complaint.attachments:
            storage.delete(attachment.stored_name)
            if attachment.thumbnail_name:
                storage.delete(attachment.thumbnail_name)
            summary["attachments_destroyed"] += 1

        db.session.delete(complaint)
        summary["complaints_purged"] += 1

    db.session.commit()
    return summary
