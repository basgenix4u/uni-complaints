"""The national institution list.

A student cannot sign up until their institution exists to be chosen, so
the directory ships pre-populated. These tests cover the two things that
would quietly ruin it: a reload that overwrites an institution's own
corrections, and a search that cannot find a university by the name
everybody actually uses.
"""

import json

import pytest

from app.extensions import db
from app.models.institution import Institution
from app.services.directory import search
from app.services.seed_directory import DATA_FILE, load
from tests.conftest import make_institution


@pytest.fixture
def directory(app):
    load()
    return Institution.query.count()


def test_the_source_list_is_well_formed():
    """A malformed row would be discovered as a failed deploy otherwise."""
    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    assert len(records) > 400

    slugs = [r["slug"] for r in records]
    assert len(slugs) == len(set(slugs)), "slugs are the public key and must be unique"

    for record in records:
        assert record["name"].strip()
        assert record["state"], f"{record['name']} has no state"
        assert record["kind"] in {"university", "polytechnic", "college_of_education"}
        assert record["ownership"] in {"federal", "state", "private"}


def test_loading_fills_the_directory(app):
    summary = load()

    assert summary["created"] > 400
    assert Institution.query.count() == summary["total_in_file"]
    # Known to us, not yet signed up.
    assert Institution.query.filter_by(is_onboarded=True).count() == 0


def test_every_institution_gets_a_unique_ticket_prefix(app, directory):
    """`code` prefixes every ticket number, so a collision is a data leak
    between institutions' ticket sequences."""
    codes = [c for (c,) in db.session.query(Institution.code).all()]

    assert len(codes) == len(set(codes))
    assert all(c and 2 <= len(c) <= 8 for c in codes)


def test_loading_again_changes_nothing(app, directory):
    """The list will be refreshed as new institutions are accredited."""
    summary = load()

    assert summary["created"] == 0
    assert Institution.query.count() == directory


def test_a_reload_does_not_overwrite_an_onboarded_institution(app):
    """Their own administrators may have corrected what we imported."""
    load()
    unilag = Institution.query.filter_by(slug="university-of-lagos").one()
    unilag.is_onboarded = True
    unilag.name = "University of Lagos, Akoka"
    db.session.commit()

    summary = load()

    assert summary["skipped_onboarded"] >= 1
    assert Institution.query.filter_by(slug="university-of-lagos").one().name == (
        "University of Lagos, Akoka"
    )


@pytest.mark.parametrize(
    "term,expected",
    [
        ("unilag", "University of Lagos"),
        ("UNILAG", "University of Lagos"),
        ("futa", "Federal University of Technology Akure"),
        ("yabatech", "Yaba College of Technology"),
        ("oau", "Obafemi Awolowo University"),
        ("unn", "University of Nigeria, Nsukka"),
    ],
)
def test_an_acronym_finds_the_institution_it_belongs_to(app, directory, term, expected):
    """Nobody types "University of Lagos" when UNILAG will do."""
    results = search(query=term)

    assert results, f"no match for {term}"
    assert results[0].name == expected


@pytest.mark.parametrize(
    "town,expected",
    [
        ("ibadan", "University of Ibadan"),
        ("lagos", "University of Lagos"),
        ("abuja", "University of Abuja"),
        ("jos", "University of Jos"),
    ],
)
def test_a_town_finds_the_institution_people_mean(app, directory, town, expected):
    """A place name matches many institutions.

    Ranking a name that merely starts with the town above one that
    contains it put Ibadan City Polytechnic ahead of the University of
    Ibadan, which is not what anyone typing "ibadan" is looking for.
    """
    assert search(query=town)[0].name == expected


def test_an_onboarded_institution_outranks_one_that_is_not(app, directory):
    poly = Institution.query.filter_by(slug="the-polytechnic-ibadan").one()
    poly.is_onboarded = True
    db.session.commit()

    assert search(query="polytechnic ibadan")[0].slug == "the-polytechnic-ibadan"


def test_results_can_be_narrowed_by_state_and_type(app, directory):
    universities = search(state="Kano", kind="university")

    assert universities
    assert all(i.state == "Kano" and i.type == "university" for i in universities)


def test_a_search_never_returns_the_whole_table(app, directory):
    """Several hundred rows would be shipped to a phone on a slow link."""
    assert len(search()) <= 50


def test_an_institution_added_by_hand_is_still_found(app):
    """The directory is not only the imported list."""
    make_institution(code="ZZZ", slug="zeta-university", name="Zeta University")

    assert [i.slug for i in search(query="Zeta")] == ["zeta-university"]
