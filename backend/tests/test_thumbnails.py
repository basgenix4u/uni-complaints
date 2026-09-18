import io

import pytest

from app.extensions import db
from app.models.attachment import Attachment
from app.services import thumbnails
from tests.conftest import auth, login, make_user

pytestmark = pytest.mark.skipif(
    not thumbnails.PILLOW_AVAILABLE, reason="Pillow is not installed"
)

COMPLAINT = {
    "title": "Broken window in the hostel",
    "description": "The window in my room has been broken since the start of term.",
    "category": "accommodation",
    "priority": "medium",
}


def real_png(size=(900, 700)):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, (11, 107, 87)).save(buffer, "PNG")
    return buffer.getvalue()


def file_complaint(client, token):
    return client.post("/api/complaints", headers=auth(token), json=COMPLAINT).get_json()[
        "data"
    ]["complaint"]["id"]


def upload(client, token, complaint_id, data=None, name="photo.png", mime="image/png", **form):
    return client.post(
        f"/api/complaints/{complaint_id}/attachments",
        headers=auth(token),
        data={"file": (io.BytesIO(data or real_png()), name, mime), **form},
        content_type="multipart/form-data",
    )


def test_an_image_upload_gets_a_preview(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    attachment = upload(client, token, complaint_id).get_json()["data"]["attachment"]

    assert attachment["has_preview"] is True


def test_a_document_gets_no_preview(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    attachment = upload(
        client, token, complaint_id,
        data=b"%PDF-1.4\n" + b"\x00" * 200, name="receipt.pdf", mime="application/pdf",
    ).get_json()["data"]["attachment"]

    assert attachment["has_preview"] is False


def test_the_preview_is_served_as_webp(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)
    attachment_id = upload(client, token, complaint_id).get_json()["data"]["attachment"]["id"]

    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}/preview",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.mimetype == "image/webp"
    # The preview must be materially smaller than the original or it is
    # not saving anyone bandwidth.
    assert len(response.data) < len(real_png())


def test_the_preview_is_downscaled(client, alpha):
    from PIL import Image

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)
    attachment_id = upload(
        client, token, complaint_id, data=real_png((2000, 1500))
    ).get_json()["data"]["attachment"]["id"]

    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}/preview",
        headers=auth(token),
    )

    with Image.open(io.BytesIO(response.data)) as image:
        assert max(image.size) <= 480


def test_another_student_cannot_fetch_the_preview(client, alpha):
    make_user(alpha, "owner@test.ng")
    make_user(alpha, "other@test.ng")

    owner = login(client, "owner@test.ng")
    complaint_id = file_complaint(client, owner)
    attachment_id = upload(client, owner, complaint_id).get_json()["data"]["attachment"]["id"]

    other = login(client, "other@test.ng")
    response = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}/preview",
        headers=auth(other),
    )

    assert response.status_code == 404


def test_a_private_attachment_has_a_private_preview(client, alpha):
    """A preview of a staff-only file is still staff-only."""
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student)

    officer = login(client, "officer@test.ng")
    attachment_id = upload(
        client, officer, complaint_id, is_internal="true"
    ).get_json()["data"]["attachment"]["id"]

    blocked = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}/preview",
        headers=auth(student),
    )
    allowed = client.get(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}/preview",
        headers=auth(officer),
    )

    assert blocked.status_code == 404
    assert allowed.status_code == 200


def test_removing_an_attachment_removes_its_preview(client, alpha, app):
    from pathlib import Path

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)
    attachment_id = upload(client, token, complaint_id).get_json()["data"]["attachment"]["id"]

    preview_name = db.session.get(Attachment, attachment_id).thumbnail_name
    preview_path = Path(app.config["UPLOAD_DIR"]) / preview_name
    assert preview_path.exists()

    client.delete(
        f"/api/complaints/{complaint_id}/attachments/{attachment_id}", headers=auth(token)
    )

    assert not preview_path.exists()


def test_location_data_is_not_carried_into_the_preview(client, alpha, app):
    """A photograph of a hostel should not disclose where it was taken."""
    from pathlib import Path

    from PIL import Image

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")
    complaint_id = file_complaint(client, token)

    buffer = io.BytesIO()
    source = Image.new("RGB", (800, 600), (200, 100, 50))
    source.save(buffer, "JPEG", exif=source.getexif().tobytes())

    attachment_id = upload(
        client, token, complaint_id, data=buffer.getvalue(), name="photo.jpg", mime="image/jpeg"
    ).get_json()["data"]["attachment"]["id"]

    preview_name = db.session.get(Attachment, attachment_id).thumbnail_name
    with Image.open(Path(app.config["UPLOAD_DIR"]) / preview_name) as preview:
        assert not preview.getexif()
