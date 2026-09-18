"""Comma separated exports.

Institutions report to senates, councils and regulators on schedules that
no dashboard will ever match. Giving them the underlying rows avoids
requests for one more chart every term.
"""

import csv
import io

from app.models.base import as_aware
from app.models.complaint import Complaint
from app.models.user import User

COMPLAINT_COLUMNS = [
    "ticket_number",
    "title",
    "category",
    "priority",
    "status",
    "department",
    "owner",
    "student_name",
    "matric_number",
    "filed_at",
    "acknowledged_at",
    "resolved_at",
    "resolution_hours",
    "within_deadline",
    "escalated",
    "response_count",
    "satisfaction_rating",
]


def _timestamp(value) -> str:
    moment = as_aware(value)
    return moment.strftime("%Y-%m-%d %H:%M") if moment else ""


def _cell(value) -> str:
    """Neutralise values a spreadsheet would treat as a formula.

    A title beginning with an equals sign is executed on open by Excel and
    similar tools, which turns an exported complaint into a way to run
    something on a registrar's machine.
    """
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def complaints_to_csv(complaints: list[Complaint], include_personal: bool = True) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)

    columns = list(COMPLAINT_COLUMNS)
    if not include_personal:
        columns.remove("student_name")
        columns.remove("matric_number")
    writer.writerow(columns)

    for complaint in complaints:
        anonymous = complaint.is_anonymous
        row = {
            "ticket_number": complaint.ticket_number,
            "title": complaint.title,
            "category": complaint.category,
            "priority": complaint.priority,
            "status": complaint.status,
            "department": complaint.department.name if complaint.department else "",
            "owner": complaint.assigned_to.full_name if complaint.assigned_to else "",
            "student_name": (
                "" if anonymous or not complaint.student else complaint.student.full_name
            ),
            "matric_number": (
                "" if anonymous or not complaint.student else (complaint.student.matric_number or "")
            ),
            "filed_at": _timestamp(complaint.created_at),
            "acknowledged_at": _timestamp(complaint.acknowledged_at),
            "resolved_at": _timestamp(complaint.resolved_at),
            "resolution_hours": complaint.resolution_hours or "",
            "within_deadline": _within_deadline(complaint),
            "escalated": "yes" if complaint.escalated_at else "no",
            "response_count": complaint.response_count,
            "satisfaction_rating": complaint.satisfaction_rating or "",
        }
        writer.writerow([_cell(row[column]) for column in columns])

    return buffer.getvalue()


def _within_deadline(complaint: Complaint) -> str:
    if not complaint.resolved_at or not complaint.resolve_due_at:
        return ""
    return "yes" if as_aware(complaint.resolved_at) <= as_aware(complaint.resolve_due_at) else "no"


def users_to_csv(users: list[User]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    columns = ["full_name", "email", "role", "matric_number", "faculty", "active", "joined"]
    writer.writerow(columns)

    for user in users:
        writer.writerow(
            [
                _cell(user.full_name),
                _cell(user.email),
                _cell(user.role),
                _cell(user.matric_number or ""),
                _cell(user.faculty or ""),
                "yes" if user.is_active else "no",
                _timestamp(user.created_at),
            ]
        )

    return buffer.getvalue()
