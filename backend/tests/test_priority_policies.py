"""Priority-based acknowledgement, reminders and escalation windows."""

from datetime import datetime, timezone

from app.extensions import db
from app.models.routing import PriorityPolicy
from app.services.routing import seed_priority_policies
from app.services.sla import add_working_hours, deadline_for
from tests.conftest import auth, login, make_institution, make_user


def test_the_default_policy_is_visible_and_complete(app, alpha):
    created = seed_priority_policies(alpha)
    db.session.commit()

    assert created == 4
    rows = PriorityPolicy.query.filter_by(institution_id=alpha.id).all()
    assert {r.priority for r in rows} == {"low", "medium", "high", "urgent"}


def test_seeding_again_does_not_overwrite_an_edit(app, alpha):
    seed_priority_policies(alpha)
    urgent = PriorityPolicy.query.filter_by(
        institution_id=alpha.id, priority="urgent"
    ).one()
    urgent.acknowledge_hours = 3
    db.session.commit()

    assert seed_priority_policies(alpha) == 0
    assert urgent.acknowledge_hours == 3


def test_acknowledgement_and_resolution_both_follow_the_policy(app, alpha):
    policy = PriorityPolicy(
        institution_id=alpha.id,
        priority="urgent",
        acknowledge_hours=1,
        resolution_factor=0.25,
        escalation_step_hours=2,
        reminder_hours_before_due=2,
    )
    db.session.add(policy)
    db.session.commit()

    # Monday at the opening of the working day, in UTC/WAT terms. The
    # expected values use the same working-calendar primitive but the
    # policy figures are asserted independently.
    start = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
    acknowledge, resolve = deadline_for(alpha, None, "urgent", start)

    assert acknowledge == add_working_hours(start, 1, 8, 17)
    assert resolve == add_working_hours(start, alpha.default_sla_hours * 0.25, 8, 17)


def test_an_institution_without_policies_keeps_legacy_behaviour(app, alpha):
    start = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
    acknowledge, resolve = deadline_for(alpha, None, "high", start)

    assert acknowledge == add_working_hours(start, alpha.acknowledge_sla_hours, 8, 17)
    assert resolve == add_working_hours(start, alpha.default_sla_hours * 0.5, 8, 17)


def test_an_institution_cannot_see_another_ones_policy(client, alpha):
    beta = make_institution(code="BBB", slug="beta-university", name="Beta University")
    make_user(alpha, "admin@alpha.ng", role="institution_admin")
    token = login(client, "admin@alpha.ng")
    db.session.add(
        PriorityPolicy(
            institution_id=beta.id,
            priority="urgent",
            acknowledge_hours=9,
            resolution_factor=0.25,
            escalation_step_hours=9,
            reminder_hours_before_due=1,
        )
    )
    db.session.commit()

    response = client.get("/api/routing/priority-policies", headers=auth(token))

    assert response.status_code == 200
    assert response.get_json()["data"]["policies"] == []


def test_an_admin_can_set_one_priority_policy(client, alpha):
    make_user(alpha, "admin@alpha.ng", role="institution_admin")
    token = login(client, "admin@alpha.ng")

    response = client.put(
        "/api/routing/priority-policies/high",
        headers=auth(token),
        json={
            "acknowledge_hours": 4,
            "resolution_factor": 0.5,
            "escalation_step_hours": 8,
            "reminder_hours_before_due": 4,
        },
    )

    assert response.status_code == 200
    policy = response.get_json()["data"]["policy"]
    assert policy["priority"] == "high"
    assert policy["acknowledge_hours"] == 4
    assert policy["escalation_step_hours"] == 8


def test_policy_validation_refuses_values_that_make_no_operational_sense(client, alpha):
    make_user(alpha, "admin@alpha.ng", role="institution_admin")
    token = login(client, "admin@alpha.ng")

    response = client.put(
        "/api/routing/priority-policies/urgent",
        headers=auth(token),
        json={
            "acknowledge_hours": 0,
            "resolution_factor": 0,
            "escalation_step_hours": 0,
            "reminder_hours_before_due": -1,
        },
    )

    assert response.status_code == 422
    assert set(response.get_json()["errors"]) == {
        "acknowledge_hours",
        "resolution_factor",
        "escalation_step_hours",
        "reminder_hours_before_due",
    }
    assert PriorityPolicy.query.count() == 0


def test_only_an_institution_admin_can_change_policy(client, alpha):
    make_user(alpha, "officer@alpha.ng", role="officer")
    token = login(client, "officer@alpha.ng")

    response = client.put(
        "/api/routing/priority-policies/medium",
        headers=auth(token),
        json={
            "acknowledge_hours": 8,
            "resolution_factor": 1,
            "escalation_step_hours": 24,
            "reminder_hours_before_due": 12,
        },
    )

    assert response.status_code == 403
