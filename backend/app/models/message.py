"""Outbound message queue."""

from app.extensions import db
from app.models.base import TimestampMixin, new_uuid


class OutboundMessage(TimestampMixin, db.Model):
    """An email or text awaiting delivery.

    Notifications are recorded here first and sent by a separate worker,
    so a provider outage delays delivery instead of failing the request
    that triggered it.
    """

    __tablename__ = "outbound_messages"
    __table_args__ = (db.Index("ix_outbound_status_created", "status", "created_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"))
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id", ondelete="CASCADE"))

    channel = db.Column(db.String(10), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    last_attempt_at = db.Column(db.DateTime(timezone=True))
    sent_at = db.Column(db.DateTime(timezone=True))
    error = db.Column(db.String(500))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "status": self.status,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }

    def __repr__(self) -> str:
        return f"<OutboundMessage {self.channel} {self.status}>"
