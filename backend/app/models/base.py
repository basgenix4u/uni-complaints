"""Shared model primitives."""

import os
import uuid
from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp.

    `datetime.utcnow()` is deprecated from Python 3.12 and returns a naive
    value, which compares incorrectly against aware timestamps.
    """
    return datetime.now(timezone.utc)


def fk(target: str) -> str:
    """Qualify a foreign key target with the configured schema.

    A reference written as "users.id" resolves against the search path,
    which is not reliable once these tables live outside `public`.
    """
    schema = os.getenv("DB_SCHEMA") or None
    if not schema or "sqlite" in os.getenv("DATABASE_URL", "sqlite"):
        return target
    return f"{schema}.{target}"


def new_uuid() -> str:
    return str(uuid.uuid4())


def as_aware(value: datetime | None) -> datetime | None:
    """Treat a stored timestamp as UTC.

    SQLite does not preserve timezone information, so values read back are
    naive. Comparing those against an aware `utcnow()` raises a TypeError.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class TenantMixin:
    """Binds a row to one institution.

    Every tenant-owned table carries this. Scoping is applied by the request
    context rather than by callers, so a forgotten filter cannot leak data
    across institutions.
    """

    @staticmethod
    def _institution_fk():
        return db.Column(
            db.String(36),
            db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
