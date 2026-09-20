import io
import json
from datetime import timedelta

from app.extensions import db
from app.models.access_log import AccessLog
from app.models.base import utcnow
from app.models.complaint import Complaint, Notification, Response
from app.models.user import User
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Hostel water supply cut for two weeks",
    "description": "There has been no running water in Block C since the start of the month.",
    "category": "accommodation",
    "priority": "high",
}


def file_complaint(client, token, **overrides):
    return client.post("/api/complaints", headers=auth(token), json={**COMPLAINT, **overrides})


# -- portability ------------------------------------------------------


def test_a_person_can_download_their_own_data(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    file_complaint(client, token)

    response = client.get("/api/privacy/my-data", headers=auth(token))

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]

    payload = json.loads(response.get_data(as_text=True))
    assert payload["account"]["email"] == "student@test.ng"
    assert len(payload["complaints"]) == 1
    assert payload["complaints"][0]["title"] == COMPLAINT["title"]


def test_the_export_excludes_internal_notes(client, alpha):
    """Staff deliberation is not personal data about the subject."""
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(officer),
        json={"message": "Escalating this quietly to the dean.", "is_internal": True},
    )
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(officer),
        json={"message": "Maintenance will attend tomorrow."},
    )

    payload = json.loads(
        client.get("/api/privacy/my-data", headers=auth(student)).get_data(as_text=True)
    )
    messages = [m["message"] for m in payload["complaints"][0]["messages"]]

    assert "Maintenance will attend tomorrow." in messages
    assert not any("dean" in message for message in messages)


def test_the_export_never_includes_another_person(client, alpha):
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    first = login(client, "one@test.ng")
    file_complaint(client, first, title="Filed by the first student here")

    second = login(client, "two@test.ng")
    payload = json.loads(
        client.get("/api/privacy/my-data", headers=auth(second)).get_data(as_text=True)
    )

    assert payload["complaints"] == []


def test_the_export_requires_signing_in(client):
    assert client.get("/api/privacy/my-data").status_code == 401


# -- erasure ----------------------------------------------------------


def erase(client, token, password="Password123", confirm="ERASE"):
    return client.post(
        "/api/privacy/erase-my-account",
        headers=auth(token),
        json={"password": password, "confirm": confirm},
    )


