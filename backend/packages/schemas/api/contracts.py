from __future__ import annotations

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