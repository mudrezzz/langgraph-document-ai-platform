from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.api.contracts import (
    HitlActionStatusSummaryItem,
    HitlActionsResponse,
    HitlDecisionSummaryItem,
    HitlObservabilityResponse,
    HitlReviewActionResponse,
    HitlReviewStatusResponse,
    HitlReviewerSummaryItem,
    SubmitHitlReviewRequest,
    TaskStatusResponse,
)


class ReviewApprovalMcpGetHitlStatusInput(BaseModel):
    """Контракт входа MCP tool для чтения HITL-статуса задачи."""

    task_id: str


class ReviewApprovalMcpGetHitlStatusOutput(HitlReviewStatusResponse):
    """Контракт ответа MCP tool по текущему HITL-статусу."""


class ReviewApprovalMcpListHitlActionsInput(BaseModel):
    """Контракт входа MCP tool для списка reviewer/HITL действий."""

    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None
    task_id: str | None = None
    decision: str | None = None
    status: str | None = None
    reviewer: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class ReviewApprovalMcpListHitlActionsOutput(HitlActionsResponse):
    """Контракт ответа MCP tool по истории reviewer/HITL действий."""


class ReviewApprovalMcpSubmitHitlReviewInput(SubmitHitlReviewRequest):
    """Контракт входа MCP tool для отправки reviewer-решения."""

    task_id: str
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)


class ReviewApprovalMcpSubmitHitlReviewOutput(TaskStatusResponse):
    """Контракт ответа MCP tool после отправки reviewer-решения."""


class ReviewApprovalMcpGetHitlObservabilitySummaryInput(BaseModel):
    """Контракт входа MCP tool для агрегированной HITL observability summary."""

    task_id: str | None = None
    decision: str | None = None
    status: str | None = None
    reviewer: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class ReviewApprovalMcpGetHitlObservabilitySummaryOutput(HitlObservabilityResponse):
    """Контракт ответа MCP tool по reviewer/HITL observability summary."""


__all__ = [
    'ReviewApprovalMcpGetHitlStatusInput',
    'ReviewApprovalMcpGetHitlStatusOutput',
    'ReviewApprovalMcpListHitlActionsInput',
    'ReviewApprovalMcpListHitlActionsOutput',
    'ReviewApprovalMcpSubmitHitlReviewInput',
    'ReviewApprovalMcpSubmitHitlReviewOutput',
    'ReviewApprovalMcpGetHitlObservabilitySummaryInput',
    'ReviewApprovalMcpGetHitlObservabilitySummaryOutput',
    'HitlReviewActionResponse',
    'HitlActionStatusSummaryItem',
    'HitlDecisionSummaryItem',
    'HitlReviewerSummaryItem',
]
