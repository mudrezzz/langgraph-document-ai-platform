from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.rag.contracts import EvidencePack, RetrievalFilter, SourceRef


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


class TaskEventTransitionSummaryItem(BaseModel):
    """Агрегированная запись перехода статусов."""

    from_status: str | None = None
    to_status: str
    total: int


class TaskEventsSummaryResponse(BaseModel):
    """Сводка по переходам статусов задач."""

    total_events: int
    unique_tasks: int
    transitions: list[TaskEventTransitionSummaryItem] = Field(default_factory=list)


class StartRetrievalTaskRequest(BaseModel):
    """Типизированный запрос на запуск retrieval workflow."""

    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    task_context: dict = Field(default_factory=dict)


class StartAuthoringTaskRequest(BaseModel):
    """Типизированный запрос на запуск authoring workflow."""

    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    task_context: dict = Field(default_factory=dict)
    artifact_type: str = "release_report"
    artifact_title: str | None = None
    artifact_format: str = "markdown"
    draft_strategy: Literal["auto", "deterministic", "llm"] = "auto"


class ResumeTaskRequest(BaseModel):
    """Типизированный payload для resume endpoint."""

    decision: str
    comment: str | None = None
    metadata: dict = Field(default_factory=dict)


class EvidencePackResponse(BaseModel):
    """Ответ API с evidence pack для конкретной задачи."""

    task_id: str
    evidence_pack: EvidencePack


class TaskArtifactTraceabilityResponse(BaseModel):
    """Traceability-связи итогового артефакта с retrieval источниками."""

    retrieval_task_id: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class TaskArtifactResponse(BaseModel):
    """Ответ API с итоговым authoring-артефактом по задаче."""

    task_id: str
    artifact_id: str
    artifact_type: str
    title: str | None = None
    content: str
    format: str
    metadata: dict = Field(default_factory=dict)
    traceability: TaskArtifactTraceabilityResponse
