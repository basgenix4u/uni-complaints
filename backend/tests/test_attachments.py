import io

from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Damaged hostel window",
    "description": "The window in my room has been broken since the start of term and lets in rain.",
    "category": "accommodation",
    "priority": "medium",
}

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 128
PDF = b"%PDF-1.4\n" + b"\x00" * 128


def file_complaint(client, token):
    return client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]


def upload(client, token, complaint_id, data=PNG, name="evidence.png", mime="image/png", **form):
    return client.post(
        f"/api/complaints/{complaint_id}/attachments",
        headers=auth(token),
        data={"file": (io.BytesIO(data), name, mime), **form},
        content_type="multipart/form-data",
    )


def test_student_can_attach_an_image(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    response = upload(client, token, complaint_id)

    assert response.status_code == 201
    attachment = response.get_json()["data"]["attachment"]
    assert attachment["original_name"] == "evidence.png"
    assert attachment["is_image"] is True


def test_executable_disguised_as_an_image_is_rejected(client, alpha):
    """The declared type is not trusted; the bytes are checked."""
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    response = upload(client, token, complaint_id, data=b"MZ\x90\x00" + b"\x00" * 128)

    assert response.status_code == 422


def test_disallowed_type_is_rejected(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    response = upload(
        client, token, complaint_id, data=b"#!/bin/sh\n", name="run.sh", mime="application/x-sh"
    )

    assert response.status_code == 422


def test_oversized_file_is_rejected(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 10)
    response = upload(client, token, complaint_id, data=oversized)

    assert response.status_code == 422


def test_empty_file_is_rejected(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    assert upload(client, token, complaint_id, data=b"").status_code == 422


def test_attachment_limit_is_enforced(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    for _ in range(5):
        assert upload(client, token, complaint_id).status_code == 201

    assert upload(client, token, complaint_id).status_code == 409


def test_another_student_cannot_download_the_file(client, alpha):
    make_user(alpha, "owner@test.ng")
    make_user(alpha, "other@test.ng")

    owner = login(client, "owner@test.ng")
    complaint_id = file_complaint(client, owner)
    attachment_id = upload(client, owner, complaint_id).get_json()["data"]["attachment"]["id"]

    other = login(client, "other@test.ng")
    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(other)
    )

    assert response.status_code == 404


def test_staff_from_another_institution_cannot_download(client, alpha, beta):
    make_user(alpha, "student@test.ng")
    make_user(beta, "beta.admin@test.ng", role="institution_admin")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student)
    attachment_id = upload(client, student, complaint_id).get_json()["data"]["attachment"]["id"]

    intruder = login(client, "beta.admin@test.ng")
    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(intruder)
    )

    assert response.status_code == 404


def test_owner_can_download_their_own_file(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)
    attachment_id = upload(client, token, complaint_id, data=PDF, name="receipt.pdf",
                           mime="application/pdf").get_json()["data"]["attachment"]["id"]

    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(token)
    )

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


def test_internal_attachment_is_hidden_from_the_student(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student)

    officer = login(client, "officer@test.ng")
    attachment_id = upload(
        client, officer, complaint_id, data=JPEG, name="internal.jpg",
        mime="image/jpeg", is_internal="true",
    ).get_json()["data"]["attachment"]["id"]

    blocked = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(student)
    )
    assert blocked.status_code == 404

    listed = client.get(f"/api/complaints/{complaint_id}", headers=auth(student))
    assert listed.get_json()["data"]["complaint"]["attachments"] == []


def test_student_cannot_mark_an_attachment_internal(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    response = upload(client, token, complaint_id, is_internal="true")

    assert response.get_json()["data"]["attachment"]["is_internal"] is False


def test_uploader_can_remove_their_file(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)
    attachment_id = upload(client, token, complaint_id).get_json()["data"]["attachment"]["id"]

    removed = client.delete(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(token)
    )
    assert removed.status_code == 200

    gone = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(token)
    )
    assert gone.status_code == 404


def test_stored_name_does_not_use_the_supplied_filename(client, alpha):
    """A crafted name must never reach the filesystem."""
    from app.models.attachment import Attachment

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    upload(client, token, complaint_id, name="../../etc/passwd.png")

    stored = Attachment.query.first().stored_name
    assert ".." not in stored
    assert "/" not in stored
