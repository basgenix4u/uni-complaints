"""Email verification and registration approval.

Nothing previously stopped somebody registering with an address that was
not theirs, which for a complaints system means a grievance carrying
someone's name and matriculation number could land in a stranger's inbox.

The two questions are kept apart on purpose: *is this address yours* is
answered by a link, and *are you a student here* is answered by the
register or by a person.
"""

from app.extensions import db
from app.models.academic import AcademicSession, Faculty, StudentRecord
from app.models.message import OutboundMessage
from app.models.user import User
from app.models.verification import EmailVerification, hash_token
from app.services.register import import_register
from tests.conftest import auth, login, make_institution, make_user

SIGNUP = {
    "full_name": "Amina Yusuf",
    "email": "amina@test.ng",
    "password": "Password123",
    "institution": "alpha-university",
}

COMPLAINT = {
    "title": "Fees receipt not reflecting",
    "description": "I paid my school fees three weeks ago and the portal still shows unpaid.",
    "category": "fees_payment",
    "priority": "medium",
}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**SIGNUP, **overrides})


def token_for(email):
    """The raw token is only ever emailed, so it is recovered from the link."""
    message = (
        OutboundMessage.query.filter_by(recipient=email)
        .order_by(OutboundMessage.created_at.desc())
        .first()
    )
    assert message, "no email was queued"
    for part in message.body.split():
        if "verify-email?token=" in part:
            return part.split("token=", 1)[1]
    raise AssertionError(f"no verification link in: {message.body}")


# -- the address ------------------------------------------------------


def test_registration_sends_a_confirmation_email(client, alpha):
    response = register(client)

    assert response.status_code == 201
    assert response.get_json()["data"]["verification_required"] is True
    assert OutboundMessage.query.filter_by(recipient="amina@test.ng").count() == 1


def test_a_new_account_starts_unverified(client, alpha):
    register(client)
    assert User.query.filter_by(email="amina@test.ng").first().is_verified is False


def test_an_unverified_student_cannot_file(client, alpha):
    """The whole point: an unproven address cannot raise a complaint."""
    register(client)
    token = login(client, "amina@test.ng")

    response = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)

    assert response.status_code == 403
    assert "confirm your email" in response.get_json()["message"].lower()


def test_an_unverified_student_can_still_sign_in(client, alpha):
    """Locking them out would leave an error screen and nowhere to go."""
    register(client)
    token = login(client, "amina@test.ng")

    status = client.get("/api/auth/verification-status", headers=auth(token))

    assert status.status_code == 200
    assert status.get_json()["data"]["can_file"] is False


def test_confirming_the_link_allows_filing(client, alpha):
    register(client)
    raw = token_for("amina@test.ng")

    confirmed = client.post("/api/auth/verify-email", json={"token": raw})
    assert confirmed.status_code == 200

    token = login(client, "amina@test.ng")
    assert client.post("/api/complaints", headers=auth(token), json=COMPLAINT).status_code == 201


def test_a_token_cannot_be_used_twice(client, alpha):
    register(client)
    raw = token_for("amina@test.ng")

    client.post("/api/auth/verify-email", json={"token": raw})
    db.session.expire_all()

    # Already verified, so replaying is harmless rather than an error.
    again = client.post("/api/auth/verify-email", json={"token": raw})
    assert again.status_code == 400


def test_a_forged_token_is_refused(client, alpha):
    register(client)
    response = client.post("/api/auth/verify-email", json={"token": "not-a-real-token"})

    assert response.status_code == 400


def test_an_expired_token_is_refused(client, alpha, db):
    from datetime import timedelta

    from app.models.base import utcnow

    register(client)
    raw = token_for("amina@test.ng")

    record = EmailVerification.query.filter_by(token_hash=hash_token(raw)).first()
    record.expires_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    assert client.post("/api/auth/verify-email", json={"token": raw}).status_code == 400


def test_only_the_hash_is_stored(client, alpha):
    """A stolen backup must not yield working links."""
    register(client)
    raw = token_for("amina@test.ng")

    record = EmailVerification.query.first()
    assert record.token_hash != raw
    assert record.token_hash == hash_token(raw)


def test_requesting_a_new_link_retires_the_old_one(client, alpha, db):
    from datetime import timedelta

    from app.models.base import utcnow

    register(client)
    first = token_for("amina@test.ng")

    # Past the resend interval, which exists so this is not a way to have
    # us send mail on demand.
    record = EmailVerification.query.first()
    record.last_sent_at = utcnow() - timedelta(minutes=5)
    db.session.commit()

    client.post("/api/auth/resend-verification", json={"email": "amina@test.ng"})

    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400


def test_resending_is_rate_limited(client, alpha):
    register(client)
    response = client.post("/api/auth/resend-verification", json={"email": "amina@test.ng"})

    assert response.status_code == 200
    assert "moment ago" in response.get_json()["message"]


