"""The institution directory, and demand from institutions not on it.

A student whose university is not using the service used to reach a dead
end: "we could not find that institution", and nothing happened. That is
a wasted signal. Fifty students asking for one university is the argument
for approaching that university.
"""

from app.extensions import db
from app.models.academic import InstitutionInterest
from app.models.institution import Institution
from tests.conftest import auth, login, make_institution, make_user


def waiting_institution(name="Waiting University", slug="waiting-university", code="WTG",
                        state="Kano"):
    """A university we know of that has not signed up."""
    institution = make_institution(code=code, slug=slug, name=name, is_onboarded=False)
    institution.state = state
    db.session.commit()
    return institution


# -- finding an institution -------------------------------------------


def test_the_directory_is_public(client, alpha):
    """A person has to find their institution before they have an account."""
    response = client.get("/api/directory/institutions")

    assert response.status_code == 200
    assert len(response.get_json()["data"]["institutions"]) == 1


def test_searching_narrows_by_name(client, alpha, beta):
    response = client.get("/api/directory/institutions?q=beta")

    rows = response.get_json()["data"]["institutions"]
    assert len(rows) == 1
    assert rows[0]["slug"] == "beta-polytechnic"


def test_searching_matches_the_code(client, alpha):
    """Students say "UNILAG" far more often than the full name."""
    rows = client.get("/api/directory/institutions?q=AAA").get_json()["data"]["institutions"]

    assert len(rows) == 1


def test_institutions_can_be_filtered_by_state(client, alpha, db):
    waiting_institution(state="Kano")

    rows = client.get("/api/directory/institutions?state=Kano").get_json()["data"]["institutions"]

    assert len(rows) == 1
    assert rows[0]["slug"] == "waiting-university"


def test_an_institution_that_has_not_signed_up_is_listed_and_flagged(client, db):
    """A different answer from "never heard of it", and it leads somewhere."""
    waiting_institution()

    rows = client.get("/api/directory/institutions").get_json()["data"]["institutions"]

    assert len(rows) == 1
    assert rows[0]["is_onboarded"] is False


def test_onboarded_institutions_come_first(client, alpha, db):
    """Those are the ones a student can actually use."""
    waiting_institution(name="Aaa Waiting University", slug="aaa-waiting", code="AWU")

    rows = client.get("/api/directory/institutions").get_json()["data"]["institutions"]

    assert rows[0]["is_onboarded"] is True


def test_the_list_can_be_limited_to_those_in_service(client, alpha, db):
    waiting_institution()

    rows = client.get(
        "/api/directory/institutions?onboarded=1"
    ).get_json()["data"]["institutions"]

    assert len(rows) == 1
    assert all(r["is_onboarded"] for r in rows)


def test_a_suspended_institution_is_not_listed(client, alpha, db):
    alpha.is_active = False
    db.session.commit()

    rows = client.get("/api/directory/institutions").get_json()["data"]["institutions"]

    assert rows == []


def test_the_directory_does_not_leak_internal_settings(client, alpha):
    """It is served without authentication, so it carries only what is needed."""
    row = client.get("/api/directory/institutions").get_json()["data"]["institutions"][0]

    for private in ("default_sla_hours", "contact_email", "retention_months", "code"):
        assert private not in row


def test_the_sign_up_form_learns_what_to_ask_for(client, db):
    """No point demanding a matric number an institution cannot check."""
    institution = make_institution(verification_mode="register")
    institution.matric_example = "ENG/COE/21/013"
    db.session.commit()

    row = client.get(
        "/api/directory/institutions/alpha-university"
    ).get_json()["data"]["institution"]

    assert row["verification_mode"] == "register"
    assert row["matric_example"] == "ENG/COE/21/013"


def test_an_unknown_slug_is_reported_clearly(client, alpha):
    assert client.get("/api/directory/institutions/nowhere").status_code == 404


def test_states_are_listed_for_the_filter(client, alpha, db):
    waiting_institution(state="Kano")

    states = client.get("/api/directory/states").get_json()["data"]["states"]

    assert "Kano" in states


# -- registering against one ------------------------------------------


