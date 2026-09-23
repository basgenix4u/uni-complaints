"""Working-hours SLA calculation and escalation.

A complaint filed at 18:00 on Friday should not be overdue by Monday
morning. Deadlines therefore advance only through an institution's working
hours, skipping weekends and Nigerian public holidays.
"""

from datetime import date, datetime, time, timedelta, timezone

from app.extensions import db
from app.models.base import as_aware, utcnow
from app.models.complaint import Complaint, PRIORITY_SLA_FACTOR
from app.services.delivery import queue_sms
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


def deadline_for(institution, department, priority: str, start: datetime | None = None,
                 override_hours: int | None = None):
    """Acknowledgement and resolution deadlines in working hours.

    Three settings can supply the base figure, and the most specific one
    wins: the routing rule for this category, then the handling unit,
    then the institution. A missing result and a broken tap are both
    Registry's problem and are not the same kind of wait.
    """
    start = start or utcnow()
    base_hours = (
        override_hours
        or (department.sla_hours if department and department.sla_hours else None)
        or institution.default_sla_hours
    )
    factor = PRIORITY_SLA_FACTOR.get(priority, 1.0)

    open_hour = institution.working_hours_start
    close_hour = institution.working_hours_end

    return (
        # Acknowledgement is part of the same promise as resolution. An
        # urgent safety report that resolves four times faster but waits
        # the same full day to be acknowledged is not urgent in any
        # meaningful sense.
        add_working_hours(
            start, institution.acknowledge_sla_hours * factor, open_hour, close_hour
        ),
        add_working_hours(start, base_hours * factor, open_hour, close_hour),
    )


# Base working hours a rung is given before the next one is told. The
# priority factor applies here as it does to acknowledgement and
# resolution: urgent cases climb in six hours, medium in twenty-four,
# and low-priority work is allowed forty-eight.
ESCALATION_STEP_HOURS = 24


def escalation_step_hours(priority: str) -> float:
    return ESCALATION_STEP_HOURS * PRIORITY_SLA_FACTOR.get(priority, 1.0)


def escalation_ladder(complaint) -> list[tuple[str, list]]:
    """Who is told, in order, as a complaint goes unanswered.

    A university has a chain of command and it is worth following. The
    demo notified every department head at once, which trains people to
    ignore the alerts and leaves nobody accountable. This climbs one rung
    at a time: the unit that owns the work, then the office above it,
    then the institution.

    Empty rungs are dropped rather than stalling the climb, so an
    institution that has not appointed a dean still escalates.
    """
    from app.models.routing import RoutingRule
    from app.models.user import User
    from app.security import can_view_complaint

    def staff_in(department_id, roles):
        if not department_id:
            return []
        return (
            User.query.filter(
                User.institution_id == complaint.institution_id,
                User.department_id == department_id,
                User.role.in_(roles),
                User.is_active.is_(True),
            )
            .limit(10)
            .all()
        )

    rule = RoutingRule.query.filter_by(
        institution_id=complaint.institution_id, category=complaint.category
    ).first()

    rungs: list[tuple[str, list]] = [
        ("the unit head", staff_in(complaint.department_id, ("dept_head", "dean"))),
    ]

    # The office above the handling unit. For an academic matter that is
    # the dean of the student's faculty; for an administrative one it is
    # whichever unit the rule nominates, usually Registry.
    if rule and rule.target_type == "department":
        student = db.session.get(User, complaint.student_id)
        faculty_id = student.faculty_id if student else None
        deans = (
            User.query.filter(
                User.institution_id == complaint.institution_id,
                User.faculty_id == faculty_id,
                User.role == "dean",
                User.is_active.is_(True),
            ).all()
            if faculty_id
            else []
        )
        rungs.append(("the dean", deans))
    elif rule and rule.escalates_to_department_id:
        rungs.append(
            ("the escalation unit", staff_in(rule.escalates_to_department_id, ("dept_head", "dean")))
        )

    rungs.append(
        (
            "the institution",
            User.query.filter(
                User.institution_id == complaint.institution_id,
                User.role == "institution_admin",
                User.is_active.is_(True),
            )
            .limit(10)
            .all(),
        )
    )

    # A confidential complaint must not widen its audience simply because
    # it was ignored. Anyone who could not open it is dropped here.
    return [
        (label, [u for u in people if can_view_complaint(u, complaint)])
        for label, people in rungs
        if people
    ]


