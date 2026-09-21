"""staff invitations and the dean role

An invitation replaces an administrator typing a colleague's password,
which meant one person knew another's credentials and did not scale past
a handful of staff.

Adds the faculty link on users, because a dean's remit is a faculty
rather than a single unit.

Revision ID: 0003_invitations
Revises: 0002_academic
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0003_invitations"
down_revision = "0002_academic"
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

    op.create_table('invitations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=True),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('department_id', sa.String(length=36), nullable=True),
    sa.Column('faculty_id', sa.String(length=36), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('invited_by_id', sa.String(length=36), nullable=True),
    sa.Column('accepted_user_id', sa.String(length=36), nullable=True),
    sa.Column('sent_count', sa.Integer(), nullable=False),
    sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['accepted_user_id'], ['resolve.users.id'], name=op.f('fk_invitations_accepted_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['department_id'], ['resolve.departments.id'], name=op.f('fk_invitations_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['faculty_id'], ['resolve.faculties.id'], name=op.f('fk_invitations_faculty_id_faculties'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_invitations_institution_id_institutions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by_id'], ['resolve.users.id'], name=op.f('fk_invitations_invited_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invitations')),
    schema=SCHEMA
    )
    op.create_index('ix_invitation_email', 'invitations', ['institution_id', 'email'], unique=False, schema=SCHEMA)
    op.create_index('ix_invitation_institution_status', 'invitations', ['institution_id', 'status'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_invitations_created_at'), 'invitations', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_invitations_institution_id'), 'invitations', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_invitations_token_hash'), 'invitations', ['token_hash'], unique=True, schema=SCHEMA)
    # ### end Alembic commands ###

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.add_column(sa.Column("faculty_id", sa.String(length=36), nullable=True))
        batch.create_index("ix_users_faculty_id", ["faculty_id"], unique=False)


def downgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("users", schema=SCHEMA) as batch:
        batch.drop_index("ix_users_faculty_id")
        batch.drop_column("faculty_id")

    op.drop_table("invitations", schema=SCHEMA)
