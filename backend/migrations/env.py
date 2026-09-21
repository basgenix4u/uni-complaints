import logging
import os

import sqlalchemy as sa

# Read once at import: Alembic needs it before any app exists. SQLite has
# no schemas, so the setting is ignored there and development keeps
# working without a PostgreSQL instance.
_CONFIGURED_SCHEMA = os.getenv("DB_SCHEMA") or None
SCHEMA = _CONFIGURED_SCHEMA


def _schema_for(connection):
    if not _CONFIGURED_SCHEMA:
        return None
    return _CONFIGURED_SCHEMA if connection.dialect.name == "postgresql" else None
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    schema = _CONFIGURED_SCHEMA if url.startswith("postgresql") else None
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        include_object=include_object,
        include_schemas=bool(schema),
        version_table_schema=schema,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(obj, name, type_, reflected, compare_to):
    """Ignore anything outside our schema.

    The same database may host another application. Without this,
    autogenerate sees its tables as unexpected and proposes dropping
    them.
    """
    if type_ == "table":
        return (obj.schema or "public") == (SCHEMA or "public")
    return True


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        # SQLite has no schemas, so this applies to PostgreSQL only.
        # Created before anything else so the version table has somewhere
        # to live on a first run.
        schema = _schema_for(connection)
        if schema:
            # Created before anything else so the version table has
            # somewhere to live on a first run.
            connection.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            include_object=include_object,
            include_schemas=bool(schema),
            version_table_schema=schema,
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
