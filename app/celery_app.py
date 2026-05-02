from celery import Celery
from config import Config


def make_celery(app_name=__name__):
    celery = Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL or "redis://localhost:6379/0",
        backend=Config.CELERY_RESULT_BACKEND or "redis://localhost:6379/0",
    )
    return celery


celery = make_celery()

import app.tasks
