"""Complaint endpoints for students and staff."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy.orm import joinedload

from app.extensions import db, limiter
from app.models.complaint import (
    ALLOWED_TRANSITIONS,
    PRIORITIES,
    Complaint,
    Response,
)
from app.models.institution import Department, Institution
from app.models.routing import RoutingRule
from app.models.user import User
from app.routes.auth import fail, ok
from app.security import (
    auth_required,
    can_view_complaint,
    confidential_filter,
    staff_required,
    tenant_query,
)
from app.models.access_log import AccessLog
from app.services.notifications import notify, record_event
from app.services.routing import resolve_destination
from app.services.tickets import generate_ticket_number, normalise_ticket
from app.models.base import utcnow

# The subset of timeline actions a student may see on their own
# complaint. Everything else — private notes, the record of staff reads —
# is the institution's working, not the complaint's progress.
STUDENT_VISIBLE_EVENTS = {
    "created", "status_changed", "assigned", "unassigned",
    "priority_changed", "attached", "attachment_removed",
    "rated", "escalated",
}

bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")

TITLE_MIN, TITLE_MAX = 5, 200
BODY_MIN, BODY_MAX = 20, 5000


def paginate(query, page: int, per_page: int):
    per_page = min(max(per_page, 1), 50)
    result = query.paginate(page=max(page, 1), per_page=per_page, error_out=False)
    return result, {
        "page": result.page,
        "per_page": result.per_page,
        "total_items": result.total,
        "total_pages": result.pages or 1,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }


@bp.post("")
@auth_required()
@limiter.limit("20 per hour")
def create_complaint():
    user = g.current_user

    # Verification gates filing rather than signing in, so an unconfirmed
    # student can still get in and finish the step instead of being left
    # at an error screen with nowhere to go.
    allowed, reason = user.can_file_complaints
    if not allowed:
        return fail(reason, 403, {"verification_required": True})

    payload = request.get_json(silent=True) or {}
    errors = {}

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    category = (payload.get("category") or "").strip()
    priority = (payload.get("priority") or "medium").strip()

    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        errors["title"] = f"Give it a short title ({TITLE_MIN}-{TITLE_MAX} characters)."
    if not BODY_MIN <= len(description) <= BODY_MAX:
        errors["description"] = (
            f"Add a bit more detail - what happened, and when? ({BODY_MIN} characters minimum)"
        )
    if not category:
        errors["category"] = "Choose a category."
    if priority not in PRIORITIES:
        errors["priority"] = "Choose a valid priority."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    institution = db.session.get(Institution, user.institution_id)
    if not institution:
        return fail("Your account is not linked to an institution.", 400)

    # A student who asks to be anonymous and is quietly filed under their
    # own name is worse off than one who was refused, because they will
    # say things they would not have said. If the institution has the
    # setting off, say so and file nothing.
    wants_anonymity = bool(payload.get("is_anonymous"))
    if wants_anonymity and not institution.allow_anonymous:
        return fail(
            "This institution does not accept anonymous complaints. "
            "You can still file this under your name, or raise it with "
            "the platform team if you cannot safely be identified.",
            422,
            {"is_anonymous": "Anonymous complaints are turned off here."},
        )

    # Routing decides the destination; a student is not asked to work out
    # which office owns their problem, which is the thing they came here
    # unable to do. An explicit choice is still honoured, because a
    # student who already knows is usually right.
    department, rule = resolve_destination(institution, category, user)

    if payload.get("department_id"):
        chosen = tenant_query(Department).filter_by(id=payload["department_id"]).first()
        if chosen:
            department = chosen

    complaint = Complaint(
        institution_id=institution.id,
        student_id=user.id,
        department_id=department.id if department else None,
        ticket_number=generate_ticket_number(institution),
        title=title,
        description=description,
        category=category,
        priority=priority,
        is_anonymous=wants_anonymity,
        is_confidential=bool(rule and rule.is_confidential),
        status="submitted",
    )
    complaint.apply_sla(
        institution, department, override_hours=rule.sla_hours if rule else None
    )

    db.session.add(complaint)
    db.session.flush()

    record_event(
        complaint,
        user.id,
        "created",
        to_value="submitted",
        note=f"Routed to {department.name}." if department else "Awaiting routing.",
    )

    where = f" It is with {department.name}." if department else ""
    notify(
        user.id,
        institution.id,
        "Complaint logged",
        f"Your complaint {complaint.ticket_number} has been logged.{where}",
        complaint.id,
        "submitted",
    )
    db.session.commit()

    return ok({"complaint": complaint.to_dict(viewer=user)}, "Your complaint is logged.", 201)


@bp.get("")
@auth_required()
def list_complaints():
    user = g.current_user
    query = tenant_query(Complaint)

    # Students see only their own; staff see everything except the
    # confidential work that is not theirs.
    query = query.filter(confidential_filter(user))

    if user.is_staff:
        if request.args.get("scope") == "mine":
            query = query.filter(Complaint.assigned_to_id == user.id)
        if request.args.get("unassigned") in ("1", "true"):
            query = query.filter(Complaint.assigned_to_id.is_(None))

    for field in ("status", "category", "priority"):
        value = request.args.get(field)
        if value:
            query = query.filter(getattr(Complaint, field) == value)

    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Complaint.title.ilike(like),
                Complaint.ticket_number.ilike(like),
                Complaint.description.ilike(like),
            )
        )

    if request.args.get("overdue") in ("1", "true"):
        query = query.filter(
            Complaint.resolve_due_at < utcnow(),
            Complaint.status.notin_(("resolved", "closed", "declined")),
        )

    # to_dict() reads the department, the student and the assignee for
    # every row, which is three extra queries per complaint on a list of
    # fifty. Loading them alongside turns fifty-one round trips into one.
    query = query.options(
        joinedload(Complaint.department),
        joinedload(Complaint.student),
        joinedload(Complaint.assigned_to),
    ).order_by(Complaint.created_at.desc())

    result, meta = paginate(
        query, request.args.get("page", 1, type=int), request.args.get("per_page", 10, type=int)
    )

    return ok(
        {
            "complaints": [c.to_dict(viewer=user) for c in result.items],
            "pagination": meta,
        }
    )


@bp.get("/<complaint_id>")
@auth_required()
def get_complaint(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        # A complaint belonging to someone else is reported as missing rather
        # than forbidden, so IDs cannot be probed.
        return fail("We could not find that complaint.", 404)

    data = complaint.to_dict(viewer=user, include_responses=True)

    if user.is_staff:
        data["events"] = [e.to_dict() for e in complaint.events]

        # Only staff reads are recorded. A student opening their own
        # complaint is ordinary use, and logging it would bury the
        # entries that matter.
        db.session.add(
            AccessLog(
                institution_id=complaint.institution_id,
                complaint_id=complaint.id,
                actor_id=user.id,
                actor_role=user.role,
                action="viewed",
                ip_address=request.remote_addr,
                user_agent=(request.user_agent.string or "")[:255],
            )
        )
        db.session.commit()
    else:
        # The student gets the same timeline with the internal workings
        # removed. Watching a complaint move — filed, routed,
        # acknowledged, resolved — is the product's whole promise, and
        # until now only staff could see the movement. Private notes and
        # the record of staff reads stay out.
        data["events"] = [
            e.to_dict()
            for e in complaint.events
            if e.action in STUDENT_VISIBLE_EVENTS
        ]

    return ok({"complaint": data})


@bp.post("/<complaint_id>/responses")
@auth_required()
def add_response(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that complaint.", 404)

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if len(message) < 2:
        return fail("Write a message first.", 422, {"message": "Write a message first."})

    # Only staff may mark a message private; a student cannot create one.
    is_internal = bool(payload.get("is_internal")) and user.is_staff

    response = Response(
        institution_id=complaint.institution_id,
        complaint_id=complaint.id,
        author_id=user.id,
        message=message,
        is_internal=is_internal,
    )
    db.session.add(response)

    if not is_internal:
        complaint.response_count += 1
        recipient = complaint.assigned_to_id if user.id == complaint.student_id else complaint.student_id
        if recipient:
            notify(
                recipient,
                complaint.institution_id,
                "New reply",
                f"There is a new reply on {complaint.ticket_number}.",
                complaint.id,
                "response",
            )

    record_event(complaint, user.id, "replied", note="private note" if is_internal else None)
    db.session.commit()

    return ok({"response": response.to_dict()}, "Message sent.", 201)


@bp.put("/<complaint_id>/status")
@staff_required("officer")
def update_status(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()
    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that complaint.", 404)

    payload = request.get_json(silent=True) or {}
    new_status = (payload.get("status") or "").strip()

    if not complaint.can_transition_to(new_status):
        allowed = ", ".join(ALLOWED_TRANSITIONS.get(complaint.status, ())) or "none"
        return fail(
            f"A complaint that is {complaint.status} cannot move to {new_status}. Allowed: {allowed}.",
            409,
        )

    if new_status == "declined" and not (payload.get("reason") or "").strip():
        return fail("Give a reason so the student understands the decision.", 422,
                    {"reason": "Give a reason so the student understands the decision."})

    if new_status == "resolved" and not (payload.get("note") or "").strip():
        return fail("Explain how it was resolved.", 422,
                    {"note": "Explain how it was resolved."})

    previous = complaint.status
    now = utcnow()

    # The check above ran against a value read moments ago. Two officers
    # working the same queue can both pass it and both write, and the
    # second silently overwrites the first — a complaint resolved by one
    # and declined by the other ends as whichever committed last.
    #
    # Re-asserting the old status inside the UPDATE closes that window:
    # the database matches zero rows if anything moved in between, and
    # the loser is told rather than ignored.
    changed = (
        db.session.query(Complaint)
        .filter(Complaint.id == complaint.id, Complaint.status == previous)
        .update({Complaint.status: new_status}, synchronize_session=False)
    )

    if not changed:
        db.session.rollback()
        return fail(
            "Somebody else updated this complaint a moment ago. Reload it and try again.",
            409,
        )

    complaint.status = new_status

    if new_status == "acknowledged":
        complaint.acknowledged_at = now
    elif new_status == "resolved":
        complaint.resolved_at = now
        complaint.resolution_note = (payload.get("note") or "").strip()
    elif new_status == "declined":
        complaint.decline_reason = (payload.get("reason") or "").strip()
    elif new_status == "closed":
        complaint.closed_at = now

    record_event(complaint, user.id, "status_changed", previous, new_status)
    notify(
        complaint.student_id,
        complaint.institution_id,
        "Complaint updated",
        f"{complaint.ticket_number} is now {new_status.replace('_', ' ')}.",
        complaint.id,
    )
    db.session.commit()

    return ok({"complaint": complaint.to_dict(viewer=user)}, "Status updated.")


@bp.put("/<complaint_id>/assign")
@staff_required("dept_head")
def assign(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()
    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that complaint.", 404)

    payload = request.get_json(silent=True) or {}
    assignee_id = payload.get("assigned_to_id")

    if assignee_id:
        assignee = tenant_query(User).filter_by(id=assignee_id).first()
        if not assignee or not assignee.is_staff:
            return fail("Choose a member of staff.", 422)
        if complaint.is_confidential and not can_view_complaint(assignee, complaint):
            return fail(
                "This complaint is confidential and can only be given to the handling unit.", 422
            )
        previous = complaint.assigned_to.full_name if complaint.assigned_to else None
        complaint.assigned_to_id = assignee.id
        record_event(complaint, user.id, "assigned", previous, assignee.full_name)
        notify(
            assignee.id,
            complaint.institution_id,
            "Complaint assigned to you",
            f"You now own {complaint.ticket_number}.",
            complaint.id,
            "assignment",
        )
    else:
        complaint.assigned_to_id = None
        record_event(complaint, user.id, "unassigned")

    db.session.commit()
    return ok({"complaint": complaint.to_dict(viewer=user)}, "Assignment updated.")


@bp.put("/<complaint_id>/priority")
@staff_required("officer")
def update_priority(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()
    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that complaint.", 404)

    priority = (request.get_json(silent=True) or {}).get("priority")
    if priority not in PRIORITIES:
        return fail("Choose a valid priority.", 422)

    previous = complaint.priority
    complaint.priority = priority
    institution = db.session.get(Institution, complaint.institution_id)

    rule = RoutingRule.query.filter_by(
        institution_id=complaint.institution_id, category=complaint.category
    ).first()
    complaint.apply_sla(
        institution, complaint.department, override_hours=rule.sla_hours if rule else None
    )
    record_event(complaint, user.id, "priority_changed", previous, priority)
    db.session.commit()

    return ok({"complaint": complaint.to_dict(viewer=user)}, "Priority updated.")


@bp.post("/<complaint_id>/rate")
@auth_required()
def rate(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or complaint.student_id != user.id:
        return fail("We could not find that complaint.", 404)
    if complaint.status not in ("resolved", "closed"):
        return fail("You can rate a complaint once it has been resolved.", 409)

    rating = (request.get_json(silent=True) or {}).get("rating")
    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return fail("Give a rating between 1 and 5.", 422)

    complaint.satisfaction_rating = rating
    record_event(complaint, user.id, "rated", to_value=str(rating))
    db.session.commit()
    return ok(message="Thank you for the feedback.")


# Public lookup. No authentication: a ticket number is the only credential,
# and the payload deliberately excludes personal data.
public_bp = Blueprint("public", __name__, url_prefix="/api/public")


@public_bp.get("/track/<ticket>")
@limiter.limit("30 per hour")
def track(ticket):
    normalised = normalise_ticket(ticket)
    if len(normalised) < 6:
        return fail("Check the ticket number and try again.", 400)

    # Compare without hyphens so users may type the number either way.
    match = None
    for complaint in Complaint.query.filter(
        Complaint.ticket_number.ilike(f"{normalised[:3]}%")
    ).limit(200):
        if normalise_ticket(complaint.ticket_number) == normalised:
            match = complaint
            break

    if not match:
        return fail("We could not find a complaint with that ticket number.", 404)

    return ok({"complaint": match.to_public_dict()})


@public_bp.get("/institutions")
def institutions():
    rows = Institution.query.filter_by(is_active=True).order_by(Institution.name).all()
    return ok({"institutions": [i.to_dict() for i in rows]})
