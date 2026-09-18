import csv
import io

from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Transcript request not processed",
    "description": "I applied for my transcript in July and there has been no response since.",
    "category": "transcript",
    "priority": "medium",
}


def rows(response):
    body = response.get_data(as_text=True).lstrip("\ufeff")
    return list(csv.DictReader(io.StringIO(body)))


def test_officers_cannot_export(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    assert client.get("/api/dashboard/export/complaints", headers=auth(token)).status_code == 403


def test_students_cannot_export(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    assert client.get("/api/dashboard/export/complaints", headers=auth(token)).status_code == 403


def test_export_returns_a_downloadable_file(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "head@test.ng", role="dept_head")

    student = login(client, "student@test.ng")
    client.post("/api/complaints", headers=auth(student), json=COMPLAINT)

    head = login(client, "head@test.ng")
    response = client.get("/api/dashboard/export/complaints", headers=auth(head))

    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]
    assert "attachment" in response.headers["Content-Disposition"]

    exported = rows(response)
    assert len(exported) == 1
    assert exported[0]["title"] == COMPLAINT["title"]
    assert exported[0]["status"] == "submitted"


def test_export_never_crosses_institutions(client, alpha, beta):
    make_user(alpha, "alpha.student@test.ng")
    make_user(alpha, "alpha.head@test.ng", role="dept_head")
    make_user(beta, "beta.student@test.ng")

    client.post(
        "/api/complaints",
        headers=auth(login(client, "alpha.student@test.ng")),
        json=COMPLAINT,
    )
    client.post(
        "/api/complaints",
        headers=auth(login(client, "beta.student@test.ng")),
        json={**COMPLAINT, "title": "Belongs to the other institution"},
    )

    head = login(client, "alpha.head@test.ng")
    exported = rows(client.get("/api/dashboard/export/complaints", headers=auth(head)))

    titles = {row["title"] for row in exported}
    assert "Belongs to the other institution" not in titles


def test_anonymous_complaints_stay_anonymous_in_the_export(client, alpha, db):
    from app.models.complaint import Complaint

    make_user(alpha, "student@test.ng")
    make_user(alpha, "head@test.ng", role="dept_head")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.is_anonymous = True
    db.session.commit()

    head = login(client, "head@test.ng")
    exported = rows(client.get("/api/dashboard/export/complaints", headers=auth(head)))

    assert exported[0]["student_name"] == ""
    assert exported[0]["matric_number"] == ""


def test_formula_injection_is_neutralised(client, alpha):
    """A spreadsheet executes a leading equals sign on open."""
    make_user(alpha, "student@test.ng")
    make_user(alpha, "head@test.ng", role="dept_head")

    student = login(client, "student@test.ng")
    client.post(
        "/api/complaints",
        headers=auth(student),
        json={**COMPLAINT, "title": '=cmd|calc!A1 exam result missing'},
    )

    head = login(client, "head@test.ng")
    exported = rows(client.get("/api/dashboard/export/complaints", headers=auth(head)))

    assert exported[0]["title"].startswith("'=")


def test_people_export_requires_an_administrator(client, alpha):
    make_user(alpha, "head@test.ng", role="dept_head")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    head = login(client, "head@test.ng")
    assert client.get("/api/dashboard/export/users", headers=auth(head)).status_code == 403

    admin = login(client, "admin@test.ng")
    assert client.get("/api/dashboard/export/users", headers=auth(admin)).status_code == 200


def test_average_resolution_is_computed_in_the_database(client, alpha):
    """Guards the dialect-specific arithmetic used to avoid loading rows."""
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
               json={"status": "resolved", "note": "Transcript has been issued."})

    overview = client.get("/api/dashboard/overview", headers=auth(officer)).get_json()["data"]

    assert overview["overview"]["avg_resolution_time_hours"] >= 0
    assert overview["overview"]["resolution_rate"] == 100.0
