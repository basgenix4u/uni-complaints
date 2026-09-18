"""Cross-tenant isolation.

A leak between institutions would be the most serious possible failure in
this system, so these cases are treated as release blockers.
"""

from tests.conftest import auth, login, make_user


def _file_complaint(client, token, title="Missing result for CSC 301"):
    return client.post(
        "/api/complaints",
        headers=auth(token),
        json={
            "title": title,
            "description": "My result has not appeared on the portal since the semester ended.",
            "category": "result_issues",
            "priority": "medium",
        },
    )


def test_student_cannot_list_another_institutions_complaints(client, alpha, beta):
    make_user(alpha, "alpha.student@test.ng")
    make_user(beta, "beta.student@test.ng")

    alpha_token = login(client, "alpha.student@test.ng")
    _file_complaint(client, alpha_token, "Alpha only complaint")

    beta_token = login(client, "beta.student@test.ng")
    response = client.get("/api/complaints", headers=auth(beta_token))

    assert response.status_code == 200
    assert response.get_json()["data"]["complaints"] == []


def test_staff_cannot_read_complaint_from_another_institution(client, alpha, beta):
    make_user(alpha, "alpha.student@test.ng")
    make_user(beta, "beta.admin@test.ng", role="institution_admin")

    alpha_token = login(client, "alpha.student@test.ng")
    complaint_id = _file_complaint(client, alpha_token).get_json()["data"]["complaint"]["id"]

    beta_token = login(client, "beta.admin@test.ng")
    response = client.get(f"/api/complaints/{complaint_id}", headers=auth(beta_token))

    assert response.status_code == 404


def test_staff_cannot_change_status_across_institutions(client, alpha, beta):
    make_user(alpha, "alpha.student@test.ng")
    make_user(beta, "beta.admin@test.ng", role="institution_admin")

    alpha_token = login(client, "alpha.student@test.ng")
    complaint_id = _file_complaint(client, alpha_token).get_json()["data"]["complaint"]["id"]

    beta_token = login(client, "beta.admin@test.ng")
    response = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(beta_token),
        json={"status": "acknowledged"},
    )

    assert response.status_code == 404


def test_same_email_may_exist_in_two_institutions(client, alpha, beta):
    make_user(alpha, "shared@test.ng")
    make_user(beta, "shared@test.ng")

    response = client.post(
        "/api/auth/login",
        json={"email": "shared@test.ng", "password": "Password123", "institution": "beta-polytechnic"},
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user"]["institution_id"] == beta.id
