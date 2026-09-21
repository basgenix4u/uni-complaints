"""initial schema

Creates every table for this application.

The schema is read from DB_SCHEMA rather than hardcoded, so the same
revision serves a database of our own, where the tables sit in public,
and a database shared with another application, where they sit in a
namespace of their own and cannot collide on common names such as users
or notifications.

Revision ID: 0001_initial
Create Date: 2026-09-21
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    """The schema to build in, or None.

    SQLite has no schemas, so the setting is ignored there. The dialect is
    read from the live connection rather than from the URL environment
    variable, which may not be what the application actually connected
    with.
    """
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def upgrade():
    # The schema must exist before any table is created in it. Done here
    # as well as in env.py so a script generated with --sql is complete
    # and can be handed to a DBA to run by hand.
    SCHEMA = _schema()
    if SCHEMA:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table('institutions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('code', sa.String(length=8), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('state', sa.String(length=60), nullable=True),
    sa.Column('logo_url', sa.String(length=500), nullable=True),
    sa.Column('brand_hue', sa.Integer(), nullable=False),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('contact_phone', sa.String(length=30), nullable=True),
    sa.Column('default_sla_hours', sa.Integer(), nullable=False),
    sa.Column('acknowledge_sla_hours', sa.Integer(), nullable=False),
    sa.Column('working_hours_start', sa.Integer(), nullable=False),
    sa.Column('working_hours_end', sa.Integer(), nullable=False),
    sa.Column('allow_anonymous', sa.Boolean(), nullable=False),
    sa.Column('retention_months', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('ticket_sequence', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_institutions')),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_institutions_code'), 'institutions', ['code'], unique=True, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_institutions_created_at'), 'institutions', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_institutions_slug'), 'institutions', ['slug'], unique=True, schema=SCHEMA)
    op.create_table('departments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=400), nullable=True),
    sa.Column('sla_hours', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_departments_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
    sa.UniqueConstraint('institution_id', 'slug', name='uq_department_slug_per_institution'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_departments_created_at'), 'departments', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_departments_institution_id'), 'departments', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=True),
    sa.Column('department_id', sa.String(length=36), nullable=True),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('matric_number', sa.String(length=40), nullable=True),
    sa.Column('faculty', sa.String(length=100), nullable=True),
    sa.Column('department_name', sa.String(length=120), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('erased_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['resolve.departments.id'], name=op.f('fk_users_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_users_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('institution_id', 'email', name='uq_user_email_per_institution'),
    sa.UniqueConstraint('institution_id', 'matric_number', name='uq_user_matric_per_institution'),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_users_created_at'), 'users', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_users_department_id'), 'users', ['department_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_users_email'), 'users', ['email'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_users_institution_id'), 'users', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_users_matric_number'), 'users', ['matric_number'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_users_role'), 'users', ['role'], unique=False, schema=SCHEMA)
    op.create_index('ix_user_institution_role', 'users', ['institution_id', 'role'], unique=False, schema=SCHEMA)
    op.create_table('complaints',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('ticket_number', sa.String(length=20), nullable=False),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('assigned_to_id', sa.String(length=36), nullable=True),
    sa.Column('department_id', sa.String(length=36), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('is_anonymous', sa.Boolean(), nullable=False),
    sa.Column('acknowledge_due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolve_due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolution_note', sa.Text(), nullable=True),
    sa.Column('decline_reason', sa.Text(), nullable=True),
    sa.Column('satisfaction_rating', sa.Integer(), nullable=True),
    sa.Column('satisfaction_comment', sa.String(length=500), nullable=True),
    sa.Column('response_count', sa.Integer(), nullable=False),
    sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assigned_to_id'], ['resolve.users.id'], name=op.f('fk_complaints_assigned_to_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['department_id'], ['resolve.departments.id'], name=op.f('fk_complaints_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_complaints_institution_id_institutions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['resolve.users.id'], name=op.f('fk_complaints_student_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaints')),
    sa.UniqueConstraint('institution_id', 'ticket_number', name='uq_ticket_per_institution'),
    schema=SCHEMA
    )
    op.create_index('ix_complaint_assignee', 'complaints', ['institution_id', 'assigned_to_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_complaint_institution_created', 'complaints', ['institution_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index('ix_complaint_institution_status', 'complaints', ['institution_id', 'status'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_assigned_to_id'), 'complaints', ['assigned_to_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_category'), 'complaints', ['category'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_created_at'), 'complaints', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_department_id'), 'complaints', ['department_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_escalated_at'), 'complaints', ['escalated_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_institution_id'), 'complaints', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_priority'), 'complaints', ['priority'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_resolve_due_at'), 'complaints', ['resolve_due_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_status'), 'complaints', ['status'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_student_id'), 'complaints', ['student_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaints_ticket_number'), 'complaints', ['ticket_number'], unique=False, schema=SCHEMA)
    op.create_table('password_resets',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('requested_ip', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['resolve.users.id'], name=op.f('fk_password_resets_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_password_resets')),
    schema=SCHEMA
    )
    op.create_index('ix_reset_user_used', 'password_resets', ['user_id', 'used_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_password_resets_token_hash'), 'password_resets', ['token_hash'], unique=True, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_password_resets_user_id'), 'password_resets', ['user_id'], unique=False, schema=SCHEMA)
    op.create_table('access_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('complaint_id', sa.String(length=36), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=True),
    sa.Column('actor_role', sa.String(length=30), nullable=True),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['resolve.users.id'], name=op.f('fk_access_logs_actor_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_access_logs_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_access_logs_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_access_logs')),
    schema=SCHEMA
    )
    op.create_index('ix_access_actor_time', 'access_logs', ['actor_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index('ix_access_complaint_time', 'access_logs', ['complaint_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_access_logs_actor_id'), 'access_logs', ['actor_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_access_logs_complaint_id'), 'access_logs', ['complaint_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_access_logs_created_at'), 'access_logs', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_access_logs_institution_id'), 'access_logs', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_table('complaint_events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('complaint_id', sa.String(length=36), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('from_value', sa.String(length=120), nullable=True),
    sa.Column('to_value', sa.String(length=120), nullable=True),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['resolve.users.id'], name=op.f('fk_complaint_events_actor_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_complaint_events_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_complaint_events_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_complaint_events')),
    schema=SCHEMA
    )
    op.create_index('ix_event_complaint_created', 'complaint_events', ['complaint_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaint_events_complaint_id'), 'complaint_events', ['complaint_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaint_events_created_at'), 'complaint_events', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_complaint_events_institution_id'), 'complaint_events', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_table('notifications',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('complaint_id', sa.String(length=36), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_notifications_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_notifications_institution_id_institutions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['resolve.users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    schema=SCHEMA
    )
    op.create_index('ix_notification_user_read', 'notifications', ['user_id', 'is_read'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_notifications_created_at'), 'notifications', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_notifications_institution_id'), 'notifications', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_notifications_user_id'), 'notifications', ['user_id'], unique=False, schema=SCHEMA)
    op.create_table('outbound_messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('complaint_id', sa.String(length=36), nullable=True),
    sa.Column('channel', sa.String(length=10), nullable=False),
    sa.Column('recipient', sa.String(length=255), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_outbound_messages_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_outbound_messages_institution_id_institutions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['resolve.users.id'], name=op.f('fk_outbound_messages_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbound_messages')),
    schema=SCHEMA
    )
    op.create_index('ix_outbound_status_created', 'outbound_messages', ['status', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_outbound_messages_created_at'), 'outbound_messages', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_outbound_messages_institution_id'), 'outbound_messages', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_outbound_messages_status'), 'outbound_messages', ['status'], unique=False, schema=SCHEMA)
    op.create_table('responses',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('complaint_id', sa.String(length=36), nullable=False),
    sa.Column('author_id', sa.String(length=36), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_internal', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['resolve.users.id'], name=op.f('fk_responses_author_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_responses_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_responses_institution_id_institutions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_responses')),
    schema=SCHEMA
    )
    op.create_index(op.f('ix_resolve_responses_author_id'), 'responses', ['author_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_responses_complaint_id'), 'responses', ['complaint_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_responses_created_at'), 'responses', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_responses_institution_id'), 'responses', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_response_complaint_created', 'responses', ['complaint_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_table('attachments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('institution_id', sa.String(length=36), nullable=False),
    sa.Column('complaint_id', sa.String(length=36), nullable=False),
    sa.Column('response_id', sa.String(length=36), nullable=True),
    sa.Column('uploaded_by_id', sa.String(length=36), nullable=True),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=120), nullable=False),
    sa.Column('mime_type', sa.String(length=120), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('is_internal', sa.Boolean(), nullable=False),
    sa.Column('thumbnail_name', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['complaint_id'], ['resolve.complaints.id'], name=op.f('fk_attachments_complaint_id_complaints'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['institution_id'], ['resolve.institutions.id'], name=op.f('fk_attachments_institution_id_institutions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['response_id'], ['resolve.responses.id'], name=op.f('fk_attachments_response_id_responses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['resolve.users.id'], name=op.f('fk_attachments_uploaded_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attachments')),
    sa.UniqueConstraint('stored_name', name=op.f('uq_attachments_stored_name')),
    schema=SCHEMA
    )
    op.create_index('ix_attachment_complaint', 'attachments', ['complaint_id', 'created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_attachments_complaint_id'), 'attachments', ['complaint_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_attachments_created_at'), 'attachments', ['created_at'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_resolve_attachments_institution_id'), 'attachments', ['institution_id'], unique=False, schema=SCHEMA)
    # ### end Alembic commands ###


def downgrade():
    SCHEMA = _schema()

    # Reverse dependency order so foreign keys do not block the drops.
    op.drop_table('access_logs', schema=SCHEMA)
    op.drop_table('attachments', schema=SCHEMA)
    op.drop_table('complaint_events', schema=SCHEMA)
    op.drop_table('complaints', schema=SCHEMA)
    op.drop_table('departments', schema=SCHEMA)
    op.drop_table('institutions', schema=SCHEMA)
    op.drop_table('notifications', schema=SCHEMA)
    op.drop_table('outbound_messages', schema=SCHEMA)
    op.drop_table('password_resets', schema=SCHEMA)
    op.drop_table('responses', schema=SCHEMA)
    op.drop_table('users', schema=SCHEMA)
