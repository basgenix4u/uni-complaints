"""configure acknowledgement, resolution and escalation by priority

A single institution-wide acknowledgement window and fixed 24-hour
escalation step treated a safety report like a routine certificate query.
The policy belongs to the institution and is stored per priority.

Revision ID: 0009_priority_sla_policies
Revises: 0008_normalise_institution_type
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0009_priority_sla_policies"
down_revision = "0008_normalise_institution_type"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def _fk(table: str) -> str:
    schema = _schema()
    return f"{schema}.{table}" if schema else table


def upgrade():
    schema = _schema()
    op.create_table(
        "priority_sla_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("acknowledge_hours", sa.Integer(), nullable=False),
        sa.Column("resolve_hours", sa.Integer(), nullable=False),
        sa.Column("escalation_step_hours", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"], [_fk("institutions.id")],
            name="fk_priority_sla_policies_institution_id_institutions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_priority_sla_policies"),
        sa.UniqueConstraint(
            "institution_id", "priority", name="uq_sla_priority_per_institution"
        ),
        schema=schema,
    )
    op.create_index(
        "ix_priority_sla_policies_institution_id",
        "priority_sla_policies",
        ["institution_id"],
        unique=False,
        schema=schema,
    )


def downgrade():
    schema = _schema()
    op.drop_index(
        "ix_priority_sla_policies_institution_id",
        table_name="priority_sla_policies",
        schema=schema,
    )
    op.drop_table("priority_sla_policies", schema=schema)
