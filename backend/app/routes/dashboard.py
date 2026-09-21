"""Dashboard and analytics endpoints.

Aggregates are computed in SQL rather than by loading rows into Python, so
these stay usable on an institution with a large complaint history.
"""

from collections import OrderedDict
from datetime import timedelta

from flask import Blueprint, Response, g, request
from sqlalchemy import case, func

from app.extensions import db
from app.models.base import as_aware, utcnow
from app.models.complaint import Complaint
from app.models.user import User
from app.routes.auth import ok
from app.security import auth_required, staff_required, tenant_query, visible_complaints

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

OPEN_STATUSES = ("submitted", "acknowledged", "in_progress", "awaiting_student")
CLOSED_STATUSES = ("resolved", "closed", "declined")


def _status_counts(base):
    rows = base.with_entities(Complaint.status, func.count(Complaint.id)).group_by(
        Complaint.status
    ).all()
    return {status: count for status, count in rows}


def _avg_resolution_hours(base) -> float:
    """Mean hours from creation to resolution.

    Computed in the database where the dialect allows it. PostgreSQL
    subtracts timestamps directly; SQLite has no interval type, so its
    julianday function is used instead. Either way the rows stay in the
    database rather than being pulled into the process, which matters once
    an institution has a large history.
    """
    dialect = db.session.bind.dialect.name if db.session.bind else "sqlite"
    resolved = base.filter(Complaint.resolved_at.isnot(None))

    if dialect == "postgresql":
        seconds = func.avg(
            func.extract("epoch", Complaint.resolved_at - Complaint.created_at)
        )
        value = resolved.with_entities(seconds).scalar()
        return round((value or 0) / 3600, 1)

    days = func.avg(
        func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at)
    )
    value = resolved.with_entities(days).scalar()
    return round((value or 0) * 24, 1)


@bp.get("/overview")
@staff_required("officer")
def overview():
    base = visible_complaints()
    counts = _status_counts(base)
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = sum(counts.values())
    open_count = sum(counts.get(s, 0) for s in OPEN_STATUSES)

    overdue = base.filter(
        Complaint.resolve_due_at < now,
        Complaint.status.notin_(CLOSED_STATUSES),
    ).count()

    students = tenant_query(User).filter(User.role == "student").count()

    recent = (
        base.order_by(Complaint.created_at.desc()).limit(8).all()
    )

    return ok(
        {
            "overview": {
                "total_complaints": total,
                "open_complaints": open_count,
                "total_students": students,
                "unassigned_count": base.filter(Complaint.assigned_to_id.is_(None))
                .filter(Complaint.status.notin_(CLOSED_STATUSES))
                .count(),
                "overdue_count": overdue,
                "avg_resolution_time_hours": _avg_resolution_hours(base),
                "resolution_rate": (
                    round(counts.get("resolved", 0) / total * 100, 1) if total else 0.0
                ),
            },
            "status_counts": {
                status: counts.get(status, 0)
                for status in (*OPEN_STATUSES, *CLOSED_STATUSES)
            },
            "today": {
                "new": base.filter(Complaint.created_at >= today_start).count(),
                "resolved": base.filter(Complaint.resolved_at >= today_start).count(),
            },
            "recent_complaints": [c.to_dict(viewer=g.current_user) for c in recent],
        }
    )


@bp.get("/charts/status")
@staff_required("officer")
def status_chart():
    counts = _status_counts(visible_complaints())
    return ok(
        {
            "chart_data": [
                {"label": status.replace("_", " ").title(), "value": status, "count": counts.get(status, 0)}
                for status in (*OPEN_STATUSES, *CLOSED_STATUSES)
            ]
        }
    )


@bp.get("/charts/category")
@staff_required("officer")
def category_chart():
    rows = (
        visible_complaints()
        .with_entities(Complaint.category, func.count(Complaint.id).label("count"))
        .group_by(Complaint.category)
        .order_by(func.count(Complaint.id).desc())
        .all()
    )
    return ok(
        {
            "chart_data": [
                {"label": category.replace("_", " ").title(), "value": category, "count": count}
                for category, count in rows
            ]
        }
    )


@bp.get("/charts/priority")
@staff_required("officer")
def priority_chart():
    rows = (
        visible_complaints()
        .with_entities(Complaint.priority, func.count(Complaint.id))
        .group_by(Complaint.priority)
        .all()
    )
    counts = dict(rows)
    return ok(
        {
            "chart_data": [
                {"label": priority.title(), "value": priority, "count": counts.get(priority, 0)}
                for priority in ("low", "medium", "high", "urgent")
            ]
        }
    )


@bp.get("/charts/trend")
@staff_required("officer")
def trend_chart():
    days = min(max(request.args.get("days", 30, type=int), 1), 180)
    start = (utcnow() - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    rows = (
        visible_complaints()
        .filter(Complaint.created_at >= start)
        .with_entities(
            func.date(Complaint.created_at).label("day"),
            func.count(Complaint.id),
            func.sum(case((Complaint.resolved_at.isnot(None), 1), else_=0)),
        )
        .group_by("day")
        .all()
    )
    by_day = {str(day): (created, resolved or 0) for day, created, resolved in rows}

    # Days with no activity are emitted as zero so the chart has no gaps.
    series = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).date().isoformat()
        created, resolved = by_day.get(day, (0, 0))
        series.append({"date": day, "count": created, "resolved": resolved})

    return ok({"chart_data": series, "days": days})


