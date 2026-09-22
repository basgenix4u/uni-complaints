"""The public institution directory and the request to add one.

Unauthenticated by necessity: a person has to find their institution
before they can have an account anywhere.
"""

from flask import Blueprint, request

from app.extensions import limiter
from app.models.institution import Institution
from app.routes.auth import EMAIL_RE, fail, ok
from app.security import staff_required
from app.services.directory import demand, record_interest, search

bp = Blueprint("directory", __name__, url_prefix="/api/directory")


@bp.get("/institutions")
# A type-ahead sends a request every time the student stops typing, so a
# single careful sign-up can spend a dozen of these. Sixty an hour was
# set when the directory held a handful of institutions and would now
# lock people out mid-search. The endpoint is a read of public data.
@limiter.limit("300 per hour")
def list_institutions():
    """Search the directory.

    Institutions that have not signed up are included and flagged. A
    student needs to know we have heard of their university even when
    they cannot yet use it, because that answer leads somewhere and
    "not found" does not.
    """
    rows = search(
        query=request.args.get("q", ""),
        state=request.args.get("state", ""),
        kind=request.args.get("kind", ""),
        onboarded_only=request.args.get("onboarded") in ("1", "true"),
    )

    return ok(
        {
            "institutions": [i.to_directory_dict() for i in rows],
            "count": len(rows),
        }
    )


@bp.get("/institutions/<slug>")
@limiter.limit("60 per hour")
def get_institution(slug):
    """One institution, for the sign-up form.

    The form needs the verification mode to know what to ask for: a
    matriculation number is worth requesting where it will be checked
    against a register, and is a pointless obstacle where it will not.
    """
    institution = Institution.query.filter_by(slug=slug.lower(), is_active=True).first()
    if not institution:
        return fail("We could not find that institution.", 404)

    return ok({"institution": institution.to_directory_dict()})


@bp.get("/states")
@limiter.limit("60 per hour")
def states():
    """States that have at least one institution, for the filter."""
    rows = (
        Institution.query.with_entities(Institution.state)
        .filter(Institution.is_active.is_(True), Institution.state.isnot(None))
        .distinct()
        .order_by(Institution.state)
        .all()
    )
    return ok({"states": [row[0] for row in rows if row[0]]})


@bp.post("/interest")
@limiter.limit("10 per hour")
def register_interest():
    """Ask for an institution to be added.

    Always reports success, whether or not the row was new. Saying "you
    already asked" would confirm which addresses are on file to anyone
    who cared to probe.
    """
    payload = request.get_json(silent=True) or {}

    name = (payload.get("institution_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    errors = {}

    if len(name) < 3:
        errors["institution_name"] = "Enter the name of your institution."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address so we can tell you when it is ready."

    if errors:
        return fail("Please check the highlighted fields.", 422, errors)

    known = None
    if payload.get("institution_slug"):
        known = Institution.query.filter_by(
            slug=str(payload["institution_slug"]).lower()
        ).first()

    record_interest(name, email, (payload.get("full_name") or "").strip(), known)

    return ok(
        message=(
            "Thank you. We will let you know as soon as your institution is using Resolve, "
            "and the more people who ask, the sooner that tends to be."
        )
    )


platform_bp = Blueprint("directory_platform", __name__, url_prefix="/api/platform")


@platform_bp.get("/demand")
@staff_required("platform_admin")
def institution_demand():
    """Which institutions are being asked for, most wanted first.

    This is the list that decides who to approach next.
    """
    return ok({"demand": demand()})
