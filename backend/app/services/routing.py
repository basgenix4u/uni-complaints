"""Deciding where a complaint goes, and who is told when it is ignored."""

from app.extensions import db
from app.models.academic import StudentRecord
from app.models.institution import Department
from app.models.routing import DEFAULT_ROUTING, DEFAULT_UNITS, RoutingRule


def resolve_destination(institution, category: str, student):
    """Work out which unit should answer a complaint.

    Returns (department, rule). Either may be None: an institution that
    has not finished configuring routing still has to be able to accept
    complaints, so an unrouted one is left unassigned rather than
    rejected.
    """
    rule = RoutingRule.query.filter_by(
        institution_id=institution.id, category=category, is_active=True
    ).first()

    if rule is None:
        return None, None

    if rule.target_type == "unit":
        return rule.department, rule

    # An academic matter belongs to the complainant's own department, so
    # the destination depends on who is filing rather than on the
    # category alone.
    record = StudentRecord.query.filter_by(
        institution_id=institution.id, claimed_by_user_id=student.id
    ).first()

    if record and record.academic_department:
        # The academic department is not an administrative unit, so it is
        # matched to one by name where the institution has created it.
        unit = Department.query.filter_by(
            institution_id=institution.id, slug=record.academic_department.slug
        ).first()
        if unit:
            return unit, rule

    # Fall back to the escalation target rather than leaving it nowhere.
    return rule.escalates_to, rule


def seed_units(institution) -> int:
    """Create the units most institutions have.

    Offered during onboarding so an administrator reviews a list instead
    of typing one from nothing.
    """
    created = 0
    for name, slug, description in DEFAULT_UNITS:
        exists = Department.query.filter_by(
            institution_id=institution.id, slug=slug
        ).first()
        if exists:
            continue
        db.session.add(
            Department(
                institution_id=institution.id,
                name=name,
                slug=slug,
                description=description,
            )
        )
        created += 1

    db.session.flush()
    return created


def seed_routing(institution) -> int:
    """Create a draft routing table.

    Every institution will disagree with part of this. Correcting a draft
    is far easier than building the table from scratch, and an
    institution that never reviews it still has working routing rather
    than none.
    """
    units = {
        d.slug: d
        for d in Department.query.filter_by(institution_id=institution.id).all()
    }

    created = 0
    for category, unit_slug, target_type, escalate_slug, confidential in DEFAULT_ROUTING:
        exists = RoutingRule.query.filter_by(
            institution_id=institution.id, category=category
        ).first()
        if exists:
            continue

        target = units.get(unit_slug) if unit_slug else None
        escalates = units.get(escalate_slug) if escalate_slug else None

        db.session.add(
            RoutingRule(
                institution_id=institution.id,
                category=category,
                target_type=target_type,
                department_id=target.id if target else None,
                escalates_to_department_id=escalates.id if escalates else None,
                is_confidential=confidential,
            )
        )
        created += 1

    db.session.commit()
    return created


def ignored_complaints(institution, days: int = 7):
    """Complaints nobody has acted on.

    Escalation already raises a complaint past its deadline to the unit
    heads. This is the layer above: work that has been escalated and is
    still sitting there, which is what the institution head needs to see.
    """
    from datetime import timedelta

    from app.models.base import as_aware, utcnow
    from app.models.complaint import Complaint

    cutoff = utcnow() - timedelta(days=days)

    rows = (
        Complaint.query.filter(
            Complaint.institution_id == institution.id,
            Complaint.status.notin_(("resolved", "closed", "declined")),
            Complaint.escalated_at.isnot(None),
        )
        .order_by(Complaint.resolve_due_at)
        .limit(500)
        .all()
    )

    return [c for c in rows if as_aware(c.escalated_at) and as_aware(c.escalated_at) < cutoff]
