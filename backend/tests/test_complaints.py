from tests.conftest import auth, login, make_user

VALID = {
    "title": "Missing result for CSC 301",
    "description": "My result has not appeared on the portal since the semester ended.",
    "category": "result_issues",
    "priority": "medium",
}


def file_complaint(client, token, **overrides):
    return client.post("/api/complaints", headers=auth(token), json={**VALID, **overrides})


def test_ticket_number_uses_the_safe_alphabet(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    ticket = file_complaint(client, token).get_json()["data"]["complaint"]["ticket_number"]

    assert ticket.startswith("AAA-")
    # I, L, O, U, 0 and 1 are excluded because tickets are read aloud.
    assert not set("ILOU01") & set(ticket.split("-")[1])


def test_sla_deadline_is_set_on_submission(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint = file_complaint(client, token).get_json()["data"]["complaint"]

    assert complaint["resolve_due_at"] is not None
    assert complaint["acknowledge_due_at"] is not None


def test_short_description_is_rejected(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    response = file_complaint(client, token, description="too short")

    assert response.status_code == 422
    assert "description" in response.get_json()["errors"]


def test_student_cannot_read_another_students_complaint(client, alpha):
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    first = login(client, "one@test.ng")
    complaint_id = file_complaint(client, first).get_json()["data"]["complaint"]["id"]

    second = login(client, "two@test.ng")
    response = client.get(f"/api/complaints/{complaint_id}", headers=auth(second))

    assert response.status_code == 404


def test_student_cannot_change_status(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    response = client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(token), json={"status": "resolved"}
    )

    assert response.status_code == 403


def test_illegal_status_transition_is_blocked(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    # submitted -> closed is not a permitted move.
    response = client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(officer), json={"status": "closed"}
    )

    assert response.status_code == 409


def test_resolving_requires_an_explanation(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "in_progress"})

    response = client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(officer), json={"status": "resolved"}
    )

    assert response.status_code == 422


def test_declining_requires_a_reason(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    response = client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(officer), json={"status": "declined"}
    )

    assert response.status_code == 422


def test_internal_notes_are_hidden_from_the_student(client, alpha):
    """A private note leaking to a student would be a safeguarding incident."""
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(officer),
        json={"message": "Escalating to the Dean quietly.", "is_internal": True},
    )

    seen_by_student = client.get(f"/api/complaints/{complaint_id}", headers=auth(student))
    messages = [r["message"] for r in seen_by_student.get_json()["data"]["complaint"]["responses"]]
    assert messages == []

    seen_by_staff = client.get(f"/api/complaints/{complaint_id}", headers=auth(officer))
    staff_messages = [r["message"] for r in seen_by_staff.get_json()["data"]["complaint"]["responses"]]
    assert "Escalating to the Dean quietly." in staff_messages


def test_student_cannot_forge_an_internal_note(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    response = client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(token),
        json={"message": "Trying to hide this.", "is_internal": True},
    )

    assert response.get_json()["data"]["response"]["is_internal"] is False


def test_officer_cannot_assign_but_department_head_can(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")
    head = make_user(alpha, "head@test.ng", role="dept_head")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    denied = client.put(
        f"/api/complaints/{complaint_id}/assign", headers=auth(officer),
        json={"assigned_to_id": head.id},
    )
    assert denied.status_code == 403

    head_token = login(client, "head@test.ng")
    allowed = client.put(
        f"/api/complaints/{complaint_id}/assign", headers=auth(head_token),
        json={"assigned_to_id": head.id},
    )
    assert allowed.status_code == 200


def test_public_tracking_hides_personal_data(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    ticket = file_complaint(client, token).get_json()["data"]["complaint"]["ticket_number"]

    # No authentication header: a ticket number is the only credential.
    response = client.get(f"/api/public/track/{ticket.replace('-', '').lower()}")

    assert response.status_code == 200
    payload = response.get_json()["data"]["complaint"]
    assert payload["status"] == "submitted"
    for leaked in ("description", "student", "title"):
        assert leaked not in payload


def test_audit_trail_records_every_change(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "acknowledged"})

    events = client.get(f"/api/complaints/{complaint_id}", headers=auth(officer))
    actions = [e["action"] for e in events.get_json()["data"]["complaint"]["events"]]

    assert "created" in actions
    assert "status_changed" in actions
