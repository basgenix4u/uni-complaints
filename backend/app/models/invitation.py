"""Staff invitations.

Staff are insiders, so self-registration is correctly impossible. But the
demo had an administrator type a colleague's password into a form, which
is wrong twice over: one person then knows another's credentials, and
nobody is going to do it three hundred times.

An invitation is a signed, single-use, expiring link. The recipient sets
their own password, so no one else ever knows it, and an administrator can
issue hundreds from a spreadsheet.

The token handling follows the password reset model already in use: only a
hash is stored, so a stolen backup yields no working links.
"""

import hashlib
import secrets
from datetime import timedelta

from app.extensions import db
from app.models.base import as_aware, fk, new_uuid, utcnow

# Long enough to be unguessable, short enough to survive being pasted out
# of an email client that wraps lines.
TOKEN_BYTES = 32

# Staff onboarding is not urgent in the way a password reset is, and a
# registrar may forward the message to someone on leave.
TOKEN_LIFETIME = timedelta(days=14)

STATUSES = ("pending", "accepted", "revoked", "expired")


def hash_token(raw: str) -> str:
    """Hash an invitation token for storage.

    Only the hash is kept, so reading the table does not hand anyone a
    working invitation.
    """
    return hashlib.sha256(raw.encode()).hexdigest()


class Invitation(db.Model):
    __tablename__ = "invitations"
    __table_args__ = (
        db.Index("ix_invitation_institution_status", "institution_id", "status"),
        db.Index("ix_invitation_email", "institution_id", "email"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    email = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))

    # What the person becomes on acceptance. Fixed at invitation time so
    # the recipient cannot influence their own level of access.
    role = db.Column(db.String(30), nullable=False)

    # The administrative unit they will work in. Null for an institution
    # administrator, who is not tied to one.
    department_id = db.Column(
        db.String(36), db.ForeignKey(fk("departments.id"), ondelete="SET NULL")
    )
    # Set when inviting a Dean, whose scope is a faculty rather than a unit.
    faculty_id = db.Column(
        db.String(36), db.ForeignKey(fk("faculties.id"), ondelete="SET NULL")
    )

    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    status = db.Column(db.String(20), default="pending", nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True))
    revoked_at = db.Column(db.DateTime(timezone=True))

    # Who issued it, so a questionable invitation can be traced.
    invited_by_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL")
    )
    accepted_user_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL")
    )

    # How many times the message has been sent, so a reminder is visible
    # rather than looking like a duplicate invitation.
    sent_count = db.Column(db.Integer, default=1, nullable=False)
    last_sent_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    department = db.relationship("Department", foreign_keys=[department_id])
    faculty = db.relationship("Faculty", foreign_keys=[faculty_id])
    invited_by = db.relationship("User", foreign_keys=[invited_by_id])
    accepted_user = db.relationship("User", foreign_keys=[accepted_user_id])

    @classmethod
    def issue(cls, institution, email: str, role: str, invited_by,
              full_name: str | None = None, department_id: str | None = None,
              faculty_id: str | None = None) -> tuple["Invitation", str]:
        """Create an invitation, returning it and the raw token to send."""
        raw = secrets.token_urlsafe(TOKEN_BYTES)
        invitation = cls(
            institution_id=institution.id,
            email=email.strip().lower(),
            full_name=(full_name or "").strip() or None,
            role=role,
            department_id=department_id,
            faculty_id=faculty_id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + TOKEN_LIFETIME,
            invited_by_id=invited_by.id if invited_by else None,
        )
        db.session.add(invitation)
        return invitation, raw

    @property
    def is_usable(self) -> bool:
        if self.status != "pending":
            return False
        return utcnow() < as_aware(self.expires_at)

    @property
    def is_expired(self) -> bool:
        return self.status == "pending" and utcnow() >= as_aware(self.expires_at)

    def accept(self, user) -> None:
        self.status = "accepted"
        self.accepted_at = utcnow()
        self.accepted_user_id = user.id

    def revoke(self) -> None:
        self.status = "revoked"
        self.revoked_at = utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "department": self.department.name if self.department else None,
            "faculty": self.faculty.name if self.faculty else None,
            # Reported rather than stored, so a row does not need a sweep
            # to become accurate.
            "status": "expired" if self.is_expired else self.status,
            "invited_by": self.invited_by.full_name if self.invited_by else None,
            "sent_count": self.sent_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Invitation {self.email} as {self.role}>"
