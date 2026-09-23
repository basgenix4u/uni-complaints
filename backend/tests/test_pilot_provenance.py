"""Controlled and operational evidence must remain distinguishable.

The marker is inherited from the authenticated account, not accepted
from request JSON. Otherwise a controlled account could remove it and
silently turn a scripted case into an operational research outcome.
"""

from app.extensions import db
from app.models.complaint import Complaint
from tests.conftest import auth, login, make_user

BASE = {
    "title": "Course registration not updating",
    "description": "The selected courses do not appear on the final registration form.",
    "category": "course_registration",
    "priority": "medium",
}


def test_a_controlled_account_marks_every_complaint_it_files(client, alpha):
    user = make_user(alpha, "student@test.ng")
    user.data_origin = "controlled_pilot"
    user.pilot_cohort_id = "FUW-STU-001"
    user.pilot_scenario_id = "FUW-CASE-001"
    db.session.commit()
    token = login(client, "student@test.ng")

    response = client.post("/api/complaints", headers=auth(token), json=BASE)

    assert response.status_code == 201
    complaint_id = response.get_json()["data"]["complaint"]["id"]
    stored = db.session.get(Complaint, complaint_id)
    assert stored.data_origin == "controlled_pilot"
    assert stored.pilot_scenario_id == "FUW-CASE-001"


def test_the_request_cannot_remove_or_change_the_marker(client, alpha):
    user = make_user(alpha, "student@test.ng")
    user.data_origin = "controlled_pilot"
    user.pilot_scenario_id = "FUW-CASE-002"
    db.session.commit()
    token = login(client, "student@test.ng")

    response = client.post(
        "/api/complaints",
        headers=auth(token),
        json={**BASE, "data_origin": "operational", "pilot_scenario_id": None},
    )

    complaint_id = response.get_json()["data"]["complaint"]["id"]
    stored = db.session.get(Complaint, complaint_id)
    assert stored.data_origin == "controlled_pilot"
    assert stored.pilot_scenario_id == "FUW-CASE-002"


def test_an_ordinary_account_stays_operational(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    response = client.post("/api/complaints", headers=auth(token), json=BASE)

    complaint_id = response.get_json()["data"]["complaint"]["id"]
    stored = db.session.get(Complaint, complaint_id)
    assert stored.data_origin == "operational"
    assert stored.pilot_scenario_id is None
