from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_caching import Cache
# from firebase_admin import credentials, auth, initialize_app
import json

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per day", "30 per hour"]
)
cache = Cache()
