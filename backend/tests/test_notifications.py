from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Missing result for CSC 301",
    "description": "My result has not appeared on the portal since the semester ended.",
    "category": "result_issues",
    "priority": "medium",
}


def test_filing_a_complaint_notifies_the_student(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    client.post("/api/complaints", headers=auth(token), json=COMPLAINT)
    data = client.get("/api/notifications", headers=auth(token)).get_json()["data"]

    assert data["unread_count"] == 1
    assert data["notifications"][0]["type"] == "submitted"


def test_notifications_are_private_to_their_owner(client, alpha):
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    first = login(client, "one@test.ng")
    client.post("/api/complaints", headers=auth(first), json=COMPLAINT)

    second = login(client, "two@test.ng")
    data = client.get("/api/notifications", headers=auth(second)).get_json()["data"]

    assert data["notifications"] == []
    assert data["unread_count"] == 0


def test_status_change_notifies_the_student(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "acknowledged"})

    count = client.get("/api/notifications/unread-count",
                       headers=auth(student)).get_json()["data"]["unread_count"]

    assert count == 2


def test_mark_all_read_clears_the_counter(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    client.post("/api/complaints", headers=auth(token), json=COMPLAINT)
    client.put("/api/notifications/read-all", headers=auth(token))

    count = client.get("/api/notifications/unread-count",
                       headers=auth(token)).get_json()["data"]["unread_count"]

    assert count == 0


def test_cannot_mark_another_users_notification_as_read(client, alpha):
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    first = login(client, "one@test.ng")
    client.post("/api/complaints", headers=auth(first), json=COMPLAINT)
    notification_id = client.get(
        "/api/notifications", headers=auth(first)
    ).get_json()["data"]["notifications"][0]["id"]

    second = login(client, "two@test.ng")
    response = client.put(f"/api/notifications/{notification_id}/read", headers=auth(second))

    assert response.status_code == 404
