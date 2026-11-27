from celery import Celery
from .config import REDIS_URL

celery_app = Celery("agentx_archive", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks"])
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
