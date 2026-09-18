from datetime import datetime, timedelta, timezone

from app.services.sla import WAT, add_working_hours, fixed_holidays, run_escalation_sweep
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Fees receipt not reflecting",
    "description": "I paid my school fees three weeks ago and the portal still shows unpaid.",
    "category": "fees_payment",
    "priority": "medium",
}


def wat(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=WAT)


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


def test_escalation_notifies_the_student_and_leadership(client, alpha, db):
    from app.models.complaint import Complaint, Notification
    from app.models.base import utcnow

    student = make_user(alpha, "student@test.ng")
    head = make_user(alpha, "head@test.ng", role="dept_head")
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
