"""SQLAlchemy models.

Imported here so Flask-Migrate detects every table.
"""

from app.models.academic import (  # noqa: F401
    ENROLMENT_STATUSES,
    AcademicDepartment,
    AcademicSession,
    Faculty,
    InstitutionInterest,
    StudentRecord,
)
from app.models.access_log import AccessLog  # noqa: F401
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
from app.models.reset import PasswordReset  # noqa: F401
from app.models.routing import DEFAULT_ROUTING, DEFAULT_UNITS, RoutingRule  # noqa: F401
from app.models.user import ROLES, User, normalise_matric, normalise_phone  # noqa: F401

__all__ = [
    "AcademicDepartment",
    "AcademicSession",
    "AccessLog",
    "Faculty",
    "InstitutionInterest",
    "RoutingRule",
    "StudentRecord",
    "Attachment",
    "Institution",
    "Department",
    "OutboundMessage",
    "PasswordReset",
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
