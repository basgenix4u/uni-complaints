from datetime import timedelta

from app.extensions import db
from app.models.base import utcnow
from app.models.message import OutboundMessage
from app.models.reset import PasswordReset, hash_token
from tests.conftest import login, make_user


def request_reset(client, email):
    return client.post("/api/auth/forgot-password", json={"email": email})


def token_for(email):
    """Reads the raw token out of the queued email."""
    message = (
        OutboundMessage.query.filter_by(recipient=email)
        .order_by(OutboundMessage.created_at.desc())
        .first()
    )
    return message.body.split("token=")[1].split()[0] if message else None


def test_reset_does_not_reveal_whether_an_account_exists(client, alpha):
    """Disclosing registration would reveal who has complained."""
    make_user(alpha, "known@test.ng")

    known = request_reset(client, "known@test.ng")
    unknown = request_reset(client, "nobody@test.ng")

    assert known.status_code == unknown.status_code == 200
    assert known.get_json()["message"] == unknown.get_json()["message"]


def test_a_reset_email_is_queued_for_a_real_account(client, alpha):
    make_user(alpha, "student@test.ng")

    request_reset(client, "student@test.ng")

    message = OutboundMessage.query.filter_by(recipient="student@test.ng").first()
    assert message is not None
    assert "token=" in message.body


def test_no_email_is_queued_for_an_unknown_address(client, alpha):
    request_reset(client, "nobody@test.ng")

    assert OutboundMessage.query.count() == 0


def test_only_the_hash_of_a_token_is_stored(client, alpha):
    """A stolen backup must not hand over working reset links."""
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    raw = token_for("student@test.ng")
    record = PasswordReset.query.first()

    assert record.token_hash != raw
    assert record.token_hash == hash_token(raw)


def test_a_token_lets_the_password_be_changed(client, alpha):
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_for("student@test.ng"), "password": "BrandNew123"},
    )

    assert response.status_code == 200
    assert (
        client.post(
            "/api/auth/login", json={"email": "student@test.ng", "password": "BrandNew123"}
        ).status_code
        == 200
    )


def test_the_old_password_stops_working(client, alpha):
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    client.post(
        "/api/auth/reset-password",
        json={"token": token_for("student@test.ng"), "password": "BrandNew123"},
    )

    assert (
        client.post(
            "/api/auth/login", json={"email": "student@test.ng", "password": "Password123"}
        ).status_code
        == 401
    )


def test_a_token_cannot_be_used_twice(client, alpha):
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")
    raw = token_for("student@test.ng")

    first = client.post("/api/auth/reset-password", json={"token": raw, "password": "BrandNew123"})
    second = client.post("/api/auth/reset-password", json={"token": raw, "password": "Another123"})

    assert first.status_code == 200
    assert second.status_code == 400


def test_an_expired_token_is_refused(client, alpha):
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    record = PasswordReset.query.first()
    record.expires_at = utcnow() - timedelta(minutes=1)
    db.session.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_for("student@test.ng"), "password": "BrandNew123"},
    )

    assert response.status_code == 400


def test_requesting_again_retires_the_previous_token(client, alpha):
    """A forwarded older email must not still work."""
    make_user(alpha, "student@test.ng")

    request_reset(client, "student@test.ng")
    first = token_for("student@test.ng")

    request_reset(client, "student@test.ng")
    second = token_for("student@test.ng")

    assert first != second
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": first, "password": "BrandNew123"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": second, "password": "BrandNew123"}
        ).status_code
        == 200
    )


def test_an_invented_token_is_refused(client, alpha):
    make_user(alpha, "student@test.ng")

    response = client.post(
        "/api/auth/reset-password", json={"token": "not-a-real-token", "password": "BrandNew123"}
    )

    assert response.status_code == 400


def test_the_password_policy_still_applies(client, alpha):
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_for("student@test.ng"), "password": "weak"},
    )

    assert response.status_code == 422


def test_a_deactivated_account_cannot_be_reset(client, alpha):
    user = make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")
    raw = token_for("student@test.ng")

    user.is_active = False
    db.session.commit()

    response = client.post("/api/auth/reset-password", json={"token": raw, "password": "BrandNew123"})

    assert response.status_code == 400


def test_a_confirmation_is_sent_after_the_change(client, alpha):
    """Tells someone their account was taken over, if it was."""
    make_user(alpha, "student@test.ng")
    request_reset(client, "student@test.ng")

    client.post(
        "/api/auth/reset-password",
        json={"token": token_for("student@test.ng"), "password": "BrandNew123"},
    )

    subjects = [m.subject for m in OutboundMessage.query.all()]
    assert "Your password was changed" in subjects
