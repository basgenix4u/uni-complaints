"""The timeline a student sees on their own complaint.

Watching the complaint move is the product's promise, so the student
gets the events — but not the internal workings. The dangerous mistakes
are inclusion ones: a private note's existence, or the record of who
read what, leaking into a student's view.
"""

from app.extensions import db
from app.models.complaint import Complaint
from tests.conftest import auth, login, make_user

BODY = "The window has been broken since the start of term and lets in rain."


def file_and_work_on_a_complaint(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="institution_admin")
    student = login(client, "student@test.ng")
    staff = login(client, "officer@test.ng")

    complaint_id = client.post(
        "/api/complaints",
        headers=auth(student),
        json={
            "title": "Broken hostel window",
            "description": BODY,
            "category": "accommodation",
            "priority": "medium",
        },
    ).get_json()["data"]["complaint"]["id"]

    # Staff work the case: read it, change status, leave a private note.
    client.get(f"/api/complaints/{complaint_id}", headers=auth(staff))
    client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(staff),
        json={"status": "acknowledged"},
    )
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(staff),
        json={"message": "Internal: the contractor is already on site.", "is_internal": True},
    )
    return complaint_id, student, staff


def test_a_student_sees_their_complaint_move(client, alpha):
    complaint_id, student, _ = file_and_work_on_a_complaint(client, alpha)

    data = client.get(
        f"/api/complaints/{complaint_id}", headers=auth(student)
    ).get_json()["data"]["complaint"]

    actions = [e["action"] for e in data["events"]]
    assert "created" in actions
    assert "status_changed" in actions


def test_the_internal_workings_stay_internal(client, alpha):
    """Neither the private note's existence nor staff reads may leak."""
    complaint_id, student, _ = file_and_work_on_a_complaint(client, alpha)

    data = client.get(
        f"/api/complaints/{complaint_id}", headers=auth(student)
    ).get_json()["data"]["complaint"]

    actions = {e["action"] for e in data["events"]}
    assert "replied" not in actions
    assert "viewed" not in actions

    serialised = str(data["events"])
    assert "contractor" not in serialised


def test_staff_still_see_everything(client, alpha):
    complaint_id, _, staff = file_and_work_on_a_complaint(client, alpha)

    data = client.get(
        f"/api/complaints/{complaint_id}", headers=auth(staff)
    ).get_json()["data"]["complaint"]

    actions = {e["action"] for e in data["events"]}
    assert "replied" in actions
