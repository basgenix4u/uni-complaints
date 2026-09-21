"""routing applied at filing, and escalation up the real hierarchy

Three additions, all columns on existing tables.

`complaints.is_confidential` is copied from the routing rule when the
complaint is filed rather than read back from the rule later, so relaxing
a rule cannot retrospectively expose a report that was made in
confidence.

`complaints.escalation_level` and `next_escalation_at` replace notifying
every department head at once with a climb up the chain of command, one
rung at a time.

`institutions.ignored_report_sent_at` stops a scheduler that fires every
quarter of an hour from sending a weekly report that often.

Revision ID: 0004_routing_integration
Revises: 0003_invitations
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0004_routing_integration"
down_revision = "0003_invitations"
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

    with op.batch_alter_table("complaints", schema=SCHEMA) as batch:
        batch.add_column(
            sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("next_escalation_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(
        "ix_complaints_next_escalation_at",
        "complaints",
        ["next_escalation_at"],
        unique=False,
        schema=SCHEMA,
    )

    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.add_column(
            sa.Column("ignored_report_sent_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Complaints filed before this revision were escalated under the old
    # all-at-once scheme. Marking them as having reached the first rung
    # stops the new sweep treating them as fresh and starting the climb
    # again from the bottom.
    complaints = sa.table(
        "complaints",
        sa.column("escalated_at", sa.DateTime(timezone=True)),
        sa.column("escalation_level", sa.Integer),
        schema=SCHEMA,
    )
    op.execute(
        complaints.update()
        .where(complaints.c.escalated_at.isnot(None))
        .values(escalation_level=1)
    )


def downgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.drop_column("ignored_report_sent_at")

    op.drop_index("ix_complaints_next_escalation_at", table_name="complaints", schema=SCHEMA)

    with op.batch_alter_table("complaints", schema=SCHEMA) as batch:
        batch.drop_column("next_escalation_at")
        batch.drop_column("escalation_level")
        batch.drop_column("is_confidential")
