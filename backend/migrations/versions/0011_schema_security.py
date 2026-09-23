"""Keep the isolated schema's defence in depth after every migration.

Alembic creates tables, but PostgreSQL does not inherit row-level security
from neighbouring tables. The email template and register archive tables
therefore need the same protection as the original twenty tables. This
revision makes that property part of the deploy rather than a manual
follow-up step.

The operation is intentionally limited to a configured application schema.
A deployment with DB_SCHEMA unset owns its public schema and may have
legitimate API grants there; changing those grants would be surprising.

Revision ID: 0011_schema_security
Revises: 0010_email_register_archive
"""

import os

from alembic import op

revision = "0011_schema_security"
down_revision = "0010_email_register_archive"
branch_labels = None
depends_on = None

_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None


def _schema():
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if op.get_bind().dialect.name == "postgresql" else None


def _literal(value: str) -> str:
    """Quote a PostgreSQL identifier used in a statement we generate."""
    return '"' + value.replace('"', '""') + '"'


def _string_literal(value: str) -> str:
    """Quote a PostgreSQL string literal used inside the DO block."""
    return "'" + value.replace("'", "''") + "'"


def upgrade():
    schema = _schema()
    if not schema:
        return

    schema_sql = _literal(schema)
    schema_literal = _string_literal(schema)

    # Apply RLS to every table in this application's schema, including
    # tables a later revision may add before it is itself hardened.
    # The application connects as the schema owner, so this does not alter
    # normal API behaviour; it protects against an accidental PostgREST
    # exposure or a future grant to an API role.
    op.execute(
        f"""
        DO $$
        DECLARE table_row record;
        BEGIN
          FOR table_row IN
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = {schema_literal}
              AND c.relkind = 'r'
              AND NOT c.relrowsecurity
          LOOP
            EXECUTE 'ALTER TABLE '
              || quote_ident({schema_literal})
              || '.'
              || quote_ident(table_row.relname)
              || ' ENABLE ROW LEVEL SECURITY';
          END LOOP;
        END $$;
        """
    )

    # No PostgREST role should read this private schema. Repeat the revoke
    # for all current tables and sequences so the rule also covers tables
    # introduced by future revisions.
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema_sql} FROM anon, authenticated")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema_sql} FROM anon, authenticated")
    op.execute(f"REVOKE ALL ON SCHEMA {schema_sql} FROM anon, authenticated")


def downgrade():
    # Security hardening is deliberately not undone by a downgrade. The
    # tables being downgraded will be removed by 0010 and earlier revisions;
    # turning RLS off would create a needless exposure window.
    pass
