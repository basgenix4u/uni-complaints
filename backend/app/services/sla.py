"""Working-hours SLA calculation and escalation.

A complaint filed at 18:00 on Friday should not be overdue by Monday
morning. Deadlines therefore advance only through an institution's working
hours, skipping weekends and Nigerian public holidays.
"""

from datetime import date, datetime, time, timedelta, timezone

from app.extensions import db
from app.models.base import as_aware, utcnow
from app.models.complaint import Complaint, PRIORITY_SLA_FACTOR
from app.services.notifications import notify, record_event

# West Africa Time. Nigeria does not observe daylight saving, so a fixed
# offset is correct.
WAT = timezone(timedelta(hours=1))


def fixed_holidays(year: int) -> set[date]:
    """Public holidays with fixed dates.

    Islamic and Easter holidays move each year and are announced by the
    federal government, so they are configured per institution rather than
    computed here.
    """
    return {
        date(year, 1, 1),    # New Year's Day
        date(year, 5, 1),    # Workers' Day
        date(year, 6, 12),   # Democracy Day
        date(year, 10, 1),   # Independence Day
        date(year, 12, 25),  # Christmas Day
        date(year, 12, 26),  # Boxing Day
    }


def is_working_day(moment: datetime, holidays: set[date]) -> bool:
    return moment.weekday() < 5 and moment.date() not in holidays


def add_working_hours(start: datetime, hours: float, open_hour: int, close_hour: int,
                      holidays: set[date] | None = None) -> datetime:
    """Advance a timestamp by a number of working hours."""
    if holidays is None:
        holidays = fixed_holidays(start.year) | fixed_holidays(start.year + 1)

    span = max(close_hour - open_hour, 1)
    cursor = start.astimezone(WAT)
    remaining = hours

    # Start from the next opening if outside the working day.
    if cursor.hour < open_hour:
        cursor = cursor.replace(hour=open_hour, minute=0, second=0, microsecond=0)
    elif cursor.hour >= close_hour:
        cursor = (cursor + timedelta(days=1)).replace(
            hour=open_hour, minute=0, second=0, microsecond=0
        )

    guard = 0
    while remaining > 0:
        guard += 1
        if guard > 2000:
            break

        if not is_working_day(cursor, holidays):
            cursor = (cursor + timedelta(days=1)).replace(
                hour=open_hour, minute=0, second=0, microsecond=0
            )
            continue

        close_at = cursor.replace(hour=close_hour, minute=0, second=0, microsecond=0)
        available = (close_at - cursor).total_seconds() / 3600

        if remaining <= available:
            cursor += timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= available
            cursor = (cursor + timedelta(days=1)).replace(
                hour=open_hour, minute=0, second=0, microsecond=0
            )

    return cursor.astimezone(timezone.utc)


def deadline_for(institution, department, priority: str, start: datetime | None = None):
    """Acknowledgement and resolution deadlines in working hours."""
    start = start or utcnow()
    base_hours = (department.sla_hours if department and department.sla_hours else None) or (
        institution.default_sla_hours
    )
    factor = PRIORITY_SLA_FACTOR.get(priority, 1.0)

    open_hour = institution.working_hours_start
    close_hour = institution.working_hours_end

    return (
        add_working_hours(start, institution.acknowledge_sla_hours, open_hour, close_hour),
        add_working_hours(start, base_hours * factor, open_hour, close_hour),
    )


def run_escalation_sweep(institution_id: str | None = None) -> dict:
    """Escalate complaints that have passed their deadline.

    Idempotent: a complaint is escalated once, recorded on the audit trail,
    and skipped on later runs. Safe to call repeatedly from a scheduler.
    """
    from app.models.institution import Institution
    from app.models.user import User

    now = utcnow()
    query = Complaint.query.filter(
        Complaint.status.notin_(("resolved", "closed", "declined")),
        Complaint.escalated_at.is_(None),
        Complaint.resolve_due_at.isnot(None),
    )
    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)

    escalated = 0
    reminded = 0

    for complaint in query.limit(500).all():
        due = as_aware(complaint.resolve_due_at)
        if due is None:
            continue

        if now > due:
            complaint.escalated_at = now
            complaint.priority = "urgent" if complaint.priority != "urgent" else "urgent"

            leaders = (
                User.query.filter(
                    User.institution_id == complaint.institution_id,
                    User.role.in_(("dept_head", "institution_admin")),
                    User.is_active.is_(True),
                )
                .limit(10)
                .all()
            )
            for leader in leaders:
                notify(
                    leader.id,
                    complaint.institution_id,
                    "Complaint passed its deadline",
                    f"{complaint.ticket_number} was not answered in time and needs attention.",
                    complaint.id,
                    "escalation",
                )

            record_event(
                complaint,
                None,
                "escalated",
                to_value="overdue",
                note="No response before the deadline.",
            )
            notify(
                complaint.student_id,
                complaint.institution_id,
                "Your complaint has been escalated",
                f"{complaint.ticket_number} passed its deadline, so it has been raised with "
                "senior staff. You do not need to do anything.",
                complaint.id,
                "escalation",
            )
            escalated += 1

        elif complaint.assigned_to_id and (due - now) <= timedelta(hours=12):
            # One reminder before the deadline, tracked so it is not repeated.
            if not complaint.reminder_sent_at:
                complaint.reminder_sent_at = now
                notify(
                    complaint.assigned_to_id,
                    complaint.institution_id,
                    "Deadline approaching",
                    f"{complaint.ticket_number} is due soon.",
                    complaint.id,
                    "reminder",
                )
                reminded += 1

    db.session.commit()
    return {"escalated": escalated, "reminded": reminded, "checked_at": now.isoformat()}
