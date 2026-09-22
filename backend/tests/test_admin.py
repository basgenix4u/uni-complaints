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


def test_a_provisioned_institution_is_open_for_business(client, db):
    """Provisioning is the act of bringing an institution into service.

    is_onboarded defaults to false because the directory also lists
    institutions we merely know of. Inheriting that default here meant
    every institution created through the API was dead on arrival: no
    student could register, and no endpoint existed to change it.
    """
    from app.models.institution import Institution

    make_user(None, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Kano State University",
            "code": "KSU",
            "slug": "kano-state",
            "admin_name": "The Registrar",
            "admin_email": "registrar@ksu.test",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    institution = Institution.query.filter_by(slug="kano-state").first()
    assert institution.is_onboarded is True
    # Open on day one, because the register is empty until a registrar
    # uploads one. Starting in register mode rejects every student.
    assert institution.verification_mode == "open"


def test_a_student_can_register_at_a_newly_provisioned_institution(client, db):
    """The end to end consequence of the flag, rather than the flag itself."""
    make_user(None, "platform@test.ng", role="platform_admin")
    client.post(
        "/api/platform/institutions",
        headers=auth(login(client, "platform@test.ng")),
        json={
            "name": "Kano State University",
            "code": "KSU",
            "slug": "kano-state",
            "admin_name": "The Registrar",
            "admin_email": "registrar@ksu.test",
            "admin_password": "Password123",
        },
    )

    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@ksu.test",
            "password": "Password123",
            "institution": "kano-state",
        },
    )

    assert response.status_code == 201, response.get_json()


def test_the_platform_can_take_an_institution_out_of_service(client, db):
    from app.models.institution import Institution

    make_user(None, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")
    created = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Kano State University",
            "code": "KSU",
            "slug": "kano-state",
            "admin_name": "The Registrar",
            "admin_email": "registrar@ksu.test",
            "admin_password": "Password123",
        },
    ).get_json()["data"]["institution"]["id"]

    response = client.put(
        f"/api/platform/institutions/{created}/onboarding",
        headers=auth(token),
        json={"is_onboarded": False},
    )

    assert response.status_code == 200
    assert Institution.query.get(created).is_onboarded is False

    blocked = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@ksu.test",
            "password": "Password123",
            "institution": "kano-state",
        },
    )
    assert blocked.status_code == 409


def test_the_verification_mode_can_be_switched_once_a_register_exists(client, db):
    from app.models.institution import Institution

    make_user(None, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")
    created = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Kano State University",
            "code": "KSU",
            "slug": "kano-state",
            "admin_name": "The Registrar",
            "admin_email": "registrar@ksu.test",
            "admin_password": "Password123",
        },
    ).get_json()["data"]["institution"]["id"]

    response = client.put(
        f"/api/platform/institutions/{created}/onboarding",
        headers=auth(token),
        json={"is_onboarded": True, "verification_mode": "register"},
    )

    assert response.status_code == 200
    assert Institution.query.get(created).verification_mode == "register"


def test_an_invalid_verification_mode_is_refused(client, db):
    make_user(None, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")
    created = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Kano State University",
            "code": "KSU",
            "slug": "kano-state",
            "admin_name": "The Registrar",
            "admin_email": "registrar@ksu.test",
            "admin_password": "Password123",
        },
    ).get_json()["data"]["institution"]["id"]

    response = client.put(
        f"/api/platform/institutions/{created}/onboarding",
        headers=auth(token),
        json={"is_onboarded": True, "verification_mode": "invented"},
    )

    assert response.status_code == 422


def test_an_institution_admin_cannot_change_onboarding(client, alpha):
    """It is a platform decision, not one an institution makes for itself."""
    make_user(alpha, "vc@test.ng", role="institution_admin")

    response = client.put(
        f"/api/platform/institutions/{alpha.id}/onboarding",
        headers=auth(login(client, "vc@test.ng")),
        json={"is_onboarded": True},
    )

    assert response.status_code == 403
