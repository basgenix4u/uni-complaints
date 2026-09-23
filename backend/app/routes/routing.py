"""Routing configuration and the ignored-complaints report.

Routing is the institution's own policy, so it is edited rather than
shipped. Every university disagrees with part of the default table, and
the disagreements are not bugs: scholarships sit with Bursary at one and
with Student Affairs at another.

The ignored report is the answer to "what happens to a complaint the
institution never deals with". Escalation climbs the hierarchy; when it
reaches the top and still nothing happens, the work lands here, where the
institution's head and the platform can both see it.
"""

from flask import Blueprint, g, request

from app.extensions import db
from app.models.complaint import Complaint
from app.models.institution import Department, Institution
from app.models.routing import (
    SLA_PRIORITIES,
    TARGET_TYPES,
    PrioritySlaPolicy,
    RoutingRule,
)
from app.routes.auth import fail, ok
from app.security import staff_required, tenant_query
from app.services.routing import ignored_complaints, seed_routing, seed_units

bp = Blueprint("routing", __name__, url_prefix="/api/routing")

# Beyond this a deadline is no longer a deadline. Three months of working
# hours is already far longer than any complaint should take.
MAX_SLA_HOURS = 2000

# What an institution sees before it has chosen its own matrix. These are
# suggestions only and are persisted solely by an explicit save.
DEFAULT_PRIORITY_POLICIES = {
    "low": {"acknowledge_hours": 48, "resolve_hours": 120, "escalation_step_hours": 48},
    "medium": {"acknowledge_hours": 24, "resolve_hours": 72, "escalation_step_hours": 24},
    "high": {"acknowledge_hours": 4, "resolve_hours": 24, "escalation_step_hours": 8},
    "urgent": {"acknowledge_hours": 2, "resolve_hours": 8, "escalation_step_hours": 2},
}


@bp.get("/sla-policies")
@staff_required("institution_admin")
def list_sla_policies():
    saved = {
        p.priority: p.to_dict()
        for p in tenant_query(PrioritySlaPolicy).all()
    }
    policies = []
    for priority in SLA_PRIORITIES:
        policies.append(
            saved.get(priority)
            or {"priority": priority, **DEFAULT_PRIORITY_POLICIES[priority], "is_active": False}
        )
    return ok({"policies": policies})


@bp.put("/sla-policies")
@staff_required("institution_admin")
def save_sla_policies():
    """Replace the four-priority matrix atomically."""
    payload = request.get_json(silent=True) or {}
    rows = payload.get("policies")
    if not isinstance(rows, list):
        return fail("Send the four priority policies.", 422)

    supplied = {str(row.get("priority", "")).strip(): row for row in rows if isinstance(row, dict)}
    if set(supplied) != set(SLA_PRIORITIES):
        return fail(
            "Set one policy for low, medium, high and urgent.",
            422,
            {"priorities": "Each priority must appear exactly once."},
        )

    errors = {}
    for priority, row in supplied.items():
        for field in ("acknowledge_hours", "resolve_hours", "escalation_step_hours"):
            value = row.get(field)
            if not isinstance(value, int) or not 1 <= value <= MAX_SLA_HOURS:
                errors[f"{priority}.{field}"] = (
                    f"Use a whole number between 1 and {MAX_SLA_HOURS}."
                )
        ack = row.get("acknowledge_hours")
        resolve = row.get("resolve_hours")
        if isinstance(ack, int) and isinstance(resolve, int) and ack > resolve:
            errors[f"{priority}.acknowledge_hours"] = "Acknowledgement cannot be due after resolution."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    result = []
    for priority in SLA_PRIORITIES:
        row = supplied[priority]
        policy = tenant_query(PrioritySlaPolicy).filter_by(priority=priority).first()
        if not policy:
            policy = PrioritySlaPolicy(institution_id=g.institution_id, priority=priority)
            db.session.add(policy)
        policy.acknowledge_hours = row["acknowledge_hours"]
        policy.resolve_hours = row["resolve_hours"]
        policy.escalation_step_hours = row["escalation_step_hours"]
        policy.is_active = row.get("is_active", True) is not False
        result.append(policy)

    db.session.commit()
    return ok({"policies": [p.to_dict() for p in result]}, "Priority deadlines saved.")


@bp.get("/rules")
@staff_required("institution_admin")
def list_rules():
    rules = (
        tenant_query(RoutingRule).order_by(RoutingRule.category).all()
    )
    return ok(
        {
            "rules": [rule.to_dict() for rule in rules],
            "units": [d.to_dict() for d in tenant_query(Department).order_by(Department.name)],
        }
    )


