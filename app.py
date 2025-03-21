from app import create_app
from app.celery_worker import celery

app = create_app()

# Bind Celery to Flask app context
with app.app_context():
    celery.conf.update(app.config)

if __name__ == "__main__":
    app.run(debug=True)
