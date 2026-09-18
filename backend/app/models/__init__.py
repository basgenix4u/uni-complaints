"""SQLAlchemy models.

Imported here so Flask-Migrate detects every table.
"""

from app.models.attachment import (  # noqa: F401
    ALLOWED_MIME_TYPES,
    MAX_FILE_BYTES,
    MAX_FILES_PER_COMPLAINT,
    Attachment,
)
from app.models.complaint import (  # noqa: F401
    ALLOWED_TRANSITIONS,
    PRIORITIES,
    STATUSES,
    Complaint,
    ComplaintEvent,
    Notification,
    Response,
)
from app.models.institution import Department, Institution  # noqa: F401
from app.models.message import OutboundMessage  # noqa: F401
from app.models.user import ROLES, User, normalise_matric, normalise_phone  # noqa: F401

__all__ = [
    "Attachment",
    "Institution",
    "Department",
    "OutboundMessage",
    "User",
    "Complaint",
    "Response",
    "Notification",
    "ComplaintEvent",
    "ROLES",
    "STATUSES",
    "PRIORITIES",
    "ALLOWED_TRANSITIONS",
    "normalise_matric",
    "normalise_phone",
]
