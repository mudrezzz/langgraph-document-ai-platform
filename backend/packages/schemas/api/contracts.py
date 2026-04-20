from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.rag.contracts import EvidencePack, RetrievalFilter


class StartTaskRequest(BaseModel):
    """Запрос на запуск workflow-задачи."""

    task_type: str
    payload: dict = Field(default_factory=dict)


class StartTaskResponse(BaseModel):
    """Ответ на создание задачи."""

    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Текущее состояние задачи."""

    task_id: str
    status: str
    current_node: str | None = None
    details: dict = Field(default_factory=dict)


class TaskHistoryItem(BaseModel):
    """Элемент истории задач."""

    task_id: str
    task_type: str
    status: str
    current_node: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskHistoryResponse(BaseModel):
    """Ответ API с историей задач."""

    items: list[TaskHistoryItem] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class TaskEventItem(BaseModel):
    """Элемент аудита переходов статусов."""

    event_id: int | None = None
    task_id: str
    task_type: str
    from_status: str | None = None
    to_status: str
    from_current_node: str | None = None
    to_current_node: str | None = None
    event_payload: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class TaskEventsResponse(BaseModel):
    """Ответ API с аудитом переходов статусов задач."""

    items: list[TaskEventItem] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class StartRetrievalTaskRequest(BaseModel):
    """Типизированный запрос на запуск retrieval workflow."""

    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    task_context: dict = Field(default_factory=dict)


class ResumeTaskRequest(BaseModel):
    """Типизированный payload для resume endpoint."""

    decision: str
    comment: str | None = None
    metadata: dict = Field(default_factory=dict)


class EvidencePackResponse(BaseModel):
    """Ответ API с evidence pack для конкретной задачи."""

    task_id: str
    evidence_pack: EvidencePack
