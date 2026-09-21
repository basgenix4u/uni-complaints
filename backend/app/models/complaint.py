"""Complaints, responses, notifications and the audit trail."""

from datetime import timedelta

from app.extensions import db
from app.models.base import fk, TimestampMixin, as_aware, new_uuid, utcnow

STATUSES = (
    "submitted",
    "acknowledged",
    "in_progress",
    "awaiting_student",
    "resolved",
    "closed",
    "declined",
)

# Transitions permitted for staff. Anything absent is rejected by the service
# layer, so status can never move backwards or skip the audit trail.
ALLOWED_TRANSITIONS = {
    "submitted": ("acknowledged", "in_progress", "declined"),
    "acknowledged": ("in_progress", "awaiting_student", "declined"),
    "in_progress": ("awaiting_student", "resolved", "declined"),
    "awaiting_student": ("in_progress", "resolved", "declined"),
    "resolved": ("closed", "in_progress"),
    "closed": (),
    "declined": ("in_progress",),
}

TERMINAL_STATUSES = ("closed", "declined")

PRIORITIES = ("low", "medium", "high", "urgent")

# Multipliers applied to the department or institution SLA.
PRIORITY_SLA_FACTOR = {"low": 2.0, "medium": 1.0, "high": 0.5, "urgent": 0.25}


