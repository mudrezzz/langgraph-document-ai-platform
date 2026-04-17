from __future__ import annotations

from pydantic import BaseModel, Field


class ResumePayload(BaseModel):
    """Payload возобновления workflow после interrupt."""

    task_id: str
    decision: str
    comment: str | None = None
    metadata: dict = Field(default_factory=dict)


class ApprovalPayload(BaseModel):
    """Payload ручного approve/reject."""

    task_id: str
    approved: bool
    reviewer: str
    comment: str | None = None
