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
from app.models.invitation import Invitation  # noqa: F401
from app.models.message import OutboundMessage  # noqa: F401
from app.models.reset import PasswordReset  # noqa: F401
from app.models.routing import (  # noqa: F401
    DEFAULT_PRIORITY_POLICIES,
    DEFAULT_ROUTING,
    DEFAULT_UNITS,
    PriorityPolicy,
    RoutingRule,
)
from app.models.verification import EmailVerification  # noqa: F401
from app.models.user import (  # noqa: F401
    INVITABLE_ROLES,
    ROLES,
    User,
    normalise_matric,
    normalise_phone,
)

__all__ = [
    "AcademicDepartment",
    "AcademicSession",
    "AccessLog",
    "Faculty",
    "InstitutionInterest",
    "Invitation",
    "RoutingRule",
    "PriorityPolicy",
    "StudentRecord",
    "Attachment",
    "Institution",
    "Department",
    "OutboundMessage",
    "PasswordReset",
    "EmailVerification",
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
