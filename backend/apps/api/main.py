from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status

from application.errors import (
    InvalidCursorError,
    InvalidTaskStateError,
    TaskArtifactLinkNotFoundError,
    TaskNotFoundError,
    WorkflowExecutionError,
)
from apps.api.dependencies import ApiContainer, get_container
from schemas.api.contracts import (
    EvidencePackResponse,
    HitlActionsResponse,
    HitlReviewStatusResponse,
    ResumeTaskRequest,
    SubmitHitlReviewRequest,
    StartAuthoringTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskArtifactResponse,
    TaskEventsResponse,
    TaskEventsSummaryResponse,
    TaskHistoryResponse,
    TaskStatusResponse,
)

app = FastAPI(title="LangGraph Document AI API", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict:
    """Проверка доступности API сервиса."""

    return {"status": "ok"}


@app.post("/api/v1/tasks/retrieval/start", response_model=StartTaskResponse)
def start_retrieval_task(
    request: StartRetrievalTaskRequest,
    container: ApiContainer = Depends(get_container),
) -> StartTaskResponse:
    """Запускает retrieval workflow и возвращает task id."""

    try:
        return container.retrieval_service.start(request)
    except WorkflowExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/v1/tasks/authoring/start", response_model=StartTaskResponse)
def start_authoring_task(
    request: StartAuthoringTaskRequest,
    container: ApiContainer = Depends(get_container),
) -> StartTaskResponse:
    """Запускает authoring workflow и возвращает task id."""

    try:
        return container.authoring_service.start(request)
    except WorkflowExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/v1/tasks/authoring/start_async", response_model=StartTaskResponse)
def start_authoring_task_async(
    request: StartAuthoringTaskRequest,
    container: ApiContainer = Depends(get_container),
) -> StartTaskResponse:
    """Ставит authoring workflow в async очередь и возвращает queued task id."""

    try:
        return container.authoring_service.start_async(request, dispatcher=container.authoring_dispatcher)
    except WorkflowExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/api/v1/tasks", response_model=TaskHistoryResponse)
def get_tasks_history(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None, min_length=8, max_length=512),
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    updated_from: datetime | None = Query(default=None, alias="from"),
    updated_to: datetime | None = Query(default=None, alias="to"),
    container: ApiContainer = Depends(get_container),
) -> TaskHistoryResponse:
    """Возвращает историю задач с фильтрами и курсорной пагинацией."""

    try:
        return container.retrieval_service.history(
            limit=limit,
            cursor=cursor,
            status=status_filter,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/api/v1/tasks/events", response_model=TaskEventsResponse)
def get_task_events(
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str | None = Query(default=None, min_length=8, max_length=512),
    task_id: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    from_status: str | None = Query(default=None),
    to_status: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    container: ApiContainer = Depends(get_container),
) -> TaskEventsResponse:
    """Возвращает аудит переходов статусов задач с фильтрами и курсорами."""

    try:
        return container.retrieval_service.events(
            limit=limit,
            cursor=cursor,
            task_id=task_id,
            task_type=task_type,
            from_status=from_status,
            to_status=to_status,
            created_from=created_from,
            created_to=created_to,
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/api/v1/tasks/events/summary", response_model=TaskEventsSummaryResponse)
def get_task_events_summary(
    task_id: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    from_status: str | None = Query(default=None),
    to_status: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    container: ApiContainer = Depends(get_container),
) -> TaskEventsSummaryResponse:
    """Возвращает агрегированную сводку по переходам статусов задач."""

    return container.retrieval_service.events_summary(
        task_id=task_id,
        task_type=task_type,
        from_status=from_status,
        to_status=to_status,
        created_from=created_from,
        created_to=created_to,
    )


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    container: ApiContainer = Depends(get_container),
) -> TaskStatusResponse:
    """Возвращает статус выполнения задачи."""

    try:
        return container.retrieval_service.status(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/api/v1/tasks/{task_id}/evidence", response_model=EvidencePackResponse)
def get_task_evidence(
    task_id: str,
    container: ApiContainer = Depends(get_container),
) -> EvidencePackResponse:
    """Возвращает собранный evidence pack по задаче."""

    try:
        return container.retrieval_service.evidence(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/v1/tasks/{task_id}/artifact", response_model=TaskArtifactResponse)
def get_task_artifact(
    task_id: str,
    container: ApiContainer = Depends(get_container),
) -> TaskArtifactResponse:
    """Возвращает итоговый authoring-артефакт по задаче."""

    try:
        return container.authoring_service.artifact(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskArtifactLinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/v1/tasks/{task_id}/hitl", response_model=HitlReviewStatusResponse)
def get_task_hitl_status(
    task_id: str,
    container: ApiContainer = Depends(get_container),
) -> HitlReviewStatusResponse:
    """Возвращает HITL-статус задачи authoring."""

    try:
        return container.authoring_service.hitl_status(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/v1/hitl/actions", response_model=HitlActionsResponse)
def get_hitl_actions(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None, min_length=8, max_length=512),
    task_id: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    reviewer: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    container: ApiContainer = Depends(get_container),
) -> HitlActionsResponse:
    """Возвращает историю reviewer действий HITL с фильтрами и курсорами."""

    try:
        return container.authoring_service.list_hitl_actions(
            limit=limit,
            cursor=cursor,
            task_id=task_id,
            decision=decision,
            status=status_filter,
            reviewer=reviewer,
            created_from=created_from,
            created_to=created_to,
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/v1/tasks/{task_id}/hitl/submit", response_model=TaskStatusResponse)
def submit_task_hitl(
    task_id: str,
    request: SubmitHitlReviewRequest,
    container: ApiContainer = Depends(get_container),
) -> TaskStatusResponse:
    """Принимает ручное решение reviewer и продолжает authoring flow."""

    try:
        return container.authoring_service.submit_hitl(
            task_id,
            request,
            dispatcher=container.authoring_dispatcher,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkflowExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/v1/tasks/{task_id}/resume", response_model=TaskStatusResponse)
def resume_task(
    task_id: str,
    request: ResumeTaskRequest,
    container: ApiContainer = Depends(get_container),
) -> TaskStatusResponse:
    """Возобновляет задачу из checkpoint состояния."""

    try:
        return container.retrieval_service.resume(task_id, request)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
