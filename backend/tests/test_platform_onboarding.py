"""Bringing an institution into service.

The directory ships with several hundred institutions, so by the time
anyone is onboarded the entry almost always exists already. The failure
this covers is the one an administrator actually hit: typing the name in
again, and being told the address was in use with no way forward.
"""

from app.extensions import db
from app.models.institution import Institution
from app.models.user import User
from tests.conftest import auth, login, make_institution, make_user


def platform_token(client, institution):
    make_user(institution, "platform@test.ng", role="platform_admin")
    return login(client, "platform@test.ng")


def listed(client, token, **params):
    response = client.get(
        "/api/platform/institutions", headers=auth(token), query_string=params
    )
    assert response.status_code == 200
    return response.get_json()["data"]


def known_but_not_onboarded(name="Bayero University", slug="bayero-university",
                            code="BUK"):
    institution = Institution(
        name=name, slug=slug, code=code, short_name=code,
        state="Kano", type="university", ownership="federal",
        is_onboarded=False, is_active=True,
    )
    db.session.add(institution)
    db.session.commit()
    return institution


def test_an_institution_on_the_register_is_onboarded_without_retyping_it(client, alpha):
    """Only the administrator is new. Everything else is already correct."""
    token = platform_token(client, alpha)
    bayero = known_but_not_onboarded()

    response = client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    body = response.get_json()["data"]
    assert body["institution"]["is_onboarded"] is True
    # Untouched, because they were never asked for.
    assert body["institution"]["name"] == "Bayero University"
    assert body["institution"]["code"] == "BUK"
    assert body["institution"]["slug"] == "bayero-university"
    assert body["units_created"] > 0
    assert body["rules_created"] > 0


def test_the_new_administrator_can_sign_in(client, alpha):
    token = platform_token(client, alpha)
    bayero = known_but_not_onboarded()

    client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    signed_in = client.post(
        "/api/auth/login",
        json={"email": "registrar@buk.edu.ng", "password": "Password123"},
    )

    assert signed_in.status_code == 200
    assert signed_in.get_json()["data"]["user"]["role"] == "institution_admin"


def test_a_student_can_register_only_once_it_is_in_service(client, alpha):
    token = platform_token(client, alpha)
    bayero = known_but_not_onboarded()

    def register():
        return client.post(
            "/api/auth/register",
            json={
                "institution": "bayero-university",
                "full_name": "Amina Yusuf",
                "email": "amina@example.com",
                "password": "Password123",
                "matric_number": "ENG/COE/21/013",
            },
        )

    # Refused while it is only on the register.
    assert register().status_code == 409

    client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert register().status_code == 201


def test_onboarding_something_already_in_service_is_refused(client, alpha):
    token = platform_token(client, alpha)
    bayero = known_but_not_onboarded()
    bayero.is_onboarded = True
    db.session.commit()

    response = client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 409


def test_a_bad_administrator_leaves_the_institution_alone(client, alpha):
    """A rejected request must not half-onboard anything."""
    token = platform_token(client, alpha)
    bayero = known_but_not_onboarded()

    response = client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={"admin_name": "X", "admin_email": "nope", "admin_password": "short"},
    )

    assert response.status_code == 422
    assert db.session.get(Institution, bayero.id).is_onboarded is False
    assert User.query.filter_by(institution_id=bayero.id).count() == 0


def test_a_clash_points_at_the_institution_already_on_the_register(client, alpha):
    """The dead end this replaces.

    Retyping an institution that exists returned "that address is already
    in use" and nothing else, leaving the administrator on a form with no
    way forward. The matched row now comes back with the error.
    """
    token = platform_token(client, alpha)
    known_but_not_onboarded()

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Bayero University",
            "code": "BUKTWO",
            "slug": "bayero-university",
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 409
    errors = response.get_json()["errors"]
    assert errors["can_onboard"] is True
    assert errors["existing"]["slug"] == "bayero-university"
    assert errors["existing"]["id"]


def test_a_clash_on_the_ticket_prefix_says_who_holds_it(client, alpha):
    token = platform_token(client, alpha)
    known_but_not_onboarded()

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Somewhere Else",
            "code": "BUK",
            "slug": "somewhere-else",
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@elsewhere.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["errors"]["existing"]["name"] == "Bayero University"


def test_the_list_shows_institutions_in_service_by_default(client, alpha):
    """Several hundred register entries would bury the handful that matter."""
    token = platform_token(client, alpha)
    known_but_not_onboarded()

    body = listed(client, token)

    slugs = [i["slug"] for i in body["institutions"]]
    assert alpha.slug in slugs
    assert "bayero-university" not in slugs


def test_the_register_can_be_listed_and_searched(client, alpha):
    token = platform_token(client, alpha)
    known_but_not_onboarded()

    on_register = listed(client, token, scope="directory")
    assert [i["slug"] for i in on_register["institutions"]] == ["bayero-university"]

    found = listed(client, token, scope="all", q="BUK")
    assert [i["slug"] for i in found["institutions"]] == ["bayero-university"]

    assert listed(client, token, scope="all", q="nothing here")["institutions"] == []


def test_the_list_is_paged(client, alpha):
    token = platform_token(client, alpha)
    for n in range(5):
        known_but_not_onboarded(f"Institution {n}", f"institution-{n}", f"INST{n}")

    first = listed(client, token, scope="directory", limit=2)

    assert len(first["institutions"]) == 2
    assert first["total"] == 5


def test_user_counts_are_still_reported(client, alpha):
    token = platform_token(client, alpha)
    make_user(alpha, "student@test.ng")

    body = listed(client, token)
    row = next(i for i in body["institutions"] if i["slug"] == alpha.slug)

    assert row["user_count"] >= 2


def test_only_a_platform_admin_may_onboard(client, alpha):
    bayero = known_but_not_onboarded()
    make_user(alpha, "admin@test.ng", role="institution_admin")
    token = login(client, "admin@test.ng")

    response = client.post(
        f"/api/platform/institutions/{bayero.id}/onboard",
        headers=auth(token),
        json={
            "admin_name": "Registrar Bello",
            "admin_email": "registrar@buk.edu.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 403


def test_the_listing_carries_what_the_picker_needs_to_tell_them_apart(client, alpha):
    """Names collide; the acronym and ownership are what disambiguate.

    The admin listing serialises with to_dict rather than the directory
    payload, and those fields were missing from it, so the picker showed
    a blank line under every name.
    """
    token = platform_token(client, alpha)
    known_but_not_onboarded()

    body = listed(client, token, scope="directory")
    row = next(i for i in body["institutions"] if i["slug"] == "bayero-university")

    assert row["short_name"] == "BUK"
    assert row["state"] == "Kano"
    assert row["ownership"] == "federal"
    assert row["type"] == "university"
