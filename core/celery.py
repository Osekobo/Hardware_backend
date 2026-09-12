import os
from celery import Celery

celery = Celery(
    "mpesa_app",
    broker=os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
)