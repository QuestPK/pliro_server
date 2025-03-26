import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")

    # Database (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Firebase Auth
    # FIREBASE_CREDENTIALS = "path/to/firebase_credentials.json"

    # Redis & Celery
    REDIS_URL = "redis://redis:6379/0"
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # API Docs (Swagger)
    RESTX_VALIDATE = True
    SWAGGER_UI_DOC_EXPANSION = "list"
    RATELIMIT_STORAGE_URI = "redis://redis:6379/0"

config = Config()
