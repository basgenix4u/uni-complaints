"""Data subject rights endpoints."""

import json

from flask import Blueprint, Response, g, request

from app.extensions import db, limiter
from app.models.access_log import AccessLog
from app.models.base import utcnow
from app.models.complaint import Complaint
from app.models.institution import Institution
from app.models.user import User
from app.routes.auth import fail, ok
from app.security import auth_required, staff_required, tenant_query
from app.services.privacy import erase_user, export_user_data, purge_expired_data

bp = Blueprint("privacy", __name__, url_prefix="/api/privacy")


@bp.get("/my-data")
@auth_required()
@limiter.limit("5 per hour")
def download_my_data():
    """Everything held about the signed-in person.

    Served as a file rather than a JSON body so it can be kept, which is
    the point of a portability right.
    """
    payload = export_user_data(g.current_user)
    stamp = utcnow().strftime("%Y-%m-%d")

    return Response(
        json.dumps(payload, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="my-data-{stamp}.json"',
            "Cache-Control": "no-store",
        },
    )


@bp.post("/erase-my-account")
@auth_required()
@limiter.limit("3 per day")
def erase_my_account():
    """Erase the signed-in person's data.

    The password is required again because this cannot be undone, and a
    borrowed unlocked session should not be enough to destroy someone's
    record of a complaint.
    """
    user = g.current_user
    payload = request.get_json(silent=True) or {}

    if not user.check_password(payload.get("password") or ""):
        return fail("Enter your password to confirm.", 401)

    if (payload.get("confirm") or "").strip().upper() != "ERASE":
        return fail('Type ERASE to confirm.', 422, {"confirm": 'Type ERASE to confirm.'})

    if user.role != "student":
        return fail(
            "Staff accounts are erased by an administrator, so that handover of open "
            "work can be arranged first.",
            409,
        )

    try:
        summary = erase_user(user)
    except ValueError as error:
        return fail(str(error), 409)

    return ok(
        {"summary": summary},
        "Your personal data has been erased. Complaints you filed remain as "
        "anonymous records of what the institution decided.",
    )


@bp.post("/users/<user_id>/erase")
@staff_required("institution_admin")
def erase_on_request(user_id):
    """Erase a person's data on their written request.

    Institutions receive these on paper as often as online, so an
    administrator needs to be able to act on one.
    """
    actor = g.current_user
    user = tenant_query(User).filter(User.id == user_id).first()

    if not user:
        return fail("We could not find that person.", 404)
    if user.id == actor.id:
        return fail("Use the account page to erase your own data.", 409)
    if user.erased_at:
        return fail("That account has already been erased.", 409)

    reason = (request.get_json(silent=True) or {}).get("reason") or "requested in writing"

    try:
        summary = erase_user(user, reason=f"{reason} (actioned by {actor.full_name})")
    except ValueError as error:
        return fail(str(error), 409)

    return ok({"summary": summary}, "That person's data has been erased.")


@bp.get("/complaints/<complaint_id>/access-log")
@staff_required("institution_admin")
def complaint_access_log(complaint_id):
    """Who has opened a complaint.

    Restricted to administrators: the log is itself sensitive, since it
    shows which officers took an interest in a case.
    """
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()
    if not complaint:
        return fail("We could not find that complaint.", 404)

    entries = (
        AccessLog.query.filter_by(complaint_id=complaint.id)
        .order_by(AccessLog.created_at.desc())
        .limit(200)
        .all()
    )

    return ok({"access_log": [entry.to_dict() for entry in entries]})


@bp.post("/retention/purge")
@staff_required("institution_admin")
def run_purge():
    """Apply the retention period now.

    Also runs on a schedule; exposed so an administrator can see the
    effect of a setting immediately rather than waiting a day.
    """
    institution = db.session.get(Institution, g.current_user.institution_id)
    if not institution:
        return fail("We could not find your institution.", 404)

    return ok({"summary": purge_expired_data(institution)}, "Retention applied.")
