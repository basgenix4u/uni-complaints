"""User accounts and roles."""

import re

from app.extensions import bcrypt, db
from app.models.base import TimestampMixin, new_uuid, utcnow

# Ordered by privilege; used for hierarchical permission checks.
ROLES = ("student", "officer", "dept_head", "institution_admin", "platform_admin")
ROLE_RANK = {role: index for index, role in enumerate(ROLES)}

STAFF_ROLES = ("officer", "dept_head", "institution_admin", "platform_admin")


def normalise_matric(value: str | None) -> str | None:
    """Accept the formats students actually type.

    `eng/coe/21/013`, `ENG-COE-21-013` and `ENG COE 21 013` all normalise to
    `ENG/COE/21/013`.
    """
    if not value:
        return None
    cleaned = re.sub(r"[\s\-_/]+", "/", value.strip().upper())
    return cleaned.strip("/")


def normalise_phone(value: str | None) -> str | None:
    """Normalise Nigerian numbers to E.164."""
    if not value:
        return None
    digits = re.sub(r"[^\d+]", "", value.strip())
    if digits.startswith("+234"):
        return digits
    if digits.startswith("234"):
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+234" + digits[1:]
    return digits


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "email", name="uq_user_email_per_institution"),
        db.UniqueConstraint("institution_id", "matric_number", name="uq_user_matric_per_institution"),
        db.Index("ix_user_institution_role", "institution_id", "role"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    # Nullable so a platform administrator can exist outside any tenant.
    institution_id = db.Column(
        db.String(36), db.ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    department_id = db.Column(
        db.String(36), db.ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    matric_number = db.Column(db.String(40), index=True)
    faculty = db.Column(db.String(100))
    department_name = db.Column(db.String(120))
    phone = db.Column(db.String(30))

    role = db.Column(db.String(30), default="student", nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    # Set when the account has been through erasure. The row survives so
    # foreign keys stay intact, but it identifies nobody.
    erased_at = db.Column(db.DateTime(timezone=True))

    institution = db.relationship("Institution", back_populates="users")
    department = db.relationship("Department", foreign_keys=[department_id])

    # -- password -----------------------------------------------------

    def set_password(self, raw: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw)

    def record_login(self) -> None:
        self.last_login_at = utcnow()

    # -- roles --------------------------------------------------------

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    def has_role_at_least(self, role: str) -> bool:
        return ROLE_RANK.get(self.role, -1) >= ROLE_RANK.get(role, 99)

    # -- serialisation ------------------------------------------------

    def to_dict(self, include_contact: bool = True) -> dict:
        data = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "institution_id": self.institution_id,
            "department_id": self.department_id,
            "matric_number": self.matric_number,
            "faculty": self.faculty,
            "department_name": self.department_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_contact:
            data["phone"] = self.phone
        return data

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
