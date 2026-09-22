"""HTTP task trigger.

This endpoint runs privileged work with no signed-in user, so the access
check is the whole of its security.
"""

from datetime import timedelta

from app.extensions import db
from app.models.base import utcnow
from app.models.complaint import Complaint
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Transcript request not processed",
    "description": "I applied for my transcript in July and have had no response since then.",
    "category": "transcript",
    "priority": "medium",
}

TOKEN = "a-long-random-task-secret"


def configure(app):
    app.config["TASK_TOKEN"] = TOKEN


def headers(token=TOKEN):
    return {"X-Task-Token": token}


# -- access -----------------------------------------------------------


def test_the_endpoint_does_not_exist_without_a_configured_secret(client, app):
    """A deployment that forgets the secret must not get an open trigger."""
    app.config["TASK_TOKEN"] = None

    response = client.post("/api/tasks/escalate", headers=headers())

    assert response.status_code == 404


def test_a_missing_token_is_refused(client, app):
    configure(app)

    assert client.post("/api/tasks/escalate").status_code == 404


def test_a_wrong_token_is_refused(client, app):
    configure(app)

    assert client.post("/api/tasks/escalate", headers=headers("wrong")).status_code == 404


def test_refusal_looks_like_absence(client, app):
    """404 rather than 401, so probing cannot confirm the route exists."""
    configure(app)

    response = client.post("/api/tasks/escalate", headers=headers("wrong"))

    assert response.status_code == 404
    assert "task" not in response.get_json()


def test_a_signed_in_student_cannot_trigger_work(client, alpha, app):
    """Being a user is not authorisation for this."""
    configure(app)
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    response = client.post("/api/tasks/escalate", headers=auth(token))

    assert response.status_code == 404


def test_only_known_tasks_run(client, app):
    """The name must not be able to reach arbitrary code."""
    configure(app)

    response = client.post("/api/tasks/rm-rf", headers=headers())

    assert response.status_code == 400


# -- behaviour --------------------------------------------------------


def test_escalation_runs_over_http(client, alpha, app, db):
    configure(app)
    make_user(alpha, "student@test.ng")
    make_user(alpha, "head@test.ng", role="dept_head")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    response = client.post("/api/tasks/escalate", headers=headers())

    assert response.status_code == 200
    assert response.get_json()["summary"]["escalated"] == 1
    assert db.session.get(Complaint, complaint_id).escalated_at is not None


def test_running_twice_escalates_once(client, alpha, app, db):
    """A delayed scheduler may fire late or twice."""
    configure(app)
    make_user(alpha, "student@test.ng")
    student = login(client, "student@test.ng")

    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    first = client.post("/api/tasks/escalate", headers=headers())
    second = client.post("/api/tasks/escalate", headers=headers())

    assert first.get_json()["summary"]["escalated"] == 1
    assert second.get_json()["summary"]["escalated"] == 0


def test_delivery_runs_over_http(client, app):
    configure(app)

    response = client.post("/api/tasks/send-queue", headers=headers())

    assert response.status_code == 200
    assert "considered" in response.get_json()["summary"]


def test_purge_runs_over_http(client, app):
    configure(app)

    response = client.post("/api/tasks/purge-expired", headers=headers())

    assert response.status_code == 200
    assert "complaints_purged" in response.get_json()["summary"]


def test_every_job_runs_in_one_request(client, app):
    """Separate calls would each pay the wake-up cost on a sleeping host."""
    configure(app)

    response = client.post("/api/tasks/all", headers=headers())

    assert response.status_code == 200
    results = response.get_json()["results"]
    assert set(results) == {"escalate", "send-queue", "purge-expired", "report-ignored"}


def test_one_failing_job_does_not_stop_the_others(client, app, monkeypatch):
    """Delivery failing must not prevent an overdue complaint escalating."""
    configure(app)

    from app.services import delivery

    def explode(*_args, **_kwargs):
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr(delivery, "process_queue", explode)

    response = client.post("/api/tasks/all", headers=headers())
    results = response.get_json()["results"]

    assert response.status_code == 200
    assert "error" in results["send-queue"]
    assert "escalated" in results["escalate"]


def test_a_failure_is_reported_rather_than_raised(client, app, monkeypatch):
    configure(app)

    from app.services import sla

    monkeypatch.setattr(
        sla, "run_escalation_sweep", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    response = client.post("/api/tasks/escalate", headers=headers())

    assert response.status_code == 500
    assert response.get_json()["success"] is False


# -- free tier configuration ------------------------------------------


def test_production_allows_a_single_worker_without_redis(monkeypatch):
    """The free tier depends on this pairing being permitted."""
    import importlib

    import app.config

    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "memory://",
        "WEB_CONCURRENCY": "1",
        "CORS_ORIGINS": "https://uni-complaints.vercel.app",
        "TRUSTED_PROXIES": "1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)

    config = importlib.reload(app.config)
    assert config.ProductionConfig() is not None


def test_production_still_refuses_two_workers_without_redis(monkeypatch):
    import importlib

    import pytest

    import app.config

    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "memory://",
        "WEB_CONCURRENCY": "2",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)

    config = importlib.reload(app.config)
    with pytest.raises(RuntimeError, match="shared storage"):
        config.ProductionConfig()
