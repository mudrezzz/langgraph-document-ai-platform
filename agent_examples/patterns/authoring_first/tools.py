from __future__ import annotations

from typing import Any


def build_project_context(
    *,
    requester: str,
    case_dataset_id: str,
    workflow_mode: str,
    draft_strategy: str,
) -> dict[str, Any]:
    return {
        "requester": requester,
        "case_dataset_id": case_dataset_id,
        "workflow_mode": workflow_mode,
        "draft_strategy": draft_strategy,
    }


def build_workflow_steps(
    *,
    retrieval_confidence: float | None,
    section_steps: list[dict[str, Any]],
    review_status: str,
    recommendation: str,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        {
            "name": "retrieval",
            "status": "completed",
            "confidence": retrieval_confidence,
        },
        {"name": "research_summary", "status": "completed"},
        {"name": "writer_draft", "status": "completed"},
        {
            "name": "review",
            "status": review_status,
            "recommendation": recommendation,
        },
    ]
    steps.extend(section_steps)
    steps.extend(
        [
            {"name": "assemble_document", "status": "completed"},
            {"name": "export_artifact", "status": "completed"},
        ]
    )
    return steps


def preview_content(content: str, *, limit: int = 400) -> str:
    cleaned = content.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
