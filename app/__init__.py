from flask import Flask
from flask_restx import Api
from app.extensions import db, migrate, limiter, firebase_auth, cache
from app.celery_worker import make_celery
from app.config import config


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    # firebase_auth.init_app(app)
    cache.init_app(app)

    # Initialize Celery
    celery = make_celery(app)

    @celery.task()
    def process_data(data):
        return {"message": "Processed", "data": data}

    # Setup API
    api = Api(app, title="Pliro API", version="1.0", description="API docs")

    # Import and register API namespaces
    from app.routes.product_routes import api as product_ns
    from app.routes.user_routes import api as user_ns

    api.add_namespace(product_ns, path="/products")
    api.add_namespace(user_ns, path="/users")

    return app
