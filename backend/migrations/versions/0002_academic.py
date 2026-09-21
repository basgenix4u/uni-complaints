"""academic structure, student register and routing

Adds the academic hierarchy a university actually has, the register used
to verify a student, the routing table that decides which unit answers
which complaint, and a record of demand from institutions not yet using
the service.

The schema is read from DB_SCHEMA rather than hardcoded, so the same
revision works in a database of our own and in one shared with another
application.

Revision ID: 0002_academic
Revises: 0001_initial
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0002_academic"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    """The schema to build in, or None.

    SQLite has no schemas, so the setting is ignored there. Taken from
    the live connection rather than the URL environment variable, which
    may not be what the application connected with.
    """
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    SCHEMA = _schema()

    op.create_table('academic_sessions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=20), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=True),
    sa.Column('ends_on', sa.Date(), nullable=True),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_academic_sessions_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_academic_sessions')),
    sa.UniqueConstraint('institution_id', 'name', name='uq_session_name_per_institution'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_academic_sessions_created_at'), 'academic_sessions', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_academic_sessions_institution_id'), 'academic_sessions', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_session_institution_current', 'academic_sessions', ['institution_id', 'is_current'], unique=False, schema=SCHEMA)
    op.create_table('institution_interest',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_name', sa.String(length=200), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=True),
    sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_institution_interest_institution_id_institutions'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_institution_interest')),
    sa.UniqueConstraint('email', 'institution_name', name='uq_interest_email_institution'),
    schema=SCHEMA
    )
    op.create_index('ix_interest_name', 'institution_interest', ['institution_name'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_institution_interest_created_at'), 'institution_interest', ['created_at'], unique=False, schema=SCHEMA)
    op.create_table('routing_rules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('department_id', sa.String(length=36), nullable=True),
    sa.Column('escalates_to_department_id', sa.String(length=36), nullable=True),
    sa.Column('is_confidential', sa.Boolean(), nullable=False),
    sa.Column('sla_hours', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['resolve.departments.id'], name=op.f('fk_routing_rules_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['escalates_to_department_id'], ['resolve.departments.id'], name=op.f('fk_routing_rules_escalates_to_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_routing_rules_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_routing_rules')),
    sa.UniqueConstraint('institution_id', 'category', name='uq_routing_category'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_routing_rules_created_at'), 'routing_rules', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_routing_rules_institution_id'), 'routing_rules', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_routing_institution', 'routing_rules', ['institution_id', 'is_active'], unique=False, schema=SCHEMA)
    op.create_table('faculties',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('dean_user_id', sa.String(length=36), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['dean_user_id'], ['resolve.users.id'], name=op.f('fk_faculties_dean_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_faculties_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faculties')),
    sa.UniqueConstraint('institution_id', 'slug', name='uq_faculty_slug_per_institution'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_faculties_created_at'), 'faculties', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_faculties_institution_id'), 'faculties', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_table('academic_departments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('faculty_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('head_user_id', sa.String(length=36), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['faculty_id'], ['resolve.faculties.id'], name=op.f('fk_academic_departments_faculty_id_faculties'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['head_user_id'], ['resolve.users.id'], name=op.f('fk_academic_departments_head_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_academic_departments_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_academic_departments')),
    sa.UniqueConstraint('institution_id', 'slug', name='uq_acaddept_slug_per_institution'),
    schema=SCHEMA
    )
    op.create_index('ix_acaddept_faculty', 'academic_departments', ['faculty_id', 'is_active'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_academic_departments_created_at'), 'academic_departments', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_academic_departments_faculty_id'), 'academic_departments', ['faculty_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_academic_departments_institution_id'), 'academic_departments', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_table('student_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('matric_number', sa.String(length=40), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('faculty_id', sa.String(length=36), nullable=True),
    sa.Column('academic_department_id', sa.String(length=36), nullable=True),
    sa.Column('programme', sa.String(length=150), nullable=True),
    sa.Column('level', sa.Integer(), nullable=True),
    sa.Column('admitted_session_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('claimed_by_user_id', sa.String(length=36), nullable=True),
    sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['academic_department_id'], ['resolve.academic_departments.id'], name=op.f('fk_student_records_academic_department_id_academic_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['admitted_session_id'], ['resolve.academic_sessions.id'], name=op.f('fk_student_records_admitted_session_id_academic_sessions'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['claimed_by_user_id'], ['resolve.users.id'], name=op.f('fk_student_records_claimed_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['faculty_id'], ['resolve.faculties.id'], name=op.f('fk_student_records_faculty_id_faculties'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_student_records_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_records')),
    sa.UniqueConstraint('claimed_by_user_id', name=op.f('uq_student_records_claimed_by_user_id')),
    sa.UniqueConstraint('institution_id', 'matric_number', name='uq_student_matric_per_institution'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_student_records_created_at'), 'student_records', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_student_records_institution_id'), 'student_records', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_student_records_matric_number'), 'student_records', ['matric_number'], unique=False, schema=SCHEMA)
    op.create_index('ix_student_record_claimed', 'student_records', ['institution_id', 'claimed_by_user_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_student_record_status', 'student_records', ['institution_id', 'status'], unique=False, schema=SCHEMA)
    # ### end Alembic commands ###

    # Institutions created before this revision predate onboarding, so
    # they are marked as onboarded to avoid locking out their students.
    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.add_column(sa.Column("verification_mode", sa.String(length=20),
                                   nullable=False, server_default="register"))
        batch.add_column(sa.Column("matric_pattern", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("matric_example", sa.String(length=60), nullable=True))
        batch.add_column(sa.Column("is_onboarded", sa.Boolean(),
                                   nullable=False, server_default=sa.true()))


def downgrade():
    SCHEMA = _schema()

    with op.batch_alter_table("institutions", schema=SCHEMA) as batch:
        batch.drop_column("is_onboarded")
        batch.drop_column("matric_example")
        batch.drop_column("matric_pattern")
        batch.drop_column("verification_mode")

    op.drop_table('institution_interest', schema=SCHEMA)
    op.drop_table('routing_rules', schema=SCHEMA)
    op.drop_table('student_records', schema=SCHEMA)
    op.drop_table('academic_departments', schema=SCHEMA)
    op.drop_table('faculties', schema=SCHEMA)
    op.drop_table('academic_sessions', schema=SCHEMA)