def _escalate_one(complaint, now) -> bool:
    """Advance a complaint one rung. Returns True if it moved.

    Missing the deadline and telling somebody about it are kept apart on
    purpose. An institution that has appointed nobody to a unit still has
    an overdue complaint, and the student is still owed the news; it
    simply goes straight onto the ignored report instead of climbing.
    """
    from app.models.institution import Institution
    from app.models.user import User

    ladder = escalation_ladder(complaint)
    level = complaint.escalation_level or 0
    first_time = complaint.escalated_at is None

    if level >= len(ladder) and not first_time:
        # The top has been reached and nothing happened. Nobody else is
        # told; the complaint now belongs on the ignored report.
        complaint.next_escalation_at = None
        return False

    label = None
    if level < len(ladder):
        label, recipients = ladder[level]
        for person in recipients:
            notify(
                person.id,
                complaint.institution_id,
                "Complaint needs attention",
                f"{complaint.ticket_number} was not answered in time and has been raised with you.",
                complaint.id,
                "escalation",
            )
        complaint.escalation_level = level + 1

        institution = db.session.get(Institution, complaint.institution_id)
        complaint.next_escalation_at = add_working_hours(
            now,
            escalation_step_hours(complaint.priority),
            institution.working_hours_start if institution else 8,
            institution.working_hours_end if institution else 17,
        )
    else:
        complaint.next_escalation_at = None

    record_event(
        complaint,
        None,
        "escalated",
        to_value=f"level {complaint.escalation_level}",
        note=(
            f"Raised with {label} after no response."
            if label
            else "Past its deadline, and there is nobody above to raise it with."
        ),
    )

    if first_time:
        complaint.escalated_at = now
        complaint.priority = "urgent"

        notify(
            complaint.student_id,
            complaint.institution_id,
            "Your complaint has been escalated",
            f"{complaint.ticket_number} passed its deadline, so it has been raised with "
            "senior staff. You do not need to do anything.",
            complaint.id,
            "escalation",
        )

        # Escalation is the one event worth the cost of a text: data
        # runs out, but a phone still receives SMS.
        student = db.session.get(User, complaint.student_id)
        if student and student.phone:
            queue_sms(
                complaint.institution_id,
                student.phone,
                f"Resolve: complaint {complaint.ticket_number} passed its deadline and has "
                "been escalated to senior staff. No action needed from you.",
                user_id=student.id,
                complaint_id=complaint.id,
            )

    return True


def run_escalation_sweep(institution_id: str | None = None) -> dict:
    """Escalate complaints that have passed a deadline.

    Safe to call repeatedly: each complaint advances at most one rung per
    sweep, and only once the previous rung has had its own window to
    respond.
    """
    now = utcnow()

    due_now = db.or_(
        db.and_(
            Complaint.escalated_at.is_(None),
            Complaint.resolve_due_at.isnot(None),
            Complaint.resolve_due_at < now,
        ),
        db.and_(
            Complaint.next_escalation_at.isnot(None),
            Complaint.next_escalation_at < now,
        ),
    )

    query = Complaint.query.filter(
        Complaint.status.notin_(("resolved", "closed", "declined")), due_now
    )
    if institution_id:
        query = query.filter(Complaint.institution_id == institution_id)

    escalated = 0
    for complaint in query.limit(500).all():
        if _escalate_one(complaint, now):
            escalated += 1

    # A separate pass for the reminder, which is about an approaching
    # deadline rather than a missed one.
    approaching = Complaint.query.filter(
        Complaint.status.notin_(("resolved", "closed", "declined")),
        Complaint.escalated_at.is_(None),
        Complaint.reminder_sent_at.is_(None),
        Complaint.assigned_to_id.isnot(None),
        Complaint.resolve_due_at.isnot(None),
        Complaint.resolve_due_at >= now,
    )
    if institution_id:
        approaching = approaching.filter(Complaint.institution_id == institution_id)

    reminded = 0
    for complaint in approaching.limit(500).all():
        due = as_aware(complaint.resolve_due_at)
        if due is None or (due - now) > timedelta(hours=12):
            continue
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