@bp.get("/charts/monthly")
@staff_required("officer")
def monthly_chart():
    year = request.args.get("year", utcnow().year, type=int)
    rows = (
        visible_complaints()
        .filter(func.strftime("%Y", Complaint.created_at) == str(year))
        .with_entities(func.strftime("%m", Complaint.created_at).label("month"), func.count(Complaint.id))
        .group_by("month")
        .all()
    )
    counts = {int(month): count for month, count in rows}
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    return ok(
        {
            "year": year,
            "chart_data": [
                {"month": index + 1, "month_name": name, "count": counts.get(index + 1, 0)}
                for index, name in enumerate(names)
            ],
        }
    )


@bp.get("/reports/summary")
@staff_required("dept_head")
def summary_report():
    base = visible_complaints()
    counts = _status_counts(base)
    total = sum(counts.values())

    by_category = (
        base.with_entities(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .order_by(func.count(Complaint.id).desc())
        .all()
    )

    ratings = base.filter(Complaint.satisfaction_rating.isnot(None)).with_entities(
        func.avg(Complaint.satisfaction_rating), func.count(Complaint.id)
    ).first()

    return ok(
        {
            "summary": {
                "total_complaints": total,
                "resolved": counts.get("resolved", 0),
                "declined": counts.get("declined", 0),
                "open": sum(counts.get(s, 0) for s in OPEN_STATUSES),
                "avg_resolution_time_hours": _avg_resolution_hours(base),
                "avg_satisfaction": round(ratings[0], 2) if ratings and ratings[0] else None,
                "rated_count": ratings[1] if ratings else 0,
            },
            "by_category": [
                {"category": category, "count": count} for category, count in by_category
            ],
        }
    )


@bp.get("/reports/staff-performance")
@staff_required("dept_head")
def staff_performance():
    """Per-officer workload and throughput.

    Intended for spotting unassigned backlogs and uneven distribution, not
    for ranking individuals.
    """
    staff = tenant_query(User).filter(User.role.in_(("officer", "dept_head", "institution_admin"))).all()
    base = visible_complaints()

    report = []
    for member in staff:
        assigned = base.filter(Complaint.assigned_to_id == member.id)
        assigned_count = assigned.count()
        if assigned_count == 0:
            continue
        resolved = assigned.filter(Complaint.status.in_(("resolved", "closed"))).count()
        report.append(
            {
                "id": member.id,
                "full_name": member.full_name,
                "role": member.role,
                "assigned": assigned_count,
                "resolved": resolved,
                "open": assigned.filter(Complaint.status.in_(OPEN_STATUSES)).count(),
                "overdue": assigned.filter(
                    Complaint.resolve_due_at < utcnow(),
                    Complaint.status.notin_(CLOSED_STATUSES),
                ).count(),
                "avg_resolution_time_hours": _avg_resolution_hours(assigned),
                "resolution_rate": round(resolved / assigned_count * 100, 1),
            }
        )

    report.sort(key=lambda row: row["assigned"], reverse=True)
    return ok({"staff": report})


def _csv_response(body: str, filename: str) -> Response:
    return Response(
        # A leading byte order mark makes Excel open the file as UTF-8
        # rather than mangling names with accents.
        "\ufeff" + body,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.get("/export/complaints")
@staff_required("dept_head")
def export_complaints():
    """Export the complaint register.

    Institutions report to senates and regulators on schedules no
    dashboard will match, so the underlying rows are made available.
    """
    from app.services.export import complaints_to_csv

    query = visible_complaints()

    for field in ("status", "category", "priority"):
        value = request.args.get(field)
        if value:
            query = query.filter(getattr(Complaint, field) == value)

    rows = query.order_by(Complaint.created_at.desc()).limit(5000).all()
    stamp = utcnow().strftime("%Y-%m-%d")

    return _csv_response(
        complaints_to_csv(rows, include_personal=g.current_user.has_role_at_least("dept_head")),
        f"complaints-{stamp}.csv",
    )


@bp.get("/export/users")
@staff_required("institution_admin")
def export_users():
    from app.services.export import users_to_csv

    rows = tenant_query(User).order_by(User.created_at.desc()).limit(5000).all()
    stamp = utcnow().strftime("%Y-%m-%d")

    return _csv_response(users_to_csv(rows), f"people-{stamp}.csv")


@bp.get("/student-stats")
@auth_required()
def student_stats():
    """Counts for the student's own dashboard."""
    user = g.current_user
    base = visible_complaints().filter(Complaint.student_id == user.id)
    counts = _status_counts(base)

    recent = base.order_by(Complaint.created_at.desc()).limit(5).all()

    return ok(
        {
            "statistics": {
                "total": sum(counts.values()),
                "pending": counts.get("submitted", 0) + counts.get("acknowledged", 0),
                "in_progress": counts.get("in_progress", 0) + counts.get("awaiting_student", 0),
                "resolved": counts.get("resolved", 0) + counts.get("closed", 0),
                "declined": counts.get("declined", 0),
                "awaiting_you": counts.get("awaiting_student", 0),
            },
            "recent_complaints": [c.to_dict(viewer=user) for c in recent],
        }
    )
