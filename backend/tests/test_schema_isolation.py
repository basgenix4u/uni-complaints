"""Sharing a database with another application.

These tables are deployed into a Supabase project that already hosts a
different system. Several names are ones any application is likely to
use: users, notifications, attachments, responses. Landing them in
`public` would collide, and sharing `alembic_version` is worse than a
collision, because a later autogenerate would see the other application's
tables as unexpected and propose dropping them.

A dedicated PostgreSQL schema avoids all of it. These tests pin the
behaviour so it cannot regress quietly.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent

# Names another application in the same database plausibly also uses.
CONTESTED = ("users", "notifications", "attachments", "responses", "alembic_version")


psycopg2 = pytest.importorskip(
    "psycopg2",
    reason="the PostgreSQL driver is needed to render PostgreSQL DDL",
)


def generate_sql(schema: str | None) -> str:
    """Render the migration as SQL without needing a live database."""
    env = {
        **os.environ,
        "FLASK_APP": "run.py",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/shared",
    }
    if schema:
        env["DB_SCHEMA"] = schema
    else:
        env.pop("DB_SCHEMA", None)

    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade", "base:head", "--sql"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    # Without this, a failed command returns an empty string and every
    # assertion below reports a missing schema rather than the real
    # cause.
    if result.returncode != 0 or not result.stdout.strip():
        raise AssertionError(
            f"could not render migration SQL (exit {result.returncode}):\n"
            f"{result.stderr[-1500:]}"
        )

    return result.stdout


@pytest.fixture(scope="module")
def shared_sql():
    return generate_sql("resolve")


@pytest.fixture(scope="module")
def standalone_sql():
    return generate_sql(None)


def test_the_schema_is_created_before_anything_uses_it(shared_sql):
    assert 'CREATE SCHEMA IF NOT EXISTS "resolve"' in shared_sql


def test_every_table_is_namespaced(shared_sql):
    created = shared_sql.count("CREATE TABLE resolve.")

    # Asserted as a floor rather than an exact figure, so adding a table
    # does not fail a test about isolation.
    assert created >= 12


def test_nothing_lands_in_public(shared_sql):
    """An unqualified CREATE TABLE would collide with the other system."""
    import re

    unqualified = re.findall(r"^CREATE TABLE ([a-z_]+) \(", shared_sql, re.M)

    assert unqualified == []


def test_contested_names_are_all_namespaced(shared_sql):
    for name in CONTESTED:
        assert f"CREATE TABLE resolve.{name} " in shared_sql, name


def test_the_version_table_is_namespaced(shared_sql):
    """The most damaging collision of the three.

    A shared alembic_version means our migrations read the other
    application's revision id, and autogenerate would then treat its
    tables as extras to drop.
    """
    assert "CREATE TABLE resolve.alembic_version" in shared_sql
    assert "CREATE TABLE alembic_version" not in shared_sql


def test_foreign_keys_point_inside_the_schema(shared_sql):
    """An unqualified reference resolves against the search path.

    That could silently bind to the other application's users table.
    """
    assert "REFERENCES resolve." in shared_sql
    assert "REFERENCES users " not in shared_sql
    assert "REFERENCES institutions " not in shared_sql


def test_indexes_are_namespaced(shared_sql):
    assert " ON resolve." in shared_sql


def test_a_database_of_our_own_still_uses_public(standalone_sql):
    """Isolation must be opt in, not forced on every deployment."""
    assert "CREATE SCHEMA" not in standalone_sql
    assert "CREATE TABLE institutions (" in standalone_sql
    assert "CREATE TABLE resolve." not in standalone_sql


def test_sqlite_ignores_the_setting(tmp_path):
    """SQLite has no schemas, so development works without PostgreSQL."""
    database = tmp_path / "isolation.db"
    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=BACKEND,
        env={
            **os.environ,
            "FLASK_APP": "run.py",
            "DB_SCHEMA": "resolve",
            "DATABASE_URL": f"sqlite:///{database}",
        },
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr[-600:]

    import sqlite3

    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            )
        ]

    assert len(tables) >= 12
    assert "users" in tables


def test_models_carry_the_schema_when_configured(monkeypatch):
    monkeypatch.setenv("DB_SCHEMA", "resolve")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")

    import app.extensions

    extensions = importlib.reload(app.extensions)
    assert extensions.db.metadata.schema == "resolve"


def test_models_drop_the_schema_on_sqlite(monkeypatch):
    monkeypatch.setenv("DB_SCHEMA", "resolve")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")

    import app.extensions

    extensions = importlib.reload(app.extensions)
    assert extensions.db.metadata.schema is None


def test_constraint_names_are_deterministic(shared_sql):
    """Alembic cannot alter a constraint it cannot name.

    Without a naming convention the database invents names, and they
    differ between environments.
    """
    assert "CONSTRAINT fk_complaints_student_id_users" in shared_sql
    assert "CONSTRAINT pk_complaints" in shared_sql


def test_migrations_do_not_hardcode_a_schema_name():
    """A revision must build wherever it is pointed.

    Autogenerate writes foreign key targets as literals, baking in the
    schema that happened to be configured when the revision was produced.
    Three revisions carried 47 such literals, so an upgrade against a
    database of our own — DB_SCHEMA unset, which is the ordinary case —
    demanded a schema nobody had created and failed at the first table.

    Caught by running the migrations on real PostgreSQL in CI; invisible
    on SQLite, which ignores schemas entirely.
    """
    sql = generate_sql(schema=None)

    assert "resolve." not in sql, (
        "a revision hardcodes the 'resolve' schema, so it only works for one deployment"
    )
    assert "CREATE TABLE institutions" in sql


def test_the_same_revisions_still_honour_a_schema():
    """The other half: qualifying must not have been lost in the fix."""
    sql = generate_sql(schema="resolve")

    assert "CREATE TABLE resolve.institutions" in sql
    assert "REFERENCES resolve.institutions" in sql
