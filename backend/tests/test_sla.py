from datetime import datetime, timedelta, timezone

from app.services.sla import (
    WAT,
    add_working_hours,
    escalation_step_hours,
    fixed_holidays,
    run_escalation_sweep,
)
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Fees receipt not reflecting",
    "description": "I paid my school fees three weeks ago and the portal still shows unpaid.",
    "category": "fees_payment",
    "priority": "medium",
}


def wat(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=WAT)


def bursary(institution):
    """The unit a fees complaint routes to once routing is seeded."""
    from app.models.institution import Department

    return Department.query.filter_by(institution_id=institution.id, slug="bursary").first()


def test_working_hours_do_not_run_overnight():
    # 16:00 Monday plus 4 hours, with a day closing at 17:00, lands at
    # 11:00 Tuesday rather than 20:00 Monday.
    start = wat(2026, 9, 14, 16)
    result = add_working_hours(start, 4, 8, 17, holidays=set()).astimezone(WAT)

    assert result.day == 15
    assert result.hour == 11


def test_friday_evening_does_not_breach_over_the_weekend():
    """The failure this calculation exists to prevent."""
    start = wat(2026, 9, 18, 18)  # Friday, after closing
    result = add_working_hours(start, 8, 8, 17, holidays=set()).astimezone(WAT)

    # Counting resumes Monday morning, not Saturday.
    assert result.weekday() == 0
    assert result.day == 21


def test_saturday_is_skipped():
    start = wat(2026, 9, 19, 10)  # Saturday
    result = add_working_hours(start, 2, 8, 17, holidays=set()).astimezone(WAT)

    assert result.weekday() == 0


def test_public_holiday_is_skipped():
    # 1 October is Independence Day and falls on a Thursday in 2026.
    start = wat(2026, 9, 30, 15)
    result = add_working_hours(start, 4, 8, 17, holidays=fixed_holidays(2026)).astimezone(WAT)

    assert result.date().isoformat() != "2026-10-01"


def test_deadline_is_set_within_working_hours(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]

    due = datetime.fromisoformat(complaint["resolve_due_at"]).replace(tzinfo=timezone.utc)
    local = due.astimezone(WAT)

    assert local.weekday() < 5
    assert alpha.working_hours_start <= local.hour <= alpha.working_hours_end


def test_urgent_complaints_get_a_shorter_deadline(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    normal = client.post(
        "/api/complaints", headers=auth(token), json={**COMPLAINT, "priority": "low"}
    ).get_json()["data"]["complaint"]
    urgent = client.post(
        "/api/complaints", headers=auth(token), json={**COMPLAINT, "priority": "urgent"}
    ).get_json()["data"]["complaint"]

    assert urgent["resolve_due_at"] < normal["resolve_due_at"]
    # Before dynamic escalation, every priority got the same full-day
    # acknowledgement deadline. That contradicted the word "urgent".
    assert urgent["acknowledge_due_at"] < normal["acknowledge_due_at"]


def test_each_escalation_rung_is_priority_based():
    assert escalation_step_hours("low") == 48
    assert escalation_step_hours("medium") == 24
    assert escalation_step_hours("high") == 12
    assert escalation_step_hours("urgent") == 6


def test_unknown_priority_falls_back_to_the_standard_rung():
    """Old rows or imported data must not produce a zero-hour loop."""
    assert escalation_step_hours("not-a-priority") == 24


def test_sweep_escalates_an_overdue_complaint(client, alpha, db):
    from app.models.complaint import Complaint
    from app.models.base import utcnow

    make_user(alpha, "student@test.ng")
    make_user(alpha, "head@test.ng", role="dept_head")
    token = login(client, "student@test.ng")

    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    result = run_escalation_sweep()

    assert result["escalated"] == 1
    assert db.session.get(Complaint, complaint_id).escalated_at is not None


def test_sweep_does_not_escalate_twice(client, alpha, db):
    """Safe to run repeatedly from a scheduler."""
    from app.models.complaint import Complaint
    from app.models.base import utcnow

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    assert run_escalation_sweep()["escalated"] == 1
    assert run_escalation_sweep()["escalated"] == 0


def test_escalation_notifies_the_student_and_the_handling_unit(client, alpha, db):
    from app.models.base import utcnow
    from app.models.complaint import Complaint, Notification
    from app.services.routing import seed_routing, seed_units

    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)
    db.session.commit()

    student = make_user(alpha, "student@test.ng")
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = bursary(alpha).id
    db.session.commit()

    token = login(client, "student@test.ng")
    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    run_escalation_sweep()

    assert Notification.query.filter_by(user_id=head.id, type="escalation").count() == 1
    assert Notification.query.filter_by(user_id=student.id, type="escalation").count() == 1


def test_escalation_climbs_one_rung_at_a_time(client, alpha, db):
    """Telling everyone at once trains everyone to ignore the alerts."""
    from app.models.base import utcnow
    from app.models.complaint import Complaint, Notification
    from app.services.routing import seed_routing, seed_units

    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)
    db.session.commit()

    make_user(alpha, "student@test.ng")
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = bursary(alpha).id
    principal = make_user(alpha, "vc@test.ng", role="institution_admin")
    db.session.commit()

    token = login(client, "student@test.ng")
    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    run_escalation_sweep()

    # Only the unit head so far. The institution has not been troubled.
    assert Notification.query.filter_by(user_id=head.id, type="escalation").count() == 1
    assert Notification.query.filter_by(user_id=principal.id, type="escalation").count() == 0

    complaint = db.session.get(Complaint, complaint_id)
    assert complaint.escalation_level == 1

    # The unit had its window and did nothing, so it climbs.
    complaint.next_escalation_at = utcnow() - timedelta(minutes=1)
    db.session.commit()
    run_escalation_sweep()

    assert Notification.query.filter_by(user_id=principal.id, type="escalation").count() == 1
    assert db.session.get(Complaint, complaint_id).escalation_level == 2


def test_escalation_stops_at_the_top(client, alpha, db):
    """Once the institution has been told, there is nobody else to tell."""
    from app.models.base import utcnow
    from app.models.complaint import Complaint

    make_user(alpha, "student@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")

    token = login(client, "student@test.ng")
    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    run_escalation_sweep()
    complaint = db.session.get(Complaint, complaint_id)
    assert complaint.escalation_level == 1

    complaint.next_escalation_at = utcnow() - timedelta(minutes=1)
    db.session.commit()

    assert run_escalation_sweep()["escalated"] == 0
    assert db.session.get(Complaint, complaint_id).next_escalation_at is None


def test_a_complaint_still_escalates_when_no_staff_exist(client, alpha, db):
    """An unstaffed unit is not a reason to leave the student uninformed."""
    from app.models.base import utcnow
    from app.models.complaint import Complaint, Notification

    student = make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint_id = client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    assert run_escalation_sweep()["escalated"] == 1
    assert db.session.get(Complaint, complaint_id).escalated_at is not None
    assert Notification.query.filter_by(user_id=student.id, type="escalation").count() == 1


def test_resolved_complaints_are_never_escalated(client, alpha, db):
    from app.models.complaint import Complaint
    from app.models.base import utcnow

    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "in_progress"})
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "resolved", "note": "Receipt has now been applied."})

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(days=3)
    db.session.commit()

    assert run_escalation_sweep()["escalated"] == 0
