from celery import Celery
from app.config import Config

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND
    )
    celery.conf.update(app.config)
    return celery

