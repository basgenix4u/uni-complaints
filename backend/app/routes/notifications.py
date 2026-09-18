"""Notification endpoints."""

from flask import Blueprint, g, request

from app.extensions import db
from app.models.complaint import Notification
from app.routes.auth import fail, ok
from app.security import auth_required, tenant_query

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _mine():
    return tenant_query(Notification).filter(Notification.user_id == g.current_user.id)


@bp.get("")
@auth_required()
def list_notifications():
    query = _mine()

    if request.args.get("unread") in ("1", "true"):
        query = query.filter(Notification.is_read.is_(False))

    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 50)
    result = query.order_by(Notification.created_at.desc()).paginate(
        page=max(request.args.get("page", 1, type=int), 1), per_page=per_page, error_out=False
    )

    return ok(
        {
            "notifications": [n.to_dict() for n in result.items],
            "unread_count": _mine().filter(Notification.is_read.is_(False)).count(),
            "pagination": {
                "page": result.page,
                "per_page": result.per_page,
                "total_items": result.total,
                "total_pages": result.pages or 1,
                "has_next": result.has_next,
                "has_prev": result.has_prev,
            },
        }
    )


@bp.get("/unread-count")
@auth_required()
def unread_count():
    """Polled by the navigation bar, so kept as a single count query."""
    return ok({"unread_count": _mine().filter(Notification.is_read.is_(False)).count()})


@bp.put("/<notification_id>/read")
@auth_required()
def mark_read(notification_id):
    notification = _mine().filter(Notification.id == notification_id).first()
    if not notification:
        return fail("We could not find that notification.", 404)

    notification.is_read = True
    db.session.commit()
    return ok({"notification": notification.to_dict()}, "Marked as read.")


@bp.put("/read-all")
@auth_required()
def mark_all_read():
    updated = _mine().filter(Notification.is_read.is_(False)).update(
        {Notification.is_read: True}, synchronize_session=False
    )
    db.session.commit()
    return ok({"updated": updated}, "All notifications marked as read.")
