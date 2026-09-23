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
from app.models.complaint import PRIORITIES
from app.models.routing import TARGET_TYPES, PriorityPolicy, RoutingRule
from app.routes.auth import fail, ok
from app.security import staff_required, tenant_query
from app.services.routing import (
    ignored_complaints,
    seed_priority_policies,
    seed_routing,
    seed_units,
)

bp = Blueprint("routing", __name__, url_prefix="/api/routing")

# Beyond this a deadline is no longer a deadline. Three months of working
# hours is already far longer than any complaint should take.
MAX_SLA_HOURS = 2000


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


@bp.get("/priority-policies")
@staff_required("institution_admin")
def list_priority_policies():
    """The visible SLA and escalation behaviour for all four priorities."""
    rows = tenant_query(PriorityPolicy).order_by(PriorityPolicy.acknowledge_hours).all()
    return ok({"policies": [row.to_dict() for row in rows]})


@bp.put("/priority-policies/<priority>")
@staff_required("institution_admin")
def upsert_priority_policy(priority):
    """Change one priority without affecting any other tenant."""
    priority = priority.strip().lower()
    if priority not in PRIORITIES:
        return fail("Choose low, medium, high or urgent.", 422)

    payload = request.get_json(silent=True) or {}
    errors = {}

    def integer(field, minimum=1, maximum=MAX_SLA_HOURS):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            errors[field] = f"Give a whole number between {minimum} and {maximum}."
            return None
        return value

    ack = integer("acknowledge_hours")
    step = integer("escalation_step_hours")
    reminder = integer("reminder_hours_before_due", minimum=0)

    factor = payload.get("resolution_factor")
    if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not 0.05 <= factor <= 10:
        errors["resolution_factor"] = "Give a multiplier between 0.05 and 10."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    policy = tenant_query(PriorityPolicy).filter_by(priority=priority).first()
    if policy is None:
        policy = PriorityPolicy(institution_id=g.institution_id, priority=priority)
        db.session.add(policy)

    policy.acknowledge_hours = ack
    policy.resolution_factor = float(factor)
    policy.escalation_step_hours = step
    policy.reminder_hours_before_due = reminder
    policy.is_active = payload.get("is_active", True) is not False
    db.session.commit()

    return ok({"policy": policy.to_dict()}, "Priority policy updated.")


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
    db.session.flush()
    rules = seed_routing(institution)
    policies = seed_priority_policies(institution)
    db.session.commit()

    return ok(
        {
            "units_created": units,
            "rules_created": rules,
            "priority_policies_created": policies,
        },
        f"Added {units} units, {rules} routing rules and {policies} priority policies.",
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
