"""Staff invitations.

The demo had an administrator type a colleague's password into a form.
That is wrong twice: one person then knows another's credentials, and
nobody does it three hundred times. These cover the replacement, and in
particular that an invitation cannot be used to gain more access than it
offered.
"""

import io

from app.extensions import db
from app.models.academic import Faculty
from app.models.institution import Department
from app.models.invitation import Invitation
from app.models.message import OutboundMessage
from app.models.user import User
from tests.conftest import auth, login, make_user


def faculty_for(institution, name="Engineering", slug="engineering"):
    record = Faculty(institution_id=institution.id, name=name, slug=slug)
    db.session.add(record)
    db.session.commit()
    return record


def unit_for(institution, name="Bursary", slug="bursary"):
    existing = Department.query.filter_by(institution_id=institution.id, slug=slug).first()
    if existing:
        return existing
    record = Department(institution_id=institution.id, name=name, slug=slug)
    db.session.add(record)
    db.session.commit()
    return record


def token_from_email(email: str) -> str | None:
    message = (
        OutboundMessage.query.filter_by(recipient=email)
        .order_by(OutboundMessage.created_at.desc())
        .first()
    )
    return message.body.split("token=")[1].split()[0] if message else None


def invite(client, token, **payload):
    return client.post("/api/invitations", headers=auth(token), json=payload)


# -- issuing ----------------------------------------------------------


def test_an_administrator_can_invite_an_officer(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")

    response = invite(
        client, admin, email="grace@test.ng", role="officer", department_id=unit.id
    )

    assert response.status_code == 201
    assert Invitation.query.count() == 1
    assert token_from_email("grace@test.ng") is not None


def test_no_password_is_ever_set_by_the_inviter(client, alpha):
    """The whole point: nobody knows anyone else's password."""
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")

    invite(client, admin, email="grace@test.ng", role="officer", department_id=unit.id)

    # No account exists until the person accepts and chooses one.
    assert User.query.filter_by(email="grace@test.ng").first() is None


def test_only_the_hash_of_a_token_is_stored(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")

    invite(client, admin, email="grace@test.ng", role="officer", department_id=unit.id)

    raw = token_from_email("grace@test.ng")
    assert Invitation.query.first().token_hash != raw


def test_nobody_can_invite_above_their_own_role(client, alpha):
    make_user(alpha, "head@test.ng", role="dept_head")
    unit = unit_for(alpha)
    make_user(alpha, "head2@test.ng", role="dept_head")
    User.query.filter_by(email="head@test.ng").first().department_id = unit.id
    db.session.commit()

    head = login(client, "head@test.ng")
    response = invite(
        client, head, email="new@test.ng", role="institution_admin", department_id=unit.id
    )

    assert response.status_code == 422
    assert "role" in response.get_json()["errors"]


def test_a_unit_head_can_only_invite_into_their_own_unit(client, alpha):
    bursary = unit_for(alpha, "Bursary", "bursary")
    registry = unit_for(alpha, "Registry", "registry")

    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = bursary.id
    db.session.commit()

    token = login(client, "head@test.ng")
    response = invite(
        client, token, email="new@test.ng", role="officer", department_id=registry.id
    )

    assert response.status_code == 422


def test_an_officer_cannot_invite_at_all(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    unit = unit_for(alpha)
    token = login(client, "officer@test.ng")

    assert invite(
        client, token, email="new@test.ng", role="officer", department_id=unit.id
    ).status_code == 403


def test_a_dean_invitation_needs_a_faculty(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    admin = login(client, "admin@test.ng")

    response = invite(client, admin, email="dean@test.ng", role="dean")

    assert response.status_code == 422


def test_inviting_an_existing_account_is_refused(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    make_user(alpha, "grace@test.ng", role="officer")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")

    response = invite(
        client, admin, email="grace@test.ng", role="officer", department_id=unit.id
    )

    assert response.status_code == 409


def test_a_second_pending_invitation_is_refused(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")

    invite(client, admin, email="grace@test.ng", role="officer", department_id=unit.id)
    again = invite(client, admin, email="grace@test.ng", role="officer", department_id=unit.id)

    assert again.status_code == 409


def test_a_unit_from_another_institution_is_refused(client, alpha, beta):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    other_unit = unit_for(beta, "Beta Bursary", "beta-bursary")
    admin = login(client, "admin@test.ng")

    response = invite(
        client, admin, email="grace@test.ng", role="officer", department_id=other_unit.id
    )

    assert response.status_code == 422


# -- accepting --------------------------------------------------------


def accept(client, token, password="Password123", full_name="Grace Okon"):
    return client.post(
        "/api/invitations/accept",
        json={"token": token, "password": password, "full_name": full_name},
    )


def issued(client, alpha, role="officer", **extra):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)
    admin = login(client, "admin@test.ng")
    invite(
        client, admin, email="grace@test.ng", role=role,
        department_id=extra.pop("department_id", unit.id), **extra,
    )
    return token_from_email("grace@test.ng")


def test_accepting_creates_the_account(client, alpha):
    raw = issued(client, alpha)

    response = accept(client, raw)

    assert response.status_code == 201
    user = User.query.filter_by(email="grace@test.ng").first()
    assert user.role == "officer"
    assert user.is_active is True


def test_the_new_account_can_sign_in(client, alpha):
    raw = issued(client, alpha)
    accept(client, raw, password="MyOwnPass123")

    response = client.post(
        "/api/auth/login", json={"email": "grace@test.ng", "password": "MyOwnPass123"}
    )

    assert response.status_code == 200


def test_the_role_comes_from_the_invitation_not_the_request(client, alpha):
    """A recipient must not be able to promote themselves."""
    raw = issued(client, alpha, role="officer")

    client.post(
        "/api/invitations/accept",
        json={
            "token": raw,
            "password": "Password123",
            "full_name": "Grace Okon",
            # Ignored: the role is fixed at invitation time.
            "role": "institution_admin",
            "institution_id": "somewhere-else",
        },
    )

    assert User.query.filter_by(email="grace@test.ng").first().role == "officer"


def test_the_email_comes_from_the_invitation(client, alpha):
    """Otherwise an invitation could be redirected to another address."""
    raw = issued(client, alpha)

    client.post(
        "/api/invitations/accept",
        json={
            "token": raw,
            "password": "Password123",
            "full_name": "Grace Okon",
            "email": "attacker@test.ng",
        },
    )

    assert User.query.filter_by(email="attacker@test.ng").first() is None
    assert User.query.filter_by(email="grace@test.ng").first() is not None


def test_a_token_cannot_be_used_twice(client, alpha):
    raw = issued(client, alpha)

    first = accept(client, raw)
    second = accept(client, raw)

    assert first.status_code == 201
    assert second.status_code == 400


def test_an_expired_invitation_is_refused(client, alpha):
    from datetime import timedelta

    from app.models.base import utcnow

    raw = issued(client, alpha)
    invitation = Invitation.query.first()
    invitation.expires_at = utcnow() - timedelta(days=1)
    db.session.commit()

    assert accept(client, raw).status_code == 400


def test_a_revoked_invitation_is_refused(client, alpha):
    raw = issued(client, alpha)
    Invitation.query.first().revoke()
    db.session.commit()

    assert accept(client, raw).status_code == 400


def test_an_invented_token_is_refused(client, alpha):
    assert accept(client, "not-a-real-token").status_code == 400


def test_the_password_policy_applies(client, alpha):
    raw = issued(client, alpha)

    assert accept(client, raw, password="weak").status_code == 422


def test_preview_describes_the_invitation_without_accepting_it(client, alpha):
    raw = issued(client, alpha)

    response = client.get(f"/api/invitations/preview?token={raw}")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["email"] == "grace@test.ng"
    assert data["role"] == "officer"
    assert Invitation.query.first().status == "pending"


# -- managing ---------------------------------------------------------


def test_resending_issues_a_new_token(client, alpha):
    """A message forwarded to the wrong person must stop working."""
    raw = issued(client, alpha)
    admin = login(client, "admin@test.ng")
    invitation = Invitation.query.first()

    client.post(f"/api/invitations/{invitation.id}/resend", headers=auth(admin))

    assert token_from_email("grace@test.ng") != raw
    assert accept(client, raw).status_code == 400


def test_an_accepted_invitation_cannot_be_revoked(client, alpha):
    raw = issued(client, alpha)
    accept(client, raw)
    admin = login(client, "admin@test.ng")

    invitation = Invitation.query.first()
    response = client.delete(f"/api/invitations/{invitation.id}", headers=auth(admin))

    assert response.status_code == 409


def test_a_unit_head_sees_only_their_own_units_invitations(client, alpha):
    bursary = unit_for(alpha, "Bursary", "bursary")
    registry = unit_for(alpha, "Registry", "registry")

    make_user(alpha, "admin@test.ng", role="institution_admin")
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = bursary.id
    db.session.commit()

    admin = login(client, "admin@test.ng")
    invite(client, admin, email="one@test.ng", role="officer", department_id=bursary.id)
    invite(client, admin, email="two@test.ng", role="officer", department_id=registry.id)

    head_token = login(client, "head@test.ng")
    rows = client.get("/api/invitations", headers=auth(head_token)).get_json()["data"][
        "invitations"
    ]

    assert {r["email"] for r in rows} == {"one@test.ng"}


def test_invitations_do_not_cross_institutions(client, alpha, beta):
    make_user(alpha, "alpha.admin@test.ng", role="institution_admin")
    make_user(beta, "beta.admin@test.ng", role="institution_admin")
    unit = unit_for(alpha)

    admin = login(client, "alpha.admin@test.ng")
    invite(client, admin, email="grace@test.ng", role="officer", department_id=unit.id)

    other = login(client, "beta.admin@test.ng")
    rows = client.get("/api/invitations", headers=auth(other)).get_json()["data"]["invitations"]

    assert rows == []


# -- bulk -------------------------------------------------------------


def bulk(client, token, csv_text, dry_run=False):
    return client.post(
        "/api/invitations/bulk",
        headers=auth(token),
        data={
            "file": (io.BytesIO(csv_text.strip().encode()), "staff.csv"),
            "dry_run": "true" if dry_run else "false",
        },
        content_type="multipart/form-data",
    )


def test_many_staff_are_invited_from_one_file(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit_for(alpha, "Bursary", "bursary")
    unit_for(alpha, "Registry", "registry")
    admin = login(client, "admin@test.ng")

    response = bulk(
        client, admin,
        """
email,full_name,role,unit
grace@test.ng,Grace Okon,officer,Bursary
ibrahim@test.ng,Ibrahim Sani,dept_head,Registry
""",
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["summary"]["invited"] == 2
    assert Invitation.query.count() == 2


def test_a_bulk_dry_run_changes_nothing(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit_for(alpha)
    admin = login(client, "admin@test.ng")

    response = bulk(
        client, admin,
        "email,role,unit\ngrace@test.ng,officer,Bursary",
        dry_run=True,
    )

    assert response.get_json()["data"]["summary"]["invited"] == 1
    assert Invitation.query.count() == 0


def test_bad_rows_are_reported_and_good_ones_still_go(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit_for(alpha)
    admin = login(client, "admin@test.ng")

    summary = bulk(
        client, admin,
        """
email,role,unit
not-an-email,officer,Bursary
grace@test.ng,officer,Bursary
ibrahim@test.ng,officer,Nowhere
""",
    ).get_json()["data"]["summary"]

    assert summary["invited"] == 1
    assert summary["skipped"] == 2
    assert any("not-an-email" in p for p in summary["problems"])
    assert any("nowhere" in p.lower() for p in summary["problems"])


def test_a_duplicate_inside_the_file_is_invited_once(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit_for(alpha)
    admin = login(client, "admin@test.ng")

    summary = bulk(
        client, admin,
        """
email,role,unit
grace@test.ng,officer,Bursary
grace@test.ng,officer,Bursary
""",
    ).get_json()["data"]["summary"]

    assert summary["invited"] == 1
    assert summary["skipped"] == 1


def test_bulk_cannot_grant_more_access_than_the_caller_has(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    unit_for(alpha)
    admin = login(client, "admin@test.ng")

    summary = bulk(
        client, admin,
        "email,role,unit\nsomeone@test.ng,platform_admin,Bursary",
    ).get_json()["data"]["summary"]

    assert summary["invited"] == 0
    assert Invitation.query.count() == 0


def test_a_unit_head_cannot_bulk_invite(client, alpha):
    unit = unit_for(alpha)
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = unit.id
    db.session.commit()

    token = login(client, "head@test.ng")
    response = bulk(client, token, "email,role,unit\ngrace@test.ng,officer,Bursary")

    assert response.status_code == 403


def test_a_file_without_an_email_column_is_refused(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    admin = login(client, "admin@test.ng")

    response = bulk(client, admin, "name,role\nGrace,officer")

    assert response.status_code == 422
