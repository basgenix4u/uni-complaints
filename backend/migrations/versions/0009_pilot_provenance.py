"""preserve the provenance of controlled pilot data

The FUW evaluation has a controlled phase followed by an operational
phase. Both use the same workflow, but they are not the same evidence.
The marker lives in the database rather than the UI so it cannot be lost
in an export, can be wiped in one operation, and does not distract the
people using the product.

Revision ID: 0009_pilot_provenance
Revises: 0008_normalise_institution_type
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0009_pilot_provenance"
down_revision = "0008_normalise_institution_type"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    schema = _schema()

    with op.batch_alter_table("users", schema=schema) as batch:
        batch.add_column(
            sa.Column(
                "data_origin",
                sa.String(length=30),
                nullable=False,
                server_default="operational",
            )
        )
        batch.add_column(sa.Column("pilot_cohort_id", sa.String(length=40)))
        batch.add_column(sa.Column("pilot_scenario_id", sa.String(length=40)))

    op.create_index("ix_users_data_origin", "users", ["data_origin"], schema=schema)
    op.create_index("ix_users_pilot_cohort_id", "users", ["pilot_cohort_id"], schema=schema)
    op.create_index("ix_users_pilot_scenario_id", "users", ["pilot_scenario_id"], schema=schema)

    with op.batch_alter_table("complaints", schema=schema) as batch:
        batch.add_column(
            sa.Column(
                "data_origin",
                sa.String(length=30),
                nullable=False,
                server_default="operational",
            )
        )
        batch.add_column(sa.Column("pilot_scenario_id", sa.String(length=40)))

    op.create_index("ix_complaints_data_origin", "complaints", ["data_origin"], schema=schema)
    op.create_index(
        "ix_complaints_pilot_scenario_id",
        "complaints",
        ["pilot_scenario_id"],
        schema=schema,
    )


def downgrade():
    schema = _schema()

    op.drop_index("ix_complaints_pilot_scenario_id", table_name="complaints", schema=schema)
    op.drop_index("ix_complaints_data_origin", table_name="complaints", schema=schema)
    with op.batch_alter_table("complaints", schema=schema) as batch:
        batch.drop_column("pilot_scenario_id")
        batch.drop_column("data_origin")

    op.drop_index("ix_users_pilot_scenario_id", table_name="users", schema=schema)
    op.drop_index("ix_users_pilot_cohort_id", table_name="users", schema=schema)
    op.drop_index("ix_users_data_origin", table_name="users", schema=schema)
    with op.batch_alter_table("users", schema=schema) as batch:
        batch.drop_column("pilot_scenario_id")
        batch.drop_column("pilot_cohort_id")
        batch.drop_column("data_origin")
