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


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def search(query: str = "", state: str = "", onboarded_only: bool = False) -> list[Institution]:
    """Find institutions by name, code or state.

    Institutions that have not been onboarded are included on purpose. A
    student needs to see that their university is known to us but not yet
    signed up, which is a different answer from "never heard of it" and
    leads somewhere.
    """
    rows = Institution.query.filter_by(is_active=True)

    term = _normalise(query)
    if term:
        like = f"%{term}%"
        rows = rows.filter(
            db.or_(
                Institution.name.ilike(like),
                Institution.code.ilike(like),
                Institution.slug.ilike(like),
            )
        )

    if state:
        rows = rows.filter(Institution.state.ilike(_normalise(state)))

    if onboarded_only:
        rows = rows.filter(Institution.is_onboarded.is_(True))

    # Onboarded first: those are the ones a student can actually use.
    return (
        rows.order_by(Institution.is_onboarded.desc(), Institution.name)
        .limit(MAX_RESULTS)
        .all()
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
