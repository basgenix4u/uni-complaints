"""The institution directory, and demand from institutions not on it.

A student whose university is not using the service currently reaches a
dead end: "we could not find that institution", and nothing happens. That
is a wasted signal. Fifty students asking for the same university is the
argument for approaching that university, and it costs nothing to
collect.

The directory itself is public and unauthenticated, because a person has
to find their institution before they have an account.
"""

import re

from app.extensions import db
from app.models.academic import InstitutionInterest
from app.models.institution import Institution

# Beyond this a search is not narrowing anything, and returning the lot
# on an empty query would ship the whole table to a phone.
MAX_RESULTS = 50

# Ranking happens in Python, so the candidate set is capped first. This
# is deliberately larger than a page: a good match must not be cut off
# by SQL before it can be ranked to the top.
RANK_CEILING = 300


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def search(query: str = "", state: str = "", onboarded_only: bool = False,
           kind: str = "", limit: int = MAX_RESULTS) -> list[Institution]:
    """Find institutions by name, acronym, state or type.

    Institutions that have not been onboarded are included on purpose. A
    student needs to see that their university is known to us but not yet
    signed up, which is a different answer from "never heard of it" and
    leads somewhere.

    Ordering matters more than filtering here. With several hundred
    institutions in the list, a search for "lagos" matches a dozen, and
    the one the student means is almost always the one whose name starts
    with what they typed. Results are ranked rather than returned
    alphabetically, or the University of Lagos appears below a college
    nobody was looking for.
    """
    rows = Institution.query.filter_by(is_active=True)

    term = _normalise(query)
    if term:
        like = f"%{term}%"
        rows = rows.filter(
            db.or_(
                Institution.name.ilike(like),
                Institution.short_name.ilike(like),
                Institution.code.ilike(like),
                Institution.slug.ilike(like),
                # Typed as "uni lagos" or "unilag"; the slug is hyphenated
                # so a space-stripped comparison catches both.
                Institution.slug.ilike(f"%{term.replace(' ', '-')}%"),
            )
        )

    if state:
        rows = rows.filter(Institution.state.ilike(_normalise(state)))

    if kind:
        rows = rows.filter(Institution.type == _normalise(kind).lower())

    if onboarded_only:
        rows = rows.filter(Institution.is_onboarded.is_(True))

    found = rows.limit(RANK_CEILING).all()
    found.sort(key=lambda i: _rank(i, term))
    return found[:limit]


def _rank(institution: Institution, term: str) -> tuple:
    """Sort key: best match first.

    Sorting in Python rather than SQL keeps the same ordering on SQLite
    and PostgreSQL. The candidate set is capped first, so this never runs
    over more rows than a page could show.
    """
    name = (institution.name or "").lower()
    short = (institution.short_name or "").lower()
    term = term.lower()

    if not term:
        tier = 0
    elif short == term:
        # Someone who types UNILAG means exactly one institution.
        tier = 0
    elif name == term:
        tier = 1
    elif short.startswith(term):
        tier = 2
    elif re.search(rf"\b{re.escape(term)}\b", name):
        # A whole-word match anywhere in the name, which is the common
        # case for a place: "ibadan" should reach the University of
        # Ibadan as readily as Ibadan City Polytechnic. Ranking a prefix
        # above this put every institution that merely starts with a town
        # name ahead of the one people were looking for.
        tier = 3
    elif name.startswith(term):
        tier = 4
    else:
        tier = 5

    # A place name matches many institutions. Someone typing "ibadan"
    # almost certainly wants the University of Ibadan rather than a
    # private polytechnic that happens to sort earlier, so within a tier
    # the larger, longer-established sector comes first. This is a
    # heuristic about what people search for, not a judgement of quality.
    sector = {"university": 0, "polytechnic": 1, "college_of_education": 2}
    funding = {"federal": 0, "state": 1, "private": 2}

    return (
        tier,
        # An institution a student can actually use outranks one we merely
        # know of, but only among equally good name matches.
        0 if institution.is_onboarded else 1,
        sector.get(institution.type, 3),
        funding.get(institution.ownership, 3),
        len(name),
        name,
    )


def record_interest(institution_name: str, email: str, full_name: str = "",
                    institution: Institution | None = None) -> tuple[InstitutionInterest, bool]:
    """Note that somebody wants their institution added.

    Returns (row, created). Asking twice is not an error and does not
    inflate the count: the point of the number is how many distinct
    people want it, which is what makes it an argument.
    """
    name = _normalise(institution_name)[:200]
    address = (email or "").strip().lower()[:255]

    existing = InstitutionInterest.query.filter_by(
        email=address, institution_name=name
    ).first()
    if existing:
        return existing, False

    row = InstitutionInterest(
        institution_name=name,
        institution_id=institution.id if institution else None,
        email=address,
        full_name=_normalise(full_name)[:150] or None,
    )
    db.session.add(row)
    db.session.commit()
    return row, True


def demand(limit: int = 100) -> list[dict]:
    """Which institutions are being asked for, most wanted first.

    This is the list that decides who to approach next.
    """
    rows = (
        db.session.query(
            InstitutionInterest.institution_name,
            db.func.count(InstitutionInterest.id).label("requests"),
            db.func.max(InstitutionInterest.created_at).label("latest"),
        )
        .group_by(InstitutionInterest.institution_name)
        .order_by(db.text("requests DESC"))
        .limit(limit)
        .all()
    )

    known = {
        i.name.strip().lower(): i
        for i in Institution.query.all()
    }

    result = []
    for name, requests, latest in rows:
        match = known.get((name or "").strip().lower())
        result.append(
            {
                "institution_name": name,
                "requests": requests,
                "latest_request_at": latest.isoformat() if latest else None,
                # Distinguishes "we have never heard of this place" from
                # "we have it on file but they have not signed up", which
                # are very different sales conversations.
                "known": match is not None,
                "is_onboarded": bool(match and match.is_onboarded),
            }
        )

    return result