def test_resending_does_not_reveal_whether_an_account_exists(client, alpha):
    known = client.post("/api/auth/resend-verification", json={"email": "nobody@test.ng"})

    assert known.status_code == 200
    assert "if that address" in known.get_json()["message"].lower()


def test_staff_who_accept_an_invitation_are_already_verified(client, alpha, db):
    """The link only ever went to that address; a second email is theatre."""
    from app.models.invitation import Invitation

    from app.models.institution import Department

    make_user(alpha, "vc@test.ng", role="institution_admin")
    token = login(client, "vc@test.ng")
    bursary = Department.query.filter_by(institution_id=alpha.id, slug="bursary").first()

    invited = client.post(
        "/api/invitations",
        headers=auth(token),
        json={
            "email": "officer@test.ng",
            "role": "officer",
            "full_name": "New Officer",
            "department_id": bursary.id,
        },
    )
    assert invited.status_code == 201, invited.get_json()

    invitation = Invitation.query.filter_by(email="officer@test.ng").first()
    message = (
        OutboundMessage.query.filter_by(recipient="officer@test.ng")
        .order_by(OutboundMessage.created_at.desc())
        .first()
    )
    raw = next(p.split("token=", 1)[1] for p in message.body.split() if "token=" in p)

    accepted = client.post(
        "/api/invitations/accept",
        json={"token": raw, "password": "Password123", "full_name": "New Officer"},
    )
    assert accepted.status_code == 201
    assert invitation is not None

    officer = User.query.filter_by(email="officer@test.ng").first()
    assert officer.is_verified is True


# -- are you a student here -------------------------------------------


def register_backed_institution():
    """An institution that checks registrations against its register."""
    institution = make_institution(
        code="REG", slug="register-university", name="Register University",
        verification_mode="register",
    )
    session = AcademicSession(
        institution_id=institution.id, name="2025/2026", is_current=True
    )
    db.session.add(session)
    db.session.add(Faculty(institution_id=institution.id, name="Engineering", slug="engineering"))
    db.session.commit()

    import_register(
        institution,
        session,
        b"matric_number,full_name,faculty\nENG/COE/21/013,Amina Yusuf,Engineering",
    )
    return institution


def test_a_student_in_the_register_is_approved_outright(client, db):
    register_backed_institution()

    response = register(
        client, institution="register-university", matric_number="ENG/COE/21/013"
    )

    assert response.status_code == 201
    assert User.query.filter_by(email="amina@test.ng").first().approval_status == "approved"


def test_the_register_fills_in_the_faculty(client, db):
    """Better than a dropdown they guess at: it is the institution's own data."""
    register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/013")

    assert User.query.filter_by(email="amina@test.ng").first().faculty == "Engineering"


def test_registering_claims_the_register_entry(client, db):
    register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/013")

    assert StudentRecord.query.first().claimed_by_user_id is not None


def test_a_claimed_entry_cannot_be_claimed_again(client, db):
    """One of the two is not who they say they are."""
    register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/013")

    second = register(
        client,
        email="impostor@test.ng",
        institution="register-university",
        matric_number="ENG/COE/21/013",
    )

    assert second.status_code == 409


def test_a_student_not_in_the_register_waits_rather_than_being_refused(client, db):
    """Registers are never complete, and a real student should not be turned
    away by a spreadsheet a week out of date."""
    register_backed_institution()

    response = register(
        client, institution="register-university", matric_number="ENG/COE/21/999"
    )

    assert response.status_code == 201
    assert User.query.filter_by(email="amina@test.ng").first().approval_status == "pending"


def test_a_register_institution_asks_for_a_matric_number(client, db):
    register_backed_institution()
    response = register(client, institution="register-university")

    assert response.status_code == 422
    assert "matric_number" in response.get_json()["errors"]


def test_an_open_institution_does_not(client, alpha):
    """Demanding one an institution cannot check proves nothing."""
    assert register(client).status_code == 201


def test_a_pending_student_cannot_file_even_once_verified(client, db):
    register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/999")
    client.post("/api/auth/verify-email", json={"token": token_for("amina@test.ng")})

    token = login(client, "amina@test.ng")
    response = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)

    assert response.status_code == 403
    assert "still checking" in response.get_json()["message"]


def test_an_administrator_sees_why_a_registration_is_waiting(client, db):
    institution = register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/999")
    make_user(institution, "vc@register.ng", role="institution_admin")

    response = client.get(
        "/api/admin/registrations", headers=auth(login(client, "vc@register.ng"))
    )

    assert response.status_code == 200
    rows = response.get_json()["data"]["registrations"]
    assert len(rows) == 1
    assert "not found in the student register" in rows[0]["reason"].lower()