def test_a_student_cannot_register_at_an_institution_that_has_not_signed_up(client, db):
    """There would be nobody on the other end to answer them."""
    waiting_institution()

    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "waiting-university",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["errors"]["can_register_interest"] is True


# -- asking for one to be added ---------------------------------------


def test_a_student_can_ask_for_their_institution(client, db):
    response = client.post(
        "/api/directory/interest",
        json={"institution_name": "Bayero University Kano", "email": "amina@test.ng"},
    )

    assert response.status_code == 200
    assert InstitutionInterest.query.count() == 1


def test_asking_twice_does_not_inflate_the_count(client, db):
    """The number is how many distinct people want it; that is the argument."""
    payload = {"institution_name": "Bayero University Kano", "email": "amina@test.ng"}

    client.post("/api/directory/interest", json=payload)
    second = client.post("/api/directory/interest", json=payload)

    assert second.status_code == 200
    assert InstitutionInterest.query.count() == 1


def test_asking_twice_does_not_reveal_that_the_address_is_on_file(client, db):
    payload = {"institution_name": "Bayero University Kano", "email": "amina@test.ng"}

    first = client.post("/api/directory/interest", json=payload).get_json()["message"]
    second = client.post("/api/directory/interest", json=payload).get_json()["message"]

    assert first == second


def test_an_interest_request_needs_a_usable_address(client, db):
    response = client.post(
        "/api/directory/interest",
        json={"institution_name": "Bayero University Kano", "email": "not-an-address"},
    )

    assert response.status_code == 422
    assert "email" in response.get_json()["errors"]


def test_interest_can_be_attached_to_a_known_institution(client, db):
    """Distinguishes "never heard of it" from "on file but not signed up"."""
    waiting_institution()

    client.post(
        "/api/directory/interest",
        json={
            "institution_name": "Waiting University",
            "email": "amina@test.ng",
            "institution_slug": "waiting-university",
        },
    )

    assert InstitutionInterest.query.first().institution_id is not None


# -- who to approach next ---------------------------------------------


def test_the_platform_sees_which_institutions_are_most_wanted(client, db):
    make_user(None, "platform@test.ng", role="platform_admin")

    for address in ("a@test.ng", "b@test.ng", "c@test.ng"):
        client.post(
            "/api/directory/interest",
            json={"institution_name": "Bayero University Kano", "email": address},
        )
    client.post(
        "/api/directory/interest",
        json={"institution_name": "Federal University Lokoja", "email": "d@test.ng"},
    )

    rows = client.get(
        "/api/platform/demand", headers=auth(login(client, "platform@test.ng"))
    ).get_json()["data"]["demand"]

    assert rows[0]["institution_name"] == "Bayero University Kano"
    assert rows[0]["requests"] == 3
    assert rows[0]["known"] is False


def test_demand_marks_institutions_already_on_file(client, db):
    waiting_institution()
    make_user(None, "platform@test.ng", role="platform_admin")

    client.post(
        "/api/directory/interest",
        json={"institution_name": "Waiting University", "email": "a@test.ng"},
    )

    rows = client.get(
        "/api/platform/demand", headers=auth(login(client, "platform@test.ng"))
    ).get_json()["data"]["demand"]

    assert rows[0]["known"] is True
    assert rows[0]["is_onboarded"] is False


def test_an_institution_admin_cannot_read_platform_demand(client, alpha):
    """It is commercial information across every tenant."""
    make_user(alpha, "vc@test.ng", role="institution_admin")

    response = client.get("/api/platform/demand", headers=auth(login(client, "vc@test.ng")))

    assert response.status_code == 403


def test_onboarding_an_institution_makes_it_registrable(client, db):
    """The whole point of the flag: it gates registration."""
    institution = waiting_institution()

    blocked = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "waiting-university",
        },
    )
    assert blocked.status_code == 409

    institution.is_onboarded = True
    institution.verification_mode = "open"
    db.session.commit()

    allowed = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "waiting-university",
        },
    )
    assert allowed.status_code == 201
    assert Institution.query.filter_by(slug="waiting-university").first().is_onboarded
