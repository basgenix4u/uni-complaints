"""add configurable priority-based SLA and escalation policy

A single acknowledgement deadline and a fixed escalation interval treat a
routine ID-card request like a safety report. Institutions may now configure
acknowledgement hours, resolution factor and escalation cadence per priority.
The column is nullable so migrating an existing institution preserves its
previous behaviour until somebody deliberately saves a policy.

Revision ID: 0012_priority_sla_policy
Revises: 0011_schema_security
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0012_priority_sla_policy"
down_revision = "0011_schema_security"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    with op.batch_alter_table("institutions", schema=_schema()) as batch:
        batch.add_column(sa.Column("priority_sla_policy", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("institutions", schema=_schema()) as batch:
        batch.drop_column("priority_sla_policy")
