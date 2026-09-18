from tests.conftest import auth, login, make_user


def test_registration_requires_known_institution(client, alpha):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "does-not-exist",
        },
    )
    assert response.status_code == 422
    assert "institution" in response.get_json()["errors"]


def test_registration_normalises_matric_number(client, alpha):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "alpha-university",
            "matric_number": "eng-coe-21-013",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["user"]["matric_number"] == "ENG/COE/21/013"


def test_weak_password_is_rejected(client, alpha):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "password",
            "institution": "alpha-university",
        },
    )
    assert response.status_code == 422
    assert "password" in response.get_json()["errors"]


def test_login_does_not_reveal_whether_account_exists(client, alpha):
    make_user(alpha, "known@test.ng")

    missing = client.post("/api/auth/login", json={"email": "nobody@test.ng", "password": "Password123"})
    wrong = client.post("/api/auth/login", json={"email": "known@test.ng", "password": "WrongPass123"})

    assert missing.status_code == wrong.status_code == 401
    assert missing.get_json()["message"] == wrong.get_json()["message"]


def test_deactivated_account_is_refused(client, alpha, db):
    user = make_user(alpha, "blocked@test.ng")
    token = login(client, "blocked@test.ng")

    user.is_active = False
    db.session.commit()

    # The existing token stops working immediately, not at expiry.
    response = client.get("/api/auth/me", headers=auth(token))
    assert response.status_code == 401


def test_protected_route_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401
