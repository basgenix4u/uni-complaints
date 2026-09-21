"""Ticket number generation.

Format: <CODE>-<4 chars>-<4 digits>, for example NGX-7K2M-4318.

The alphabet omits I, L, O, U, 0 and 1. Ticket numbers are read aloud over
the phone and written by hand, so characters that are easily confused are
excluded.
"""

import secrets

from app.extensions import db

ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"


def _random_block(length: int = 4) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_ticket_number(institution) -> str:
    """Allocate the next ticket number for an institution.

    The increment is an UPDATE ... SET n = n + 1 evaluated by the
    database, not a read in Python followed by a write. Two students
    filing at the same moment previously both read the same value and
    both wrote value + 1, so the sequence advanced once for two
    complaints; the unique constraint then rejected the second, and the
    student saw a server error instead of a receipt.

    RETURNING gives the post-increment value in the same statement on
    PostgreSQL. SQLite has no RETURNING in this path, so the row is read
    back afterwards — safe there because its writes are serialised.
    """
    from app.models.institution import Institution

    updated = (
        db.session.query(Institution)
        .filter(Institution.id == institution.id)
        .update(
            {Institution.ticket_sequence: Institution.ticket_sequence + 1},
            synchronize_session=False,
        )
    )
    if not updated:
        raise RuntimeError(f"institution {institution.id} disappeared while filing")

    # The in-memory object still holds the pre-update value.
    db.session.refresh(institution, ["ticket_sequence"])

    sequence = institution.ticket_sequence % 10000
    return f"{institution.code}-{_random_block()}-{sequence:04d}"


def normalise_ticket(value: str) -> str:
    """Accept tickets typed without hyphens or in lower case."""
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())
