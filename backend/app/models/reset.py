"""Password reset tokens."""

import hashlib
import secrets
from datetime import timedelta

from app.extensions import db
from app.models.base import new_uuid, utcnow

# Long enough that guessing is impractical, short enough to be pasted from
# an email without wrapping.
TOKEN_BYTES = 32
TOKEN_LIFETIME = timedelta(hours=1)


def hash_token(raw: str) -> str:
    """Hash a reset token for storage.

    Only the hash is kept. Anyone reading the database, including a stolen
    backup, cannot use the rows to take over an account.
    """
    return hashlib.sha256(raw.encode()).hexdigest()


class PasswordReset(db.Model):
    __tablename__ = "password_resets"
    __table_args__ = (db.Index("ix_reset_user_used", "user_id", "used_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))

    # Recorded to help an institution investigate a suspicious reset.
    requested_ip = db.Column(db.String(45))

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User")

    @classmethod
    def issue(cls, user, ip: str | None = None) -> tuple["PasswordReset", str]:
        """Create a token, returning the record and the raw value to send."""
        raw = secrets.token_urlsafe(TOKEN_BYTES)
        record = cls(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + TOKEN_LIFETIME,
            requested_ip=ip,
        )
        db.session.add(record)
        return record, raw

    @property
    def is_usable(self) -> bool:
        from app.models.base import as_aware

        if self.used_at is not None:
            return False
        return utcnow() < as_aware(self.expires_at)

    def consume(self) -> None:
        self.used_at = utcnow()

    def __repr__(self) -> str:
        return f"<PasswordReset {self.user_id}>"
