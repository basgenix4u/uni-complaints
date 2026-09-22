"""settle on one spelling for an institution's type

The imported register wrote "college_of_education" while the manual form
wrote "college", so a filter for either silently excluded the other. No
error was raised anywhere: the query simply returned fewer institutions
than it should have, which is the kind of fault nobody reports because
it looks like an empty result.

Existing rows are rewritten onto the canonical spelling. The alias is
still accepted on input, so a bookmarked filter keeps working.

Revision ID: 0008_normalise_institution_type
Revises: 0007_directory_fields
"""

import os

from alembic import op

revision = "0008_normalise_institution_type"
down_revision = "0007_directory_fields"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None

# Old spelling -> canonical. Only entries that could already be in a
# database are listed; the rest of the vocabulary never had a variant.
RENAMES = (
    ("college", "college_of_education"),
    ("hospital", "teaching_hospital"),
)


def _table():
    """SQLite has no schemas, so the setting is ignored there."""
    if not _CONFIGURED_SCHEMA:
        return "institutions"
    if op.get_bind().dialect.name != "postgresql":
        return "institutions"
    return f"{_CONFIGURED_SCHEMA}.institutions"


def upgrade():
    table = _table()
    for old, new in RENAMES:
        op.execute(f"UPDATE {table} SET type = '{new}' WHERE type = '{old}'")


def downgrade():
    table = _table()
    for old, new in RENAMES:
        op.execute(f"UPDATE {table} SET type = '{old}' WHERE type = '{new}'")
