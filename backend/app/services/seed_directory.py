"""Load the national institution list into the directory.

A student cannot sign up until their institution exists to be chosen, and
asking each of several hundred institutions to register before any of
their students can complain is the wrong way round. The directory is
therefore pre-populated with every accredited institution we could
source, each marked as not onboarded: known to us, not yet using the
service.

The list is a snapshot, not a live feed. Nigeria approved thirty-three
new universities in a single year, so this will go out of date, and the
loader is written to be run again whenever the file is refreshed.
"""

import json
import re
from pathlib import Path

import structlog

from app.extensions import db
from app.models.institution import Institution

log = structlog.get_logger()

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "institutions.json"

# `code` prefixes every ticket number, so unlike the acronym it has to be
# unique across the whole table.
CODE_MAX = 8


def _load() -> list[dict]:
    with DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _candidate_codes(record: dict):
    """Codes to try, best first.

    The acronym is what an institution would choose for itself, so it is
    tried before anything derived. Everything after that exists only to
    resolve a collision.
    """
    short = (record.get("short_name") or "").upper()
    if short:
        yield short[:CODE_MAX]

    words = [w for w in re.findall(r"[A-Za-z]+", record["name"]) if len(w) > 2]
    initials = "".join(w[0] for w in words).upper()
    if initials:
        yield initials[:CODE_MAX]

    state = re.sub(r"[^A-Za-z]", "", record.get("state") or "").upper()
    if short and state:
        yield f"{short[:4]}{state[:3]}"[:CODE_MAX]

    stem = (short or initials or "INST")[:4]
    for n in range(2, 500):
        yield f"{stem}{n}"[:CODE_MAX]


def _assign_code(record: dict, taken: set[str]) -> str:
    for candidate in _candidate_codes(record):
        if len(candidate) >= 2 and candidate not in taken:
            taken.add(candidate)
            return candidate
    raise RuntimeError(f"could not assign a unique code to {record['name']!r}")


def load(commit: bool = True) -> dict:
    """Insert or update directory entries. Safe to run repeatedly.

    An institution already using the service is never overwritten. Its
    administrators may well have corrected the name or the state, and a
    refresh of a third-party list is not grounds to undo that.
    """
    records = _load()
    taken = {
        code
        for (code,) in db.session.query(Institution.code).all()
        if code
    }
    existing = {
        institution.slug: institution
        for institution in Institution.query.all()
    }

    created = updated = skipped = 0

    for record in records:
        institution = existing.get(record["slug"])

        if institution is None:
            institution = Institution(
                name=record["name"],
                slug=record["slug"],
                code=_assign_code(record, taken),
                short_name=record.get("short_name"),
                state=record.get("state"),
                type=record.get("kind") or "university",
                ownership=record.get("ownership"),
                # Known to us, not yet signed up. A student who finds
                # their institution here is told so, rather than being
                # told we have never heard of it.
                is_onboarded=False,
                is_active=True,
            )
            db.session.add(institution)
            created += 1
            continue

        if institution.is_onboarded:
            skipped += 1
            continue

        changed = False
        for field, value in (
            ("name", record["name"]),
            ("short_name", record.get("short_name")),
            ("state", record.get("state")),
            ("type", record.get("kind") or "university"),
            ("ownership", record.get("ownership")),
        ):
            if value and getattr(institution, field) != value:
                setattr(institution, field, value)
                changed = True
        if changed:
            updated += 1

    if commit:
        db.session.commit()

    summary = {
        "created": created,
        "updated": updated,
        "skipped_onboarded": skipped,
        "total_in_file": len(records),
    }
    log.info("directory_seeded", **summary)
    return summary
