"""make acknowledgement and escalation windows depend on priority

Resolution deadlines already changed with priority, but acknowledgement
was one institution-wide number and every escalation rung got the same
fixed day. The resulting policy was dynamic in name only. This table
keeps all four decisions together and makes them tenant-configurable.

Revision ID: 0009_priority_policies
Revises: 0008_normalise_institution_type
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0009_priority_policies"
down_revision = "0008_normalise_institution_type"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def _fk(table_column: str) -> str:
    schema = _schema()
    return f"{schema}.{table_column}" if schema else table_column


def upgrade():
    schema = _schema()
    op.create_table(
        "priority_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("acknowledge_hours", sa.Integer(), nullable=False),
        sa.Column("resolution_factor", sa.Float(), nullable=False),
        sa.Column("escalation_step_hours", sa.Integer(), nullable=False),
        sa.Column("reminder_hours_before_due", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"], [_fk("institutions.id")],
            name="fk_priority_policies_institution_id_institutions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_priority_policies"),
        sa.UniqueConstraint(
            "institution_id", "priority",
            name="uq_priority_policy_institution_priority",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_priority_policy_institution",
        "priority_policies",
        ["institution_id"],
        unique=False,
        schema=schema,
    )


def downgrade():
    op.drop_table("priority_policies", schema=_schema())
