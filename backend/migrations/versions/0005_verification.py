"""email verification and registration approval

Nothing previously stopped somebody registering with an address that was
not theirs. That matters more here than on most systems: a complaint
carries a name and a matriculation number, and an account opened on a
stranger's address puts their grievance in the wrong hands.

Existing accounts are marked verified and approved. They were created
before the rule existed, and locking out every current user to enforce a
policy retrospectively would be a worse failure than the one being fixed.

Revision ID: 0005_verification
Revises: 0004_routing_integration
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0005_verification"
down_revision = "0004_routing_integration"
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

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("sent_count", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id" if SCHEMA else "users.id"],
            name=op.f("fk_email_verifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verifications")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_verification_user_used", "email_verifications", ["user_id", "used_at"],
        unique=False, schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_email_verifications_user_id"), "email_verifications", ["user_id"],
        unique=False, schema=SCHEMA,
    )
    op.create_index(
        op.f("ix_email_verifications_token_hash"), "email_verifications", ["token_hash"],
        unique=True, schema=SCHEMA,
    )

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column(
                "approval_status", sa.String(length=20),
                nullable=False, server_default="approved",
            )
        )

    users = sa.table(
        "users",
        sa.column("email_verified_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )
    op.execute(users.update().values(email_verified_at=users.c.created_at))


def downgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.drop_column("approval_status")
        batch.drop_column("email_verified_at")

    op.drop_index(
        op.f("ix_email_verifications_token_hash"), table_name="email_verifications", schema=SCHEMA
    )
    op.drop_index(
        op.f("ix_email_verifications_user_id"), table_name="email_verifications", schema=SCHEMA
    )
    op.drop_index(
        "ix_verification_user_used", table_name="email_verifications", schema=SCHEMA
    )
    op.drop_table("email_verifications", schema=SCHEMA)
