"""One vocabulary for an institution's type.

The imported register wrote "college_of_education" and the manual admin
form wrote "college". Nothing errored: a filter for either simply
returned fewer institutions than it should have, which looks like an
empty result rather than a fault and so goes unreported.
"""

import pytest

from app.extensions import db
from app.models.institution import (
    INSTITUTION_TYPES,
    Institution,
    canonical_type,
)
from app.services.directory import search
from tests.conftest import auth, login, make_user


@pytest.mark.parametrize(
    "supplied,expected",
    [
        ("college", "college_of_education"),
        ("College", "college_of_education"),
        ("college-of-education", "college_of_education"),
        ("college of education", "college_of_education"),
        ("coe", "college_of_education"),
        ("hospital", "teaching_hospital"),
        ("university", "university"),
        ("poly", "polytechnic"),
    ],
)
def test_older_spellings_map_onto_the_vocabulary(supplied, expected):
    assert canonical_type(supplied) == expected


@pytest.mark.parametrize("supplied", ["", None, "   ", "nonsense", "school"])
def test_an_unrecognised_type_is_rejected_rather_than_guessed(supplied):
    assert canonical_type(supplied) is None


def college(slug="alpha-college", code="AC"):
    institution = Institution(
        name="Alpha College of Education",
        slug=slug,
        code=code,
        short_name=code,
        state="Oyo",
        type="college_of_education",
        ownership="state",
        is_onboarded=True,
        is_active=True,
    )
    db.session.add(institution)
    db.session.commit()
    return institution


def test_the_old_spelling_still_finds_the_new_one(app):
    """A bookmarked filter must not start returning nothing."""
    college()

    assert [i.slug for i in search(kind="college")] == ["alpha-college"]
    assert [i.slug for i in search(kind="college_of_education")] == ["alpha-college"]


def test_an_unrecognised_filter_returns_nothing_rather_than_everything(app):
    """Ignoring it would quietly widen the search instead of narrowing it."""
    college()

    assert search(kind="nonsense") == []


def test_the_admin_form_writes_the_canonical_spelling(client, alpha):
    """The drift started here: this endpoint stored the short form."""
    make_user(alpha, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Beta College of Education",
            "code": "BCE",
            "slug": "beta-college",
            "type": "college",
            "admin_name": "Beta Admin",
            "admin_email": "admin@beta.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    stored = Institution.query.filter_by(slug="beta-college").one()
    assert stored.type == "college_of_education"
    # And it is reachable by the filter the directory actually uses.
    assert stored.slug in [i.slug for i in search(kind="college_of_education")]


def test_a_nonsense_type_is_refused(client, alpha):
    make_user(alpha, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Gamma Institute",
            "code": "GI",
            "slug": "gamma-institute",
            "type": "school",
            "admin_name": "Gamma Admin",
            "admin_email": "admin@gamma.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 422
    assert "type" in response.get_json()["errors"]


def test_the_imported_register_only_uses_the_vocabulary(app):
    """The seed file and the model must agree on the spellings."""
    import json

    from app.services.seed_directory import DATA_FILE

    kinds = {r["kind"] for r in json.loads(DATA_FILE.read_text(encoding="utf-8"))}

    assert kinds <= set(INSTITUTION_TYPES), f"unknown kinds in the register: {kinds}"
