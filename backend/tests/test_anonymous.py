"""Anonymous complaints.

The reports least likely to be made are the ones about the people who
would read them. Anonymity is the only reason some of these arrive at
all, so the failure modes worth testing are the quiet ones: a request
for anonymity that is not honoured, and an author who leaks through a
field nobody thought about.
"""

from app.extensions import db
from app.models.complaint import Complaint
from tests.conftest import auth, login, make_user

BODY = "A lecturer asked for payment before releasing continuous assessment scores."


def file_complaint(client, token, **overrides):
    payload = {
        "title": "Payment demanded for marks",
        "description": BODY,
        "category": "misconduct",
        "priority": "high",
    }
    payload.update(overrides)
    return client.post("/api/complaints", headers=auth(token), json=payload)


def student_token(client, institution, email="student@test.ng"):
    make_user(institution, email)
    return login(client, email)


def test_an_anonymous_complaint_hides_its_author_from_staff(client, alpha):
    alpha.allow_anonymous = True
    db.session.commit()
    token = student_token(client, alpha)

    created = file_complaint(client, token, is_anonymous=True)
    assert created.status_code == 201
    assert created.get_json()["data"]["complaint"]["is_anonymous"] is True

    make_user(alpha, "officer@test.ng", role="institution_admin")
    staff = login(client, "officer@test.ng")

    listed = client.get("/api/complaints", headers=auth(staff)).get_json()
    complaints = listed["data"]["complaints"]
    assert len(complaints) == 1
    assert complaints[0]["student"] is None

    detail = client.get(
        f"/api/complaints/{complaints[0]['id']}", headers=auth(staff)
    ).get_json()["data"]["complaint"]
    assert detail["student"] is None

    # The author is still recorded, or the student could not follow their
    # own complaint and the institution could not act on a pattern.
    stored = db.session.get(Complaint, detail["id"])
    assert stored.student_id is not None


def test_a_refused_request_for_anonymity_files_nothing(client, alpha):
    """Filing it under their name anyway is the dangerous outcome.

    A student who believes they are anonymous writes things they would
    not otherwise write. Silently downgrading the request exposes them
    using their own words.
    """
    alpha.allow_anonymous = False
    db.session.commit()
    token = student_token(client, alpha)

    response = file_complaint(client, token, is_anonymous=True)

    assert response.status_code == 422
    assert "is_anonymous" in response.get_json()["errors"]
    assert Complaint.query.count() == 0


def test_an_ordinary_complaint_is_unaffected(client, alpha):
    alpha.allow_anonymous = False
    db.session.commit()
    token = student_token(client, alpha)

    response = file_complaint(client, token)

    assert response.status_code == 201
    assert response.get_json()["data"]["complaint"]["is_anonymous"] is False


def test_the_author_sees_their_own_anonymous_complaint(client, alpha):
    alpha.allow_anonymous = True
    db.session.commit()
    token = student_token(client, alpha)

    created = file_complaint(client, token, is_anonymous=True).get_json()
    ticket = created["data"]["complaint"]["ticket_number"]

    mine = client.get("/api/complaints", headers=auth(token)).get_json()
    assert [c["ticket_number"] for c in mine["data"]["complaints"]] == [ticket]


def test_a_student_is_told_whether_anonymity_is_available(client, alpha):
    """The answer changes what a student is willing to write."""
    alpha.allow_anonymous = True
    db.session.commit()
    make_user(alpha, "student@test.ng")

    body = client.post(
        "/api/auth/login",
        json={
            "institution": alpha.slug,
            "email": "student@test.ng",
            "password": "Password123",
        },
    ).get_json()

    assert body["data"]["institution"]["allow_anonymous"] is True


def test_a_new_institution_accepts_anonymous_complaints(client, alpha):
    """Off by default meant the feature existed and was never reachable."""
    make_user(alpha, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Beta University",
            "code": "BU",
            "slug": "beta-university",
            "admin_name": "Beta Admin",
            "admin_email": "admin@beta.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    from app.models.institution import Institution

    assert Institution.query.filter_by(slug="beta-university").one().allow_anonymous
