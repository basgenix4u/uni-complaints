"""Record of who read what.

The complaint audit trail records changes. It does not record reads, and
for a system where a complaint may name a member of staff, "which officers
opened this" is a question that eventually gets asked in a disciplinary or
regulatory context.

Only staff access is recorded. A student reading their own complaint is
the ordinary use of the system and logging it would bury the entries that
matter.
"""

from app.extensions import db
from app.models.base import fk, new_uuid, utcnow


class AccessLog(db.Model):
    __tablename__ = "access_logs"
    __table_args__ = (
        db.Index("ix_access_complaint_time", "complaint_id", "created_at"),
        db.Index("ix_access_actor_time", "actor_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id = db.Column(
        db.String(36), db.ForeignKey(fk("complaints.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id = db.Column(db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"), index=True)

    # Role at the time of access. Kept separately because a person's role
    # can change afterwards and the log should say what they were then.
    actor_role = db.Column(db.String(30))
    action = db.Column(db.String(30), nullable=False, default="viewed")

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    actor = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "actor": self.actor.full_name if self.actor else "Removed account",
            "actor_role": self.actor_role,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AccessLog {self.action} {self.complaint_id}>"