@bp.post("/rules")
@staff_required("institution_admin")
def upsert_rule():
    """Create or replace the rule for one category.

    Upsert rather than separate create and update endpoints because a
    category has exactly one rule, and the caller usually does not know
    or care whether one already exists.
    """
    payload = request.get_json(silent=True) or {}
    errors = {}

    category = (payload.get("category") or "").strip()
    target_type = (payload.get("target_type") or "unit").strip()

    if not category:
        errors["category"] = "Choose a category."
    if target_type not in TARGET_TYPES:
        errors["target_type"] = "Choose where this kind of complaint should go."

    department = None
    if payload.get("department_id"):
        department = tenant_query(Department).filter_by(id=payload["department_id"]).first()
        if not department:
            errors["department_id"] = "We could not find that unit."
    elif target_type == "unit":
        errors["department_id"] = "Choose the unit that handles this."

    escalates_to = None
    if payload.get("escalates_to_department_id"):
        escalates_to = (
            tenant_query(Department)
            .filter_by(id=payload["escalates_to_department_id"])
            .first()
        )
        if not escalates_to:
            errors["escalates_to_department_id"] = "We could not find that unit."

    sla_hours = payload.get("sla_hours")
    if sla_hours is not None:
        if not isinstance(sla_hours, int) or not 1 <= sla_hours <= MAX_SLA_HOURS:
            errors["sla_hours"] = f"Give a figure between 1 and {MAX_SLA_HOURS} hours, or leave it blank."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    rule = tenant_query(RoutingRule).filter_by(category=category).first()
    if rule is None:
        rule = RoutingRule(institution_id=g.institution_id, category=category)
        db.session.add(rule)

    rule.target_type = target_type
    # A rule that routes to the complainant's own department has no fixed
    # unit, so any previously chosen one is cleared rather than ignored.
    rule.department_id = department.id if department and target_type == "unit" else None
    rule.escalates_to_department_id = escalates_to.id if escalates_to else None
    rule.sla_hours = sla_hours
    rule.is_confidential = bool(payload.get("is_confidential"))
    rule.is_active = payload.get("is_active", True) is not False

    db.session.commit()
    return ok({"rule": rule.to_dict()}, "Routing updated.")


@bp.delete("/rules/<rule_id>")
@staff_required("institution_admin")
def delete_rule(rule_id):
    rule = tenant_query(RoutingRule).filter_by(id=rule_id).first()
    if not rule:
        return fail("We could not find that rule.", 404)

    # Complaints already filed keep the destination they were given. The
    # rule only decides where new ones go.
    db.session.delete(rule)
    db.session.commit()
    return ok(message="Rule removed.")


@bp.post("/seed")
@staff_required("institution_admin")
def seed():
    """Fill in the units and routing most institutions have.

    Additive: an existing unit or rule is left exactly as it is, so this
    is safe to run again after the table has been edited by hand.
    """
    institution = db.session.get(Institution, g.institution_id)
    if not institution:
        return fail("Your account is not linked to an institution.", 400)

    units = seed_units(institution)
    db.session.commit()
    rules = seed_routing(institution)

    return ok(
        {"units_created": units, "rules_created": rules},
        f"Added {units} units and {rules} routing rules.",
    )


@bp.get("/ignored")
@staff_required("institution_admin")
def ignored():
    """Complaints that climbed the whole hierarchy and were still ignored.

    The institution's own head sees this first. It is deliberately not a
    league table of officers; it is a list of students still waiting.
    """
    institution = db.session.get(Institution, g.institution_id)
    if not institution:
        return fail("Your account is not linked to an institution.", 400)

    days = max(min(request.args.get("days", 7, type=int), 365), 1)
    rows = ignored_complaints(institution, days=days)

    return ok(
        {
            "days": days,
            "count": len(rows),
            "complaints": [c.to_dict(viewer=g.current_user) for c in rows],
        }
    )


platform_bp = Blueprint("routing_platform", __name__, url_prefix="/api/platform")


@platform_bp.get("/ignored")
@staff_required("platform_admin")
def ignored_across_platform():
    """The same report, across every institution.

    An institution that ignores its students is the one thing the
    platform has to be able to see without being invited in, because by
    definition nobody inside is going to raise it.
    """
    days = max(min(request.args.get("days", 7, type=int), 365), 1)
    summary = []

    for institution in Institution.query.filter_by(is_active=True).all():
        rows = ignored_complaints(institution, days=days)
        if not rows:
            continue
        summary.append(
            {
                "institution": institution.to_dict(),
                "count": len(rows),
                # Ticket numbers only. The platform needs to know an
                # institution is not answering, not to read the
                # complaints of students who never agreed to that.
                "tickets": [c.ticket_number for c in rows[:50]],
                "oldest_escalated_at": min(
                    (c.escalated_at.isoformat() for c in rows if c.escalated_at), default=None
                ),
            }
        )

    summary.sort(key=lambda row: row["count"], reverse=True)
    return ok({"days": days, "institutions": summary})
