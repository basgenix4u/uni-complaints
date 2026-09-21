"""Scheduled work, triggered over HTTP.

Hosting tiers that include a scheduler cost money. The same jobs can be
driven by any external timer instead, which keeps a small deployment free.

This endpoint exists so something outside the application can say "run the
escalation sweep now". It is not a convenience: on a host that sleeps an
idle service, the request also wakes the process, so the call both starts
the container and does the work.

Access is a shared secret compared in constant time. Without a configured
secret the endpoint returns 404 and does not exist at all, so a deployment
that forgets to set one is not left with an open trigger.
"""

import hmac

import structlog
from flask import Blueprint, current_app, jsonify, request

from app.models.base import utcnow

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

# Only these may be triggered. A name that is not listed is rejected
# before anything is imported, so the endpoint cannot be used to reach
# arbitrary code.
TASKS = ("escalate", "send-queue", "purge-expired")


def _authorised() -> bool:
    expected = current_app.config.get("TASK_TOKEN")
    if not expected:
        return False

    supplied = request.headers.get("X-Task-Token", "")
    # Constant time, so the comparison does not leak the secret one
    # character at a time through response timing.
    return hmac.compare_digest(supplied, expected)


def _run(name: str) -> dict:
    if name == "escalate":
        from app.services.sla import run_escalation_sweep

        return run_escalation_sweep()

    if name == "send-queue":
        from app.services.delivery import process_queue

        return process_queue()

    from app.models.institution import Institution
    from app.services.privacy import purge_expired_data

    totals = {"complaints_purged": 0, "attachments_destroyed": 0}
    for institution in Institution.query.filter(Institution.retention_months > 0).all():
        result = purge_expired_data(institution)
        totals["complaints_purged"] += result.get("complaints_purged", 0)
        totals["attachments_destroyed"] += result.get("attachments_destroyed", 0)
    return totals


@bp.post("/<task_name>")
def run_task(task_name):
    """Run one scheduled job.

    Returns 404 rather than 401 for an unknown caller, so probing cannot
    confirm the endpoint exists.
    """
    if not _authorised():
        return jsonify({"success": False, "message": "Not found."}), 404

    if task_name not in TASKS:
        return jsonify({"success": False, "message": "Unknown task."}), 400

    logger = structlog.get_logger()
    started = utcnow()

    try:
        summary = _run(task_name)
    except Exception as error:  # noqa: BLE001 - reported, never raised to the caller
        logger.exception("scheduled_task_failed", task=task_name)
        return (
            jsonify({"success": False, "task": task_name, "message": str(error)[:200]}),
            500,
        )

    duration = round((utcnow() - started).total_seconds(), 2)
    logger.info("scheduled_task", task=task_name, duration_seconds=duration, **summary)

    return jsonify(
        {"success": True, "task": task_name, "duration_seconds": duration, "summary": summary}
    )


@bp.post("/all")
def run_all():
    """Run every job in one request.

    On a sleeping host each separate call pays the wake-up cost again, so
    a single request that does everything is both faster and cheaper.
    """
    if not _authorised():
        return jsonify({"success": False, "message": "Not found."}), 404

    logger = structlog.get_logger()
    results = {}

    for name in TASKS:
        try:
            results[name] = _run(name)
        except Exception as error:  # noqa: BLE001
            logger.exception("scheduled_task_failed", task=name)
            # One failing job must not stop the others. Delivery failing
            # should never prevent an overdue complaint escalating.
            results[name] = {"error": str(error)[:200]}

    return jsonify({"success": True, "results": results})
