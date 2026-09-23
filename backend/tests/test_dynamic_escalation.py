"""Priority-specific acknowledgement, resolution and escalation timing."""

from datetime import datetime, timezone

import pytest

from app.models.complaint import Complaint
from app.services.sla import deadline_for, priority_policy, validate_priority_policy


FUW_POLICY = {
    "low": {
        "acknowledge_hours": 24,
        "resolution_hours": 120,
        "escalation_step_hours": 48,
    },
    "medium": {
        "acknowledge_hours": 8,
        "resolution_hours": 72,
        "escalation_step_hours": 24,
    },
    "high": {
        "acknowledge_hours": 4,
        "resolution_hours": 24,
        "escalation_step_hours": 8,
    },
    "urgent": {
        "acknowledge_hours": 2,
        "resolution_hours": 8,
        "escalation_step_hours": 2,
    },
}

# Monday at 08:00 WAT == 07:00 UTC. Keeping every test inside one working
# day makes the assertion about policy rather than weekend arithmetic.
MONDAY_OPEN_UTC = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)


def hours_between(start, end):
    return (end - start).total_seconds() / 3600


def test_no_policy_preserves_the_old_behaviour(alpha):
    alpha.acknowledge_sla_hours = 24
    alpha.default_sla_hours = 72
    alpha.priority_sla_policy = None

    urgent = priority_policy(alpha, "urgent")

    assert urgent["acknowledge_hours"] == 24
    assert urgent["resolution_hours"] is None
    assert urgent["resolution_factor"] == 0.25
    assert urgent["escalation_step_hours"] == 24


def test_fuw_policy_is_used_for_each_priority(alpha):
    alpha.priority_sla_policy = FUW_POLICY

    assert priority_policy(alpha, "low")["resolution_hours"] == 120
    assert priority_policy(alpha, "medium")["acknowledge_hours"] == 8
    assert priority_policy(alpha, "high")["escalation_step_hours"] == 8
    assert priority_policy(alpha, "urgent") == {
        "acknowledge_hours": 2,
        "resolution_hours": 8,
        "resolution_factor": 0.25,
        "escalation_step_hours": 2,
    }


def test_urgent_deadlines_are_not_the_medium_deadlines(alpha):
    alpha.priority_sla_policy = FUW_POLICY
    alpha.working_hours_start = 8
    alpha.working_hours_end = 17

    urgent_ack, urgent_resolve = deadline_for(
        alpha, None, "urgent", start=MONDAY_OPEN_UTC
    )
    medium_ack, medium_resolve = deadline_for(
        alpha, None, "medium", start=MONDAY_OPEN_UTC
    )

    assert hours_between(MONDAY_OPEN_UTC, urgent_ack) == 2
    assert hours_between(MONDAY_OPEN_UTC, urgent_resolve) == 8
    assert hours_between(MONDAY_OPEN_UTC, medium_ack) == 8
    assert urgent_ack < medium_ack
    assert urgent_resolve < medium_resolve


def test_absolute_priority_target_wins_over_a_category_override(alpha):
    """A critical category cannot accidentally lengthen an urgent case."""
    alpha.priority_sla_policy = FUW_POLICY

    _, resolve = deadline_for(
        alpha,
        None,
        "urgent",
        start=MONDAY_OPEN_UTC,
        override_hours=200,
    )

    assert hours_between(MONDAY_OPEN_UTC, resolve) == 8


def test_the_approved_matrix_validates():
    cleaned, errors = validate_priority_policy(FUW_POLICY)

    assert errors == {}
    assert cleaned == FUW_POLICY


@pytest.mark.parametrize(
    "mutation,error_key",
    [
        (("urgent", "acknowledge_hours", 0), "priority_sla_policy.urgent.acknowledge_hours"),
        (("high", "resolution_hours", "24"), "priority_sla_policy.high.resolution_hours"),
        (("low", "escalation_step_hours", 721), "priority_sla_policy.low.escalation_step_hours"),
    ],
)
def test_invalid_policy_is_refused(mutation, error_key):
    policy = {name: dict(row) for name, row in FUW_POLICY.items()}
    priority, field, value = mutation
    policy[priority][field] = value

    cleaned, errors = validate_priority_policy(policy)

    assert cleaned is None
    assert error_key in errors


def test_policy_round_trips_through_settings_api(client, alpha):
    from tests.conftest import auth, login, make_user

    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    saved = client.put(
        "/api/admin/settings",
        headers=auth(token),
        json={"priority_sla_policy": FUW_POLICY},
    )

    assert saved.status_code == 200
    assert saved.get_json()["data"]["institution"]["priority_sla_policy"] == FUW_POLICY
