"""Authorisation helpers.

Role checks and tenant scoping live here rather than in individual routes so
that a new endpoint cannot accidentally ship without them.
"""

from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.models.user import ROLE_RANK, User


def _deny(message: str, status: int):
    return jsonify({"success": False, "message": message}), status


def load_current_user():
    """Resolve the JWT subject to a live user row.

    The database is consulted on every request so that a deactivated account
    stops working immediately instead of when its token expires.
    """
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return User.query.filter_by(id=user_id, is_active=True).first()


def auth_required(minimum_role: str = "student"):
    """Require a valid token and a sufficient role.

    Also pins `g.institution_id` from the token, which every tenant-scoped
    query derives from.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            user = load_current_user()
            if not user:
                return _deny("Your session is no longer valid. Please sign in again.", 401)

            if ROLE_RANK.get(user.role, -1) < ROLE_RANK.get(minimum_role, 99):
                return _deny("You do not have permission to do that.", 403)

            claims = get_jwt()
            token_institution = claims.get("institution_id")

            # The token must still agree with the stored record; a user moved
            # between institutions cannot keep using an old token.
            if user.role != "platform_admin" and token_institution != user.institution_id:
                return _deny("Your session is no longer valid. Please sign in again.", 401)

            g.current_user = user
            g.institution_id = user.institution_id
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def staff_required(minimum_role: str = "officer"):
    return auth_required(minimum_role)


def tenant_query(model):
    """Return a query pre-filtered to the caller's institution.

    Routes must use this instead of `Model.query` for tenant-owned tables.
    A platform administrator acting outside a tenant sees everything.
    """
    query = model.query
    institution_id = getattr(g, "institution_id", None)
    if institution_id is None:
        user = getattr(g, "current_user", None)
        if user and user.role == "platform_admin":
            return query
        # Fail closed rather than returning unscoped rows.
        return query.filter(db_false())
    return query.filter(model.institution_id == institution_id)


def db_false():
    from sqlalchemy import false

    return false()


def can_view_complaint(user, complaint) -> bool:
    if user.institution_id != complaint.institution_id and user.role != "platform_admin":
        return False

    if not user.is_staff:
        return complaint.student_id == user.id

    if not getattr(complaint, "is_confidential", False):
        return True

    # A harassment report naming a lecturer must not be readable by that
    # lecturer's own colleagues, so a confidential complaint is limited to
    # the handling unit, whoever owns it, and the institution's officers.
    if user.role in ("institution_admin", "platform_admin"):
        return True
    if complaint.assigned_to_id == user.id:
        return True
    return bool(complaint.department_id) and user.department_id == complaint.department_id


def visible_complaints():
    """Complaints the caller may read, scoped to their institution.

    Every list, count, chart and export goes through this. Filtering
    after the fact would still leak a confidential report through a
    total, and a total is enough to tell a department that one of its
    own has been reported.
    """
    from app.models.complaint import Complaint

    return tenant_query(Complaint).filter(confidential_filter(g.current_user))


def confidential_filter(user):
    """Restrict a complaint query to what this person may read.

    Applied to every list and aggregate rather than filtering after the
    fact, so a confidential report cannot leak through a count, a chart
    or an export even where the rows themselves are never rendered.
    """
    from sqlalchemy import or_

    from app.models.complaint import Complaint

    if not user.is_staff:
        return Complaint.student_id == user.id
    if user.role in ("institution_admin", "platform_admin"):
        return true_()

    permitted = [Complaint.is_confidential.is_(False), Complaint.assigned_to_id == user.id]
    if user.department_id:
        permitted.append(Complaint.department_id == user.department_id)

    return or_(*permitted)


def true_():
    from sqlalchemy import true

    return true()


def can_modify_complaint(user, complaint) -> bool:
    if not user.is_staff:
        return False
    if user.role == "platform_admin":
        return True
    return user.institution_id == complaint.institution_id
