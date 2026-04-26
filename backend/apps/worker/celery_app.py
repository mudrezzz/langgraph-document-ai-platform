from __future__ import annotations

import os

from celery import Celery


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


broker_url = _env("APP_CELERY_BROKER_URL", "redis://127.0.0.1:56379/0")
result_backend = _env("APP_CELERY_RESULT_BACKEND", broker_url)

celery_app = Celery(
    "langgraph-document-ai-worker",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_default_queue=_env("APP_CELERY_QUEUE", "authoring"),
    task_routes={
        "apps.worker.tasks.run_authoring_task": {"queue": _env("APP_CELERY_QUEUE", "authoring")},
        "apps.worker.tasks.run_authoring_hitl_action": {"queue": _env("APP_CELERY_QUEUE", "authoring")},
        "apps.worker.tasks.run_knowledge_indexing_task": {"queue": _env("APP_CELERY_INDEXING_QUEUE", "knowledge-indexing")},
        "apps.worker.tasks.run_retrieval_task": {"queue": _env("APP_CELERY_RETRIEVAL_QUEUE", "retrieval")},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(["apps.worker"])
