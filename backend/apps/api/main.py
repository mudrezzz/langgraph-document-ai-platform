from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query, status

from application.errors import InvalidTaskStateError, TaskNotFoundError, WorkflowExecutionError
from apps.api.dependencies import ApiContainer, get_container
from schemas.api.contracts import (
    EvidencePackResponse,
    ResumeTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
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


@app.get("/api/v1/tasks", response_model=TaskHistoryResponse)
def get_tasks_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    container: ApiContainer = Depends(get_container),
) -> TaskHistoryResponse:
    """Возвращает историю задач в порядке убывания времени обновления."""

    return container.retrieval_service.history(limit=limit, offset=offset)


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
