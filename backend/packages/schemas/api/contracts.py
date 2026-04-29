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


class TaskEventTimeBucketSummaryItem(BaseModel):
    """Агрегированная запись task events по временному бакету."""

    bucket_start: datetime
    total_events: int
    unique_tasks: int


class TaskEventsSummaryResponse(BaseModel):
    """Сводка по переходам статусов задач."""

    total_events: int
    unique_tasks: int
    transitions: list[TaskEventTransitionSummaryItem] = Field(default_factory=list)
    daily: list[TaskEventTimeBucketSummaryItem] = Field(default_factory=list)
    weekly: list[TaskEventTimeBucketSummaryItem] = Field(default_factory=list)


class TaskStatusSummaryItem(BaseModel):
    """Агрегированная запись по текущему статусу задач."""

    status: str
    total: int


class TaskTypeObservabilitySummaryItem(BaseModel):
    """Dashboard-friendly агрегаты по task type."""

    task_type: str
    total: int
    async_total: int = 0
    completed_total: int = 0
    failed_total: int = 0
    avg_duration_ms: int | None = None
    avg_queue_wait_ms: int | None = None
    avg_selected_block_count: float | None = None
    avg_confidence: float | None = None
    unresolved_gaps_total: int = 0
    llm_tokens_prompt_total: int = 0
    llm_tokens_completion_total: int = 0
    llm_tokens_total: int = 0


class TaskObservabilityResponse(BaseModel):
    """Сводка execution plane поверх task registry."""

    total_tasks: int
    queued_tasks: int = 0
    running_tasks: int = 0
    waiting_human_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    async_tasks: int = 0
    avg_duration_ms: int | None = None
    max_duration_ms: int | None = None
    avg_queue_wait_ms: int | None = None
    avg_selected_block_count: float | None = None
    avg_confidence: float | None = None
    tasks_with_unresolved_gaps: int = 0
    unresolved_gaps_total: int = 0
    llm_tokens_prompt_total: int = 0
    llm_tokens_completion_total: int = 0
    llm_tokens_total: int = 0
    statuses: list[TaskStatusSummaryItem] = Field(default_factory=list)
    task_types: list[TaskTypeObservabilitySummaryItem] = Field(default_factory=list)


class StartRetrievalTaskRequest(BaseModel):
    """Типизированный запрос на запуск retrieval workflow."""

    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    task_context: dict = Field(default_factory=dict)


class StartKnowledgeIndexingTaskRequest(BaseModel):
    """Типизированный запрос на запуск canonical knowledge indexing."""

    source_paths: list[str] = Field(min_length=1)
    document_version: str = "1"
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
    workflow_mode: Literal["single_pass", "multi_step"] = "multi_step"
    hitl_required: bool = False


class ResumeTaskRequest(BaseModel):
    """Типизированный payload для resume endpoint."""

    decision: str
    comment: str | None = None
    metadata: dict = Field(default_factory=dict)


class SubmitHitlReviewRequest(BaseModel):
    """Запрос ручного решения по задаче в статусе waiting_human."""

    decision: Literal["approve", "needs_changes", "reject"]
    comment: str | None = None
    metadata: dict = Field(default_factory=dict)
    idempotency_key: str | None = None
    expected_iteration: int | None = Field(default=None, ge=1)


class HitlReviewActionResponse(BaseModel):
    """Запись действия человека в HITL контуре."""

    action_id: str | None = None
    iteration: int | None = None
    decision: str
    comment: str | None = None
    status: str | None = None
    idempotency_key: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class HitlActionsResponse(BaseModel):
    """История HITL действий с пагинацией."""

    items: list[HitlReviewActionResponse] = Field(default_factory=list)
    limit: int
    total_returned: int
    next_cursor: str | None = None
    has_more: bool = False


class HitlActionStatusSummaryItem(BaseModel):
    """Агрегированная запись по статусу reviewer actions."""

    status: str
    total: int


