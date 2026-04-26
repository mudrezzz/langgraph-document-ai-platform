from __future__ import annotations

from apps.api.dependencies import get_container
from infra.logging import configure_runtime_logging, log_runtime_event
from apps.worker.celery_app import celery_app
from schemas.api.contracts import (
    StartAuthoringTaskRequest,
    StartKnowledgeIndexingTaskRequest,
    StartRetrievalTaskRequest,
    SubmitHitlReviewRequest,
)


_worker_logger = configure_runtime_logging(service="worker", component="celery")


@celery_app.task(name="apps.worker.tasks.run_authoring_task", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_authoring_task(self, *, task_id: str, request_payload: dict) -> dict:
    """Выполняет authoring flow для уже созданной queued-задачи."""

    _ = self
    container = get_container()
    task = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.authoring_task_started",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=task.task_type,
        correlation_id=task.details.get("correlation_id"),
        dispatch_id=task.details.get("dispatch_id"),
        queue_name=task.details.get("queue_name"),
    )
    request = StartAuthoringTaskRequest.model_validate(request_payload)
    try:
        result = container.authoring_service.run_existing_task(task_id=task_id, request=request)
    except Exception as exc:
        failed = container.task_service.get_task(task_id)
        log_runtime_event(
            "worker.authoring_task_failed",
            service="worker",
            component="celery",
            level="ERROR",
            logger=_worker_logger,
            task_id=task_id,
            task_type=failed.task_type,
            correlation_id=failed.details.get("correlation_id"),
            dispatch_id=failed.details.get("dispatch_id"),
            queue_name=failed.details.get("queue_name"),
            error=str(exc),
        )
        raise
    completed = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.authoring_task_completed",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=completed.task_type,
        correlation_id=completed.details.get("correlation_id"),
        dispatch_id=completed.details.get("dispatch_id"),
        queue_name=completed.details.get("queue_name"),
        status=result.status,
    )
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
    task = container.task_service.get_task(task_id)
    action_id = str(action_payload.get("action_id", ""))
    log_runtime_event(
        "worker.authoring_hitl_action_started",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=task.task_type,
        correlation_id=task.details.get("correlation_id"),
        dispatch_id=task.details.get("hitl_dispatch_id"),
        queue_name=task.details.get("queue_name"),
        action_id=action_id,
    )
    request = SubmitHitlReviewRequest.model_validate(action_payload.get("request", {}))
    try:
        result = container.authoring_service.process_hitl_action(
            task_id=task_id,
            request=request,
            action_id=action_id,
        )
    except Exception as exc:
        failed = container.task_service.get_task(task_id)
        log_runtime_event(
            "worker.authoring_hitl_action_failed",
            service="worker",
            component="celery",
            level="ERROR",
            logger=_worker_logger,
            task_id=task_id,
            task_type=failed.task_type,
            correlation_id=failed.details.get("correlation_id"),
            dispatch_id=failed.details.get("hitl_dispatch_id"),
            queue_name=failed.details.get("queue_name"),
            action_id=action_id,
            error=str(exc),
        )
        raise
    current = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.authoring_hitl_action_completed",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=current.task_type,
        correlation_id=current.details.get("correlation_id"),
        dispatch_id=current.details.get("hitl_dispatch_id"),
        queue_name=current.details.get("queue_name"),
        action_id=action_id,
        status=result.status,
        decision=request.decision,
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
    task = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.knowledge_indexing_task_started",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=task.task_type,
        correlation_id=task.details.get("correlation_id"),
        dispatch_id=task.details.get("dispatch_id"),
        queue_name=task.details.get("queue_name"),
    )
    request = StartKnowledgeIndexingTaskRequest.model_validate(request_payload)
    try:
        result = container.knowledge_indexing_service.run_existing_task(task_id=task_id, request=request)
    except Exception as exc:
        failed = container.task_service.get_task(task_id)
        log_runtime_event(
            "worker.knowledge_indexing_task_failed",
            service="worker",
            component="celery",
            level="ERROR",
            logger=_worker_logger,
            task_id=task_id,
            task_type=failed.task_type,
            correlation_id=failed.details.get("correlation_id"),
            dispatch_id=failed.details.get("dispatch_id"),
            queue_name=failed.details.get("queue_name"),
            error=str(exc),
        )
        raise
    current = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.knowledge_indexing_task_completed",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=current.task_type,
        correlation_id=current.details.get("correlation_id"),
        dispatch_id=current.details.get("dispatch_id"),
        queue_name=current.details.get("queue_name"),
        status=result.status,
    )
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
    task = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.retrieval_task_started",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=task.task_type,
        correlation_id=task.details.get("correlation_id"),
        dispatch_id=task.details.get("dispatch_id"),
        queue_name=task.details.get("queue_name"),
    )
    request = StartRetrievalTaskRequest.model_validate(request_payload)
    try:
        result = container.retrieval_service.run_existing_task(task_id=task_id, request=request)
    except Exception as exc:
        failed = container.task_service.get_task(task_id)
        log_runtime_event(
            "worker.retrieval_task_failed",
            service="worker",
            component="celery",
            level="ERROR",
            logger=_worker_logger,
            task_id=task_id,
            task_type=failed.task_type,
            correlation_id=failed.details.get("correlation_id"),
            dispatch_id=failed.details.get("dispatch_id"),
            queue_name=failed.details.get("queue_name"),
            error=str(exc),
        )
        raise
    current = container.task_service.get_task(task_id)
    log_runtime_event(
        "worker.retrieval_task_completed",
        service="worker",
        component="celery",
        logger=_worker_logger,
        task_id=task_id,
        task_type=current.task_type,
        correlation_id=current.details.get("correlation_id"),
        dispatch_id=current.details.get("dispatch_id"),
        queue_name=current.details.get("queue_name"),
        status=result.status,
    )
    return result.model_dump(mode="json")