def test_erasure_requires_the_password(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    assert erase(client, token, password="WrongPass123").status_code == 401


def test_erasure_requires_typed_confirmation(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    assert erase(client, token, confirm="yes").status_code == 422


def test_erasure_removes_identifying_details(client, alpha):
    user = make_user(alpha, "student@test.ng", matric="ENG/COE/21/013")
    user.phone = "+2348012345678"
    db.session.commit()
    token = login(client, "student@test.ng")

    assert erase(client, token).status_code == 200

    erased = db.session.get(User, user.id)
    assert erased.full_name == "Erased account"
    assert erased.email != "student@test.ng"
    assert erased.matric_number is None
    assert erased.phone is None
    assert erased.is_active is False
    assert erased.erased_at is not None


def test_erasure_keeps_the_complaint_as_an_anonymous_record(client, alpha):
    """The institution keeps its record of what it decided."""
    user = make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    erase(client, token)

    complaint = db.session.get(Complaint, complaint_id)
    assert complaint is not None
    assert complaint.is_anonymous is True
    assert COMPLAINT["description"] not in complaint.description
    assert complaint.status == "submitted"


def test_erasure_cannot_be_undone_by_signing_in(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    erase(client, token)

    assert (
        client.post(
            "/api/auth/login", json={"email": "student@test.ng", "password": "Password123"}
        ).status_code
        == 401
    )


def test_erasure_redacts_messages_the_person_wrote(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(token),
        json={"message": "My room number is B14 and my phone is 08012345678."},
    )

    erase(client, token)

    messages = [r.message for r in Response.query.all()]
    assert not any("08012345678" in message for message in messages)


def test_erasure_deletes_uploaded_files(client, alpha, app):
    from pathlib import Path

    from app.models.attachment import Attachment

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    client.post(
        f"/api/complaints/{complaint_id}/attachments",
        headers=auth(token),
        data={"file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200), "evidence.png", "image/png")},
        content_type="multipart/form-data",
    )

    stored = Attachment.query.first().stored_name
    path = Path(app.config["UPLOAD_DIR"]) / stored
    assert path.exists()

    erase(client, token)

    assert not path.exists()
    assert Attachment.query.count() == 0


def test_erasure_clears_notifications(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    file_complaint(client, token)

    assert Notification.query.count() > 0
    erase(client, token)
    assert Notification.query.count() == 0


def test_erasure_keeps_the_audit_trail_without_the_person(client, alpha):
    from app.models.complaint import ComplaintEvent

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    file_complaint(client, token)

    before = ComplaintEvent.query.count()
    erase(client, token)

    assert ComplaintEvent.query.count() == before
    assert all(event.actor_id is None for event in ComplaintEvent.query.all())


def test_staff_cannot_erase_themselves_through_the_self_route(client, alpha):
    """Open work has to be handed over first."""
    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    assert erase(client, token).status_code == 409


def test_an_administrator_can_erase_on_a_written_request(client, alpha):
    student = make_user(alpha, "student@test.ng")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    token = login(client, "admin@test.ng")
    response = client.post(
        f"/api/privacy/users/{student.id}/erase",
        headers=auth(token),
        json={"reason": "letter received 12 Oct"},
    )

    assert response.status_code == 200
    assert db.session.get(User, student.id).erased_at is not None


def test_erasure_does_not_cross_institutions(client, alpha, beta):
    make_user(alpha, "alpha.admin@test.ng", role="institution_admin")
    victim = make_user(beta, "beta.student@test.ng")

    token = login(client, "alpha.admin@test.ng")
    response = client.post(f"/api/privacy/users/{victim.id}/erase", headers=auth(token))

    assert response.status_code == 404
    assert db.session.get(User, victim.id).erased_at is None


def test_officers_cannot_erase_anyone(client, alpha):
    student = make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    token = login(client, "officer@test.ng")
    assert client.post(f"/api/privacy/users/{student.id}/erase", headers=auth(token)).status_code == 403


def test_two_erasures_do_not_collide(client, alpha):
    """A shared placeholder email would break the unique index."""
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    assert erase(client, login(client, "one@test.ng")).status_code == 200
    assert erase(client, login(client, "two@test.ng")).status_code == 200


# -- access log -------------------------------------------------------


def test_staff_reads_are_recorded(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.get(f"/api/complaints/{complaint_id}", headers=auth(officer))

    entry = AccessLog.query.first()
    assert entry is not None
    assert entry.actor_role == "officer"
    assert entry.action == "viewed"


def test_a_student_reading_their_own_complaint_is_not_logged(client, alpha):
    """Ordinary use would bury the entries that matter."""
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token).get_json()["data"]["complaint"]["id"]

    client.get(f"/api/complaints/{complaint_id}", headers=auth(token))

    assert AccessLog.query.count() == 0


def test_only_administrators_can_read_the_access_log(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.get(f"/api/complaints/{complaint_id}", headers=auth(officer))

    assert (
        client.get(f"/api/privacy/complaints/{complaint_id}/access-log", headers=auth(officer)).status_code
        == 403
    )

    admin = login(client, "admin@test.ng")
    response = client.get(
        f"/api/privacy/complaints/{complaint_id}/access-log", headers=auth(admin)
    )
    assert response.status_code == 200
    assert len(response.get_json()["data"]["access_log"]) >= 1


# -- retention --------------------------------------------------------


def test_retention_is_off_until_configured(client, alpha):
    """Deleting records must be a deliberate choice."""
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    summary = client.post("/api/privacy/retention/purge", headers=auth(token)).get_json()["data"][
        "summary"
    ]

    assert summary["complaints_purged"] == 0


def test_purge_removes_only_old_closed_complaints(client, alpha, db):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    student = login(client, "student@test.ng")
    old_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]
    open_id = file_complaint(client, student, title="Still open and recent").get_json()["data"][
        "complaint"
    ]["id"]

    alpha.retention_months = 12
    old = db.session.get(Complaint, old_id)
    old.status = "closed"
    old.closed_at = utcnow() - timedelta(days=500)
    db.session.commit()

    token = login(client, "admin@test.ng")
    summary = client.post("/api/privacy/retention/purge", headers=auth(token)).get_json()["data"][
        "summary"
    ]

    assert summary["complaints_purged"] == 1
    assert db.session.get(Complaint, old_id) is None
    # An open complaint survives however old it is.
    assert db.session.get(Complaint, open_id) is not None


def test_purge_keeps_recent_closed_complaints(client, alpha, db):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    alpha.retention_months = 12
    complaint = db.session.get(Complaint, complaint_id)
    complaint.status = "closed"
    complaint.closed_at = utcnow() - timedelta(days=30)
    db.session.commit()

    token = login(client, "admin@test.ng")
    client.post("/api/privacy/retention/purge", headers=auth(token))

    assert db.session.get(Complaint, complaint_id) is not None
