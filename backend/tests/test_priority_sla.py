"""Priority-based acknowledgement, resolution and escalation windows."""

from datetime import datetime, timezone

from app.extensions import db
from app.models.routing import PrioritySlaPolicy
from app.services.sla import deadline_for
from tests.conftest import auth, login, make_user

MATRIX = [
    {"priority": "low", "acknowledge_hours": 48, "resolve_hours": 120, "escalation_step_hours": 48},
    {"priority": "medium", "acknowledge_hours": 24, "resolve_hours": 72, "escalation_step_hours": 24},
    {"priority": "high", "acknowledge_hours": 4, "resolve_hours": 24, "escalation_step_hours": 8},
    {"priority": "urgent", "acknowledge_hours": 2, "resolve_hours": 8, "escalation_step_hours": 2},
]


def administrator(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    return login(client, "admin@test.ng")


def test_the_matrix_is_saved_atomically(client, alpha):
    token = administrator(client, alpha)

    response = client.put(
        "/api/routing/sla-policies",
        headers=auth(token),
        json={"policies": MATRIX},
    )

    assert response.status_code == 200
    saved = response.get_json()["data"]["policies"]
    assert {p["priority"] for p in saved} == {"low", "medium", "high", "urgent"}
    assert all(p["is_active"] for p in saved)


def test_the_defaults_are_suggestions_not_active_policy(client, alpha):
    token = administrator(client, alpha)

    body = client.get("/api/routing/sla-policies", headers=auth(token)).get_json()["data"]

    assert len(body["policies"]) == 4
    assert all(p["is_active"] is False for p in body["policies"])
    assert PrioritySlaPolicy.query.count() == 0


def test_every_priority_is_required(client, alpha):
    token = administrator(client, alpha)

    response = client.put(
        "/api/routing/sla-policies",
        headers=auth(token),
        json={"policies": MATRIX[:-1]},
    )

    assert response.status_code == 422
    assert PrioritySlaPolicy.query.count() == 0


def test_acknowledgement_cannot_fall_after_resolution(client, alpha):
    token = administrator(client, alpha)
    broken = [dict(p) for p in MATRIX]
    broken[0]["acknowledge_hours"] = 121

    response = client.put(
        "/api/routing/sla-policies",
        headers=auth(token),
        json={"policies": broken},
    )

    assert response.status_code == 422
    assert "low.acknowledge_hours" in response.get_json()["errors"]


def test_a_student_cannot_change_the_institution_policy(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    response = client.put(
        "/api/routing/sla-policies",
        headers=auth(token),
        json={"policies": MATRIX},
    )

    assert response.status_code == 403


def test_an_urgent_case_has_the_promised_working_hour_deadlines(app, alpha):
    policy = PrioritySlaPolicy(
        institution_id=alpha.id,
        priority="urgent",
        acknowledge_hours=2,
        resolve_hours=8,
        escalation_step_hours=2,
        is_active=True,
    )
    db.session.add(policy)
    db.session.commit()

    # Monday 08:00 WAT (07:00 UTC), safely inside working hours.
    start = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
    acknowledge, resolve = deadline_for(alpha, None, "urgent", start)

    assert acknowledge == datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc)
    assert resolve == datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)


def test_policy_wins_over_the_old_category_override(app, alpha):
    db.session.add(
        PrioritySlaPolicy(
            institution_id=alpha.id,
            priority="high",
            acknowledge_hours=4,
            resolve_hours=24,
            escalation_step_hours=8,
            is_active=True,
        )
    )
    db.session.commit()
    start = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)

    _, resolve = deadline_for(alpha, None, "high", start, override_hours=200)

    # 24 working hours, not 200 * the old high-priority factor.
    assert resolve == datetime(2026, 9, 23, 13, 0, tzinfo=timezone.utc)


def test_an_institution_without_a_matrix_keeps_the_previous_behaviour(app, alpha):
    start = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)

    acknowledge, resolve = deadline_for(alpha, None, "high", start, override_hours=24)

    assert acknowledge == datetime(2026, 9, 23, 13, 0, tzinfo=timezone.utc)
    # Old behaviour: 24 category hours × high factor 0.5 = 12 working hours.
    assert resolve == datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)


def test_each_escalation_rung_uses_the_priority_window(monkeypatch, alpha):
    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.models.institution import Department
    from app.services.sla import _escalate_one
    from tests.conftest import make_user

    unit = Department.query.filter_by(institution_id=alpha.id).first()
    student = make_user(alpha, "student@test.ng")
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = unit.id
    db.session.add(
        PrioritySlaPolicy(
            institution_id=alpha.id,
            priority="urgent",
            acknowledge_hours=2,
            resolve_hours=8,
            escalation_step_hours=2,
            is_active=True,
        )
    )
    complaint = Complaint(
        institution_id=alpha.id,
        student_id=student.id,
        department_id=unit.id,
        ticket_number="AAA-TEST-0001",
        title="Safety light is not working",
        description="The light along the route used at night is not working.",
        category="security",
        priority="urgent",
        status="submitted",
    )
    db.session.add(complaint)
    db.session.commit()

    called = {}
    sentinel = utcnow()

    def capture(start, hours, open_hour, close_hour, holidays=None):
        called["hours"] = hours
        return sentinel

    monkeypatch.setattr("app.services.sla.add_working_hours", capture)

    assert _escalate_one(complaint, utcnow()) is True
    assert called["hours"] == 2
    assert complaint.next_escalation_at == sentinel
