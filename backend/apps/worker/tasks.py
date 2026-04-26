from __future__ import annotations

from apps.api.dependencies import get_container
from apps.worker.celery_app import celery_app
from schemas.api.contracts import (
    StartAuthoringTaskRequest,
    StartKnowledgeIndexingTaskRequest,
    StartRetrievalTaskRequest,
    SubmitHitlReviewRequest,
)


@celery_app.task(name="apps.worker.tasks.run_authoring_task", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_authoring_task(self, *, task_id: str, request_payload: dict) -> dict:
    """Выполняет authoring flow для уже созданной queued-задачи."""

    _ = self
    container = get_container()
    request = StartAuthoringTaskRequest.model_validate(request_payload)
    result = container.authoring_service.run_existing_task(task_id=task_id, request=request)
    return result.model_dump(mode="json")


@celery_app.task(
    name="apps.worker.tasks.run_authoring_hitl_action",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_authoring_hitl_action(self, *, task_id: str, action_payload: dict) -> dict:
    """Продолжает authoring flow после HITL-решения."""

    _ = self
    container = get_container()
    request = SubmitHitlReviewRequest.model_validate(action_payload.get("request", {}))
    result = container.authoring_service.process_hitl_action(
        task_id=task_id,
        request=request,
        action_id=str(action_payload.get("action_id", "")),
    )
    return result.model_dump(mode="json")


@celery_app.task(
    name="apps.worker.tasks.run_knowledge_indexing_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_knowledge_indexing_task(self, *, task_id: str, request_payload: dict) -> dict:
    """Выполняет knowledge indexing flow для уже созданной queued-задачи."""

    _ = self
    container = get_container()
    request = StartKnowledgeIndexingTaskRequest.model_validate(request_payload)
    result = container.knowledge_indexing_service.run_existing_task(task_id=task_id, request=request)
    return result.model_dump(mode="json")


@celery_app.task(
    name="apps.worker.tasks.run_retrieval_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_retrieval_task(self, *, task_id: str, request_payload: dict) -> dict:
    """Выполняет retrieval flow для уже созданной queued-задачи."""

    _ = self
    container = get_container()
    request = StartRetrievalTaskRequest.model_validate(request_payload)
    result = container.retrieval_service.run_existing_task(task_id=task_id, request=request)
    return result.model_dump(mode="json")