def test_approving_a_registration_lets_the_student_file(client, db):
    institution = register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/999")
    client.post("/api/auth/verify-email", json={"token": token_for("amina@test.ng")})
    make_user(institution, "vc@register.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    decision = client.put(
        f"/api/admin/registrations/{student.id}",
        headers=auth(login(client, "vc@register.ng")),
        json={"decision": "approved"},
    )
    assert decision.status_code == 200

    token = login(client, "amina@test.ng")
    assert client.post("/api/complaints", headers=auth(token), json=COMPLAINT).status_code == 201


def test_a_rejected_student_is_told_why(client, db):
    institution = register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/999")
    client.post("/api/auth/verify-email", json={"token": token_for("amina@test.ng")})
    make_user(institution, "vc@register.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    client.put(
        f"/api/admin/registrations/{student.id}",
        headers=auth(login(client, "vc@register.ng")),
        json={"decision": "rejected"},
    )

    token = login(client, "amina@test.ng")
    response = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)

    assert response.status_code == 403
    assert "could not confirm" in response.get_json()["message"]


def test_an_officer_cannot_approve_registrations(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")

    response = client.get(
        "/api/admin/registrations", headers=auth(login(client, "officer@test.ng"))
    )

    assert response.status_code == 403


def test_registrations_do_not_cross_institutions(client, alpha, db):
    institution = register_backed_institution()
    register(client, institution="register-university", matric_number="ENG/COE/21/999")
    make_user(alpha, "vc@alpha.ng", role="institution_admin")
    assert institution is not None

    response = client.get(
        "/api/admin/registrations", headers=auth(login(client, "vc@alpha.ng"))
    )

    assert response.get_json()["data"]["count"] == 0


# -- when email itself is the problem ----------------------------------


def test_an_administrator_can_confirm_an_address_by_hand(client, alpha):
    """Without this, verification is a door with no key.

    Email is the only way to confirm, so a deployment where email is not
    working is one where nobody can ever finish registering.
    """
    register(client)
    make_user(alpha, "vc@test.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    assert student.is_verified is False

    response = client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "vc@test.ng")),
    )

    assert response.status_code == 200
    assert User.query.filter_by(email="amina@test.ng").first().is_verified is True


def test_a_hand_confirmed_student_can_file(client, alpha):
    register(client)
    make_user(alpha, "vc@test.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "vc@test.ng")),
    )

    token = login(client, "amina@test.ng")
    assert client.post("/api/complaints", headers=auth(token), json=COMPLAINT).status_code == 201


def test_confirming_by_hand_records_who_did_it(client, alpha):
    """An assertion somebody checked, not proof the address works."""
    register(client)
    admin = make_user(alpha, "vc@test.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "vc@test.ng")),
    )

    assert User.query.filter_by(email="amina@test.ng").first().email_verified_by_id == admin.id


def test_confirming_by_hand_retires_outstanding_links(client, alpha):
    register(client)
    raw = token_for("amina@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "vc@test.ng")),
    )

    assert client.post("/api/auth/verify-email", json={"token": raw}).status_code == 400


def test_an_officer_cannot_confirm_someone_elses_address(client, alpha):
    register(client)
    make_user(alpha, "officer@test.ng", role="officer")

    student = User.query.filter_by(email="amina@test.ng").first()
    response = client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "officer@test.ng")),
    )

    assert response.status_code == 403


def test_confirming_does_not_cross_institutions(client, alpha, beta):
    register(client)
    make_user(beta, "vc@beta.ng", role="institution_admin")

    student = User.query.filter_by(email="amina@test.ng").first()
    response = client.put(
        f"/api/admin/registrations/{student.id}/confirm-email",
        headers=auth(login(client, "vc@beta.ng")),
    )

    assert response.status_code == 404


def test_an_unverified_student_appears_in_the_queue(client, alpha):
    """Listing only those awaiting approval would hide exactly the people
    stuck behind an unconfirmed address."""
    register(client)
    make_user(alpha, "vc@test.ng", role="institution_admin")

    rows = client.get(
        "/api/admin/registrations", headers=auth(login(client, "vc@test.ng"))
    ).get_json()["data"]["registrations"]

    assert len(rows) == 1
    assert rows[0]["awaiting_email_only"] is True


def test_the_administrator_is_told_when_email_is_not_working(client, alpha):
    """Otherwise the first sign is students reporting they are stuck."""
    make_user(alpha, "vc@test.ng", role="institution_admin")

    health = client.get(
        "/api/admin/delivery-health", headers=auth(login(client, "vc@test.ng"))
    ).get_json()["data"]["email"]

    assert health["state"] == "not_configured"
    assert "confirm registrations by hand" in health["advice"]


def test_delivery_health_is_not_public(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")

    response = client.get(
        "/api/admin/delivery-health", headers=auth(login(client, "officer@test.ng"))
    )

    assert response.status_code == 403
