from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_caching import Cache
from firebase_admin import credentials, auth, initialize_app
import json

db = SQLAlchemy()
migrate = Migrate()
cache = Cache(config={"CACHE_TYPE": "simple"})

limiter = Limiter(
    key_func=lambda: "global",  # Rate limit per user
    default_limits=["200 per day", "50 per hour"]
)

class FirebaseAuth:
    def __init__(self):
        self.cred = None
        self.app = None

    # def init_app(self, app):
        # self.cred = credentials.Certificate(app.config["FIREBASE_CREDENTIALS"])
        # self.app = initialize_app(self.cred)

    def verify_token(self, token):
        return auth.verify_id_token(token)

firebase_auth = FirebaseAuth()
