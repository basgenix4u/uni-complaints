"""hold the acronym and ownership an institution is actually known by

The directory is about to carry several hundred institutions rather than
the handful that signed up, and a student searching it types "UNILAG",
not "University of Lagos". The existing `code` column cannot serve that
purpose: it prefixes every ticket number, so it has to stay unique, and
acronyms are not. Ownership is stored because two institutions in
different states often share a name and it is what tells them apart.

Revision ID: 0007_directory_fields
Revises: 0006_manual_confirmation
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0007_directory_fields"
down_revision = "0006_manual_confirmation"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    """SQLite has no schemas, so the setting is ignored there."""
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.add_column(sa.Column("short_name", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("ownership", sa.String(length=20), nullable=True))

    op.create_index(
        "ix_institutions_short_name",
        "institutions",
        ["short_name"],
        schema=SCHEMA,
    )


def downgrade():
    SCHEMA = _schema()

    op.drop_index("ix_institutions_short_name", table_name="institutions", schema=SCHEMA)

    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.drop_column("ownership")
        batch.drop_column("short_name")
