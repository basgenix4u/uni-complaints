"""Flask extension instances.

Kept in their own module so models and blueprints can import them without
creating a circular dependency on the application factory.
"""

import os

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

# Naming conventions make constraint names deterministic, which Alembic
# needs in order to alter or drop them later. Without this, an unnamed
# constraint created on one database cannot reliably be found on another.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# The schema is read at import time from the environment rather than from
# app config, because MetaData is constructed before an application
# exists. Empty means `public`.
_SCHEMA = os.getenv("DB_SCHEMA") or None

# SQLite has no concept of a schema, so the setting is ignored there and
# development keeps working without a PostgreSQL instance.
if _SCHEMA and "sqlite" in os.getenv("DATABASE_URL", "sqlite"):
    _SCHEMA = None

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION, schema=_SCHEMA))
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
