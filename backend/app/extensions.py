"""Flask extension instances.

Kept in their own module so models and blueprints can import them without
creating a circular dependency on the application factory.
"""

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
