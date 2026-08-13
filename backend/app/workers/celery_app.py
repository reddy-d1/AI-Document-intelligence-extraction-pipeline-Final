import os
import sys
from celery import Celery
from app.core.config import settings

is_testing = os.getenv("TESTING") == "true" or "pytest" in sys.modules or "test" in sys.argv[0] if len(sys.argv) > 0 else False

celery_app = Celery(
    "doc_intelligence_worker",
    broker=settings.REDIS_URL,
    backend=None,
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_publish_retry=False,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=0.2,
    broker_transport_options={"max_retries": 0},
    result_backend_transport_options={"max_retries": 0},
    result_backend_always_retry=False,
)



@celery_app.task(name="ping_task")
def ping_task():
    """Diagnostic Celery task"""
    return {"status": "pong", "message": "Celery worker operational"}