class Complaint(TimestampMixin, db.Model):
    __tablename__ = "complaints"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "ticket_number", name="uq_ticket_per_institution"),
        db.Index("ix_complaint_institution_status", "institution_id", "status"),
        db.Index("ix_complaint_institution_created", "institution_id", "created_at"),
        db.Index("ix_complaint_assignee", "institution_id", "assigned_to_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )

    ticket_number = db.Column(db.String(20), nullable=False, index=True)

    student_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to_id = db.Column(db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"), index=True)
    department_id = db.Column(
        db.String(36), db.ForeignKey(fk("departments.id"), ondelete="SET NULL"), index=True
    )

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)

    priority = db.Column(db.String(20), default="medium", nullable=False, index=True)
    status = db.Column(db.String(30), default="submitted", nullable=False, index=True)

    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)

    acknowledge_due_at = db.Column(db.DateTime(timezone=True))
    resolve_due_at = db.Column(db.DateTime(timezone=True), index=True)
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    resolved_at = db.Column(db.DateTime(timezone=True))
    closed_at = db.Column(db.DateTime(timezone=True))

    resolution_note = db.Column(db.Text)
    decline_reason = db.Column(db.Text)

    satisfaction_rating = db.Column(db.Integer)
    satisfaction_comment = db.Column(db.String(500))
    response_count = db.Column(db.Integer, default=0, nullable=False)

    # Set once when the deadline passes, so a sweep cannot escalate the
    # same complaint twice.
    escalated_at = db.Column(db.DateTime(timezone=True), index=True)
    reminder_sent_at = db.Column(db.DateTime(timezone=True))

    student = db.relationship("User", foreign_keys=[student_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    department = db.relationship("Department")
    responses = db.relationship(
        "Response",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="Response.created_at",
    )
    events = db.relationship(
        "ComplaintEvent",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintEvent.created_at",
    )
    attachments = db.relationship(
        "Attachment", cascade="all, delete-orphan", order_by="Attachment.created_at"
    )

    # -- SLA ----------------------------------------------------------

    def apply_sla(self, institution, department=None) -> None:
        """Set deadlines, counting only the institution's working hours."""
        from app.services.sla import deadline_for

        self.acknowledge_due_at, self.resolve_due_at = deadline_for(
            institution, department, self.priority, self.created_at or utcnow()
        )

    @property
    def is_overdue(self) -> bool:
        if self.status in ("resolved", "closed", "declined") or not self.resolve_due_at:
            return False
        return utcnow() > as_aware(self.resolve_due_at)

    @property
    def resolution_hours(self) -> float | None:
        if not self.resolved_at:
            return None
        delta = as_aware(self.resolved_at) - as_aware(self.created_at)
        return round(delta.total_seconds() / 3600, 2)

    def can_transition_to(self, status: str) -> bool:
        return status in ALLOWED_TRANSITIONS.get(self.status, ())

    # -- serialisation ------------------------------------------------

    def to_dict(self, viewer=None, include_responses: bool = False) -> dict:
        is_staff = bool(viewer and viewer.is_staff)

        data = {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "is_anonymous": self.is_anonymous,
            "is_overdue": self.is_overdue,
            "response_count": self.response_count,
            "resolution_note": self.resolution_note,
            "decline_reason": self.decline_reason,
            "satisfaction_rating": self.satisfaction_rating,
            "is_escalated": self.escalated_at is not None,
            "resolution_hours": self.resolution_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "acknowledge_due_at": self.acknowledge_due_at.isoformat() if self.acknowledge_due_at else None,
            "resolve_due_at": self.resolve_due_at.isoformat() if self.resolve_due_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "department": self.department.to_dict() if self.department else None,
            "assigned_admin": (
                {"id": self.assigned_to.id, "full_name": self.assigned_to.full_name}
                if self.assigned_to
                else None
            ),
        }

        # An anonymous complaint never exposes the author, including to staff.
        if self.is_anonymous:
            data["student"] = None
        elif self.student:
            data["student"] = {
                "id": self.student.id,
                "full_name": self.student.full_name,
                "matric_number": self.student.matric_number,
                "email": self.student.email if is_staff else None,
                "faculty": self.student.faculty,
                "department_name": self.student.department_name,
            }

        if include_responses:
            data["responses"] = [
                r.to_dict() for r in self.responses if is_staff or not r.is_internal
            ]
            data["attachments"] = [
                a.to_dict() for a in self.attachments if is_staff or not a.is_internal
            ]

        return data

    def to_public_dict(self) -> dict:
        """Minimal payload for unauthenticated ticket lookup.

        Deliberately excludes the description, the author and all staff notes.
        """
        return {
            "ticket_number": self.ticket_number,
            "status": self.status,
            "category": self.category,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolve_due_at": self.resolve_due_at.isoformat() if self.resolve_due_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "department": self.department.name if self.department else None,
            "is_overdue": self.is_overdue,
        }

    def __repr__(self) -> str:
        return f"<Complaint {self.ticket_number} {self.status}>"


class Response(TimestampMixin, db.Model):
    """A message on a complaint thread."""

    __tablename__ = "responses"
    __table_args__ = (db.Index("ix_response_complaint_created", "complaint_id", "created_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id = db.Column(
        db.String(36), db.ForeignKey(fk("complaints.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = db.Column(db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"), index=True)

    message = db.Column(db.Text, nullable=False)
    # Internal notes are filtered out for students in Complaint.to_dict and
    # again in the service layer before serialisation.
    is_internal = db.Column(db.Boolean, default=False, nullable=False)

    complaint = db.relationship("Complaint", back_populates="responses")
    author = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "message": self.message,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "author": (
                {
                    "id": self.author.id,
                    "full_name": self.author.full_name,
                    "role": self.author.role,
                }
                if self.author
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<Response {self.id}>"


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"
    __table_args__ = (db.Index("ix_notification_user_read", "user_id", "is_read"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id = db.Column(db.String(36), db.ForeignKey(fk("complaints.id"), ondelete="CASCADE"))

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(40), default="status_change", nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification {self.id}>"


class ComplaintEvent(db.Model):
    """Append-only audit record.

    Rows are never updated or deleted; accountability depends on the trail
    being immutable.
    """

    __tablename__ = "complaint_events"
    __table_args__ = (db.Index("ix_event_complaint_created", "complaint_id", "created_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id = db.Column(
        db.String(36), db.ForeignKey(fk("complaints.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id = db.Column(db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"))

    action = db.Column(db.String(60), nullable=False)
    from_value = db.Column(db.String(120))
    to_value = db.Column(db.String(120))
    note = db.Column(db.String(500))

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    complaint = db.relationship("Complaint", back_populates="events")
    actor = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actor": (
                {"id": self.actor.id, "full_name": self.actor.full_name, "role": self.actor.role}
                if self.actor
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<ComplaintEvent {self.action}>"
