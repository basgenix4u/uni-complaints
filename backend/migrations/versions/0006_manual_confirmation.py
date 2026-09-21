"""record who confirmed an address by hand

Verification depends entirely on email, which makes it a door with no key
on any deployment where email is not yet working. An administrator can now
confirm an address directly, and this records that they did: it is an
assertion somebody checked by other means, not proof the address works,
and the difference matters if it is ever disputed.

Revision ID: 0006_manual_confirmation
Revises: 0005_verification
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0006_manual_confirmation"
down_revision = "0005_verification"
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

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.add_column(sa.Column("email_verified_by_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_users_email_verified_by_id_users",
            "users",
            ["email_verified_by_id"],
            ["id"],
            ondelete="SET NULL",
            referent_schema=SCHEMA,
        )


def downgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.drop_constraint("fk_users_email_verified_by_id_users", type_="foreignkey")
        batch.drop_column("email_verified_by_id")