class HitlDecisionSummaryItem(BaseModel):
    """Агрегированная запись по reviewer decisions."""

    decision: str
    total: int


class HitlReviewerSummaryItem(BaseModel):
    """Агрегированная нагрузка по reviewer."""

    reviewer: str
    total: int
    approve_total: int = 0
    needs_changes_total: int = 0
    reject_total: int = 0


class HitlObservabilityResponse(BaseModel):
    """Сводка reviewer/HITL activity поверх hitl_actions read-model."""

    total_actions: int
    unique_tasks: int
    pending_actions: int = 0
    queued_actions: int = 0
    processing_actions: int = 0
    completed_actions: int = 0
    approve_total: int = 0
    needs_changes_total: int = 0
    reject_total: int = 0
    avg_iteration: float | None = None
    max_iteration: int | None = None
    latest_action_at: datetime | None = None
    statuses: list[HitlActionStatusSummaryItem] = Field(default_factory=list)
    decisions: list[HitlDecisionSummaryItem] = Field(default_factory=list)
    reviewers: list[HitlReviewerSummaryItem] = Field(default_factory=list)


class HitlOutlineSectionResponse(BaseModel):
    """Секция outline snapshot для HITL authoring."""

    section_id: str
    title: str
    review_status: str = "not_reviewed"
    objective: str | None = None
    required_keywords: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class HitlOutlineResponse(BaseModel):
    """Outline snapshot для ручного решения до section authoring."""

    template_id: str
    sections: list[HitlOutlineSectionResponse] = Field(default_factory=list)


class HitlReviewStatusResponse(BaseModel):
    """Текущий статус HITL по задаче."""

    task_id: str
    status: str
    required: bool
    current_iteration: int = 1
    max_iterations: int = 1
    deadline_at: datetime | None = None
    can_submit: bool = False
    pending_action_id: str | None = None
    pending_reason: str | None = None
    reviewer_notes: str | None = None
    phase: str | None = None
    outline: HitlOutlineResponse | None = None
    actions: list[HitlReviewActionResponse] = Field(default_factory=list)


class EvidencePackResponse(BaseModel):
    """Ответ API с evidence pack для конкретной задачи."""

    task_id: str
    evidence_pack: EvidencePack


class TaskArtifactSectionTraceabilityResponse(BaseModel):
    """Traceability-связи по отдельной секции итогового артефакта."""

    section_id: str
    title: str
    review_status: str = "not_reviewed"
    source_refs: list[SourceRef] = Field(default_factory=list)


class TaskArtifactTraceabilityResponse(BaseModel):
    """Traceability-связи итогового артефакта с retrieval источниками."""

    retrieval_task_id: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    sections: list[TaskArtifactSectionTraceabilityResponse] = Field(default_factory=list)


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


class UpsertTemplateRequest(BaseModel):
    """Запрос на регистрацию или обновление reusable template."""

    version: str = "1"
    status: Literal["draft", "published", "deprecated", "archived"] = "draft"
    sections: list[dict] = Field(default_factory=list)
    validation_rules: list[dict] = Field(default_factory=list)
    assembly_rules: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class PublishTemplateRequest(BaseModel):
    """Запрос на публикацию конкретной версии reusable template."""

    version: str


class SetTemplateStatusRequest(BaseModel):
    """Запрос на explicit lifecycle transition reusable template."""

    version: str
    status: Literal["draft", "published", "deprecated", "archived"]
    reason: str | None = None
    actor: str | None = None
    metadata: dict = Field(default_factory=dict)


class TemplateResponse(BaseModel):
    """Ответ API с сохраненным template spec."""

    template_id: str
    version: str
    status: Literal["draft", "published", "deprecated", "archived"] = "draft"
    template_spec: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TemplateListResponse(BaseModel):
    """Страница reusable templates."""

    items: list[TemplateResponse] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
