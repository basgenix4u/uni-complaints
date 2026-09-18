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

    The sequence is incremented in the database so concurrent submissions
    cannot receive the same number.
    """
    institution.ticket_sequence = (institution.ticket_sequence or 0) + 1
    db.session.flush()
    sequence = institution.ticket_sequence % 10000
    return f"{institution.code}-{_random_block()}-{sequence:04d}"


def normalise_ticket(value: str) -> str:
    """Accept tickets typed without hyphens or in lower case."""
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())
