from celery import Celery

from app.config import settings

celery_app = Celery(
    "saas",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(task_track_started=True, timezone="UTC")

# import tasks so the worker registers them
from app.workers import tasks  # noqa: E402,F401
