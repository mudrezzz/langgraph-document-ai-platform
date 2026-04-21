from __future__ import annotations

from apps.api.dependencies import get_container
from apps.worker.celery_app import celery_app
from schemas.api.contracts import StartAuthoringTaskRequest


@celery_app.task(name="apps.worker.tasks.run_authoring_task", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_authoring_task(self, *, task_id: str, request_payload: dict) -> dict:
    """Выполняет authoring flow для уже созданной queued-задачи."""

    _ = self
    container = get_container()
    request = StartAuthoringTaskRequest.model_validate(request_payload)
    result = container.authoring_service.run_existing_task(task_id=task_id, request=request)
    return result.model_dump(mode="json")
