from celery import Celery

celery = Celery(
    "mpesa_app",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)