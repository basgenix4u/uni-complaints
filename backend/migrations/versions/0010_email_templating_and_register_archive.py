"""email templating per institution + register archive + matric format description

Adds:
- institutions.email_sender_name, email_footer, email_reply_to, matric_format_description
- email_templates table (per-institution templating, not hardcoded, variables ticket/deadline/officer)
- register_imports table (archive of student register uploads, Cloudinary free tier)

Revision ID: 0010_email_templating_and_register_archive
Revises: 0009_pilot_provenance
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0010_email_templating_and_register_archive"
down_revision = "0009_pilot_provenance"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    schema = _schema()

    with op.batch_alter_table("institutions", schema=schema) as batch:
        batch.add_column(sa.Column("matric_format_description", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("email_sender_name", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("email_footer", sa.Text(), nullable=True))
        batch.add_column(sa.Column("email_reply_to", sa.String(length=255), nullable=True))

    # email_templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("subject_template", sa.String(length=300), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "event_type", name="uq_email_template_per_institution_event"),
        schema=schema,
    )
    op.create_index("ix_email_templates_institution_event", "email_templates", ["institution_id", "event_type"], schema=schema)

    # register_imports
    op.create_table(
        "register_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=500), nullable=False),
        sa.Column("storage_backend", sa.String(length=20), nullable=False, server_default="local"),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("rows_read", sa.Integer(), nullable=True),
        sa.Column("created_count", sa.Integer(), nullable=True),
        sa.Column("updated_count", sa.Integer(), nullable=True),
        sa.Column("skipped_count", sa.Integer(), nullable=True),
        sa.Column("problems_json", sa.JSON(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["academic_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index("ix_register_import_institution_created", "register_imports", ["institution_id", "created_at"], schema=schema)


def downgrade():
    schema = _schema()
    op.drop_index("ix_register_import_institution_created", table_name="register_imports", schema=schema)
    op.drop_table("register_imports", schema=schema)
    op.drop_index("ix_email_templates_institution_event", table_name="email_templates", schema=schema)
    op.drop_table("email_templates", schema=schema)

    with op.batch_alter_table("institutions", schema=schema) as batch:
        batch.drop_column("email_reply_to")
        batch.drop_column("email_footer")
        batch.drop_column("email_sender_name")
        batch.drop_column("matric_format_description")
