from tests.conftest import auth, login, make_user


def test_only_institution_admins_may_list_users(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")
    make_user(alpha, "admin@test.ng", role="institution_admin")

    assert client.get("/api/admin/users",
                      headers=auth(login(client, "student@test.ng"))).status_code == 403
    assert client.get("/api/admin/users",
                      headers=auth(login(client, "officer@test.ng"))).status_code == 403
    assert client.get("/api/admin/users",
                      headers=auth(login(client, "admin@test.ng"))).status_code == 200


def test_user_list_never_crosses_institutions(client, alpha, beta):
    make_user(alpha, "alpha.admin@test.ng", role="institution_admin")
    make_user(beta, "beta.student@test.ng")

    token = login(client, "alpha.admin@test.ng")
    users = client.get("/api/admin/users", headers=auth(token)).get_json()["data"]["users"]

    emails = {u["email"] for u in users}
    assert "beta.student@test.ng" not in emails


def test_admin_cannot_create_an_account_above_their_own_role(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    response = client.post(
        "/api/admin/staff",
        headers=auth(token),
        json={
            "full_name": "Escalation Attempt",
            "email": "new@test.ng",
            "password": "Password123",
            "role": "platform_admin",
        },
    )

    assert response.status_code == 422
    assert "role" in response.get_json()["errors"]


def test_admin_can_create_an_officer(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    response = client.post(
        "/api/admin/staff",
        headers=auth(token),
        json={
            "full_name": "New Officer",
            "email": "officer@test.ng",
            "password": "Password123",
            "role": "officer",
        },
    )

    assert response.status_code == 201
    created = response.get_json()["data"]["user"]
    assert created["role"] == "officer"
    assert created["institution_id"] == alpha.id


def test_admin_cannot_deactivate_themselves(client, alpha):
    admin = make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    response = client.put(f"/api/admin/users/{admin.id}/toggle-active", headers=auth(token))

    assert response.status_code == 409


def test_admin_cannot_deactivate_a_user_across_institutions(client, alpha, beta):
    make_user(alpha, "alpha.admin@test.ng", role="institution_admin")
    victim = make_user(beta, "beta.student@test.ng")

    token = login(client, "alpha.admin@test.ng")
    response = client.put(f"/api/admin/users/{victim.id}/toggle-active", headers=auth(token))

    assert response.status_code == 404


def test_settings_reject_an_inverted_working_day(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    response = client.put(
        "/api/admin/settings",
        headers=auth(token),
        json={"working_hours_start": 18, "working_hours_end": 9},
    )

    assert response.status_code == 422


def test_department_slugs_are_unique_per_institution(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    first = client.post("/api/admin/departments", headers=auth(token), json={"name": "Examinations"})
    second = client.post("/api/admin/departments", headers=auth(token), json={"name": "Examinations"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_platform_routes_are_closed_to_institution_admins(client, alpha):
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    assert client.get("/api/platform/institutions", headers=auth(token)).status_code == 403


def test_platform_admin_provisions_an_institution_with_its_first_admin(client, db):
    from app.models.user import User

    owner = User(full_name="Platform Owner", email="owner@resolve.ng", role="platform_admin")
    owner.set_password("Password123")
    db.session.add(owner)
    db.session.commit()

    token = login(client, "owner@resolve.ng")
    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Gamma University",
            "code": "GMU",
            "slug": "gamma-university",
            "admin_name": "Gamma Admin",
            "admin_email": "admin@gamma.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["institution"]["code"] == "GMU"
    assert data["admin"]["role"] == "institution_admin"

    # The new administrator can sign in immediately.
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@gamma.edu.ng", "password": "Password123"},
    ).status_code == 200
