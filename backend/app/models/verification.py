"""Email verification tokens.

Nothing previously stopped somebody registering with an address that was
not theirs. That matters more here than on most systems: a complaint
carries someone's name and matriculation number, and an account opened
on a stranger's address puts their grievance in the wrong hands.

The same hashed-token pattern as password resets, for the same reason: a
stolen backup should not yield working links.
"""

import hashlib
import secrets
from datetime import timedelta

from app.extensions import db
from app.models.base import fk, new_uuid, utcnow

TOKEN_BYTES = 32

# Longer than a password reset. A reset is a deliberate act and the person
# is waiting; a verification email may arrive while someone is in a
# lecture, and making them start again teaches them the product is
# tedious.
TOKEN_LIFETIME = timedelta(days=3)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class EmailVerification(db.Model):
    __tablename__ = "email_verifications"
    __table_args__ = (db.Index("ix_verification_user_used", "user_id", "used_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))

    # The address the token was issued for. Kept so that changing an email
    # before verifying does not leave a token that confirms the old one.
    email = db.Column(db.String(255), nullable=False)

    sent_count = db.Column(db.Integer, default=1, nullable=False)
    last_sent_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User")

    @classmethod
    def issue(cls, user) -> tuple["EmailVerification", str]:
        """Create a token, returning the record and the raw value to send."""
        raw = secrets.token_urlsafe(TOKEN_BYTES)
        record = cls(
            user_id=user.id,
            email=user.email,
            token_hash=hash_token(raw),
            expires_at=utcnow() + TOKEN_LIFETIME,
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
        return f"<EmailVerification {self.user_id}>"
