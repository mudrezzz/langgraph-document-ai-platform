from __future__ import annotations

from typing import Any

from schemas.authoring.contracts import SectionArtifact


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


def apply_human_feedback_to_sections(
    *,
    section_artifacts: list[SectionArtifact],
    comment: str,
    iteration: int,
) -> list[SectionArtifact]:
    updated: list[SectionArtifact] = []
    for item in section_artifacts:
        content = item.content + f"\n\n### Human Feedback Iteration {iteration}\n{comment}"
        metadata = dict(item.metadata)
        metadata["hitl_feedback_iteration"] = iteration
        metadata["hitl_feedback_comment"] = comment
        updated.append(
            item.model_copy(
                update={
                    "content": content,
                    "review_status": "needs_revision",
                    "metadata": metadata,
                }
            )
        )
    return updated


def build_hitl_steps(
    *,
    decision_history: list[dict[str, Any]],
    final_status: str,
    recommendation: str,
) -> list[dict[str, Any]]:
    steps = [{"name": "retrieval", "status": "completed"}]
    for item in decision_history:
        steps.append(
            {
                "name": f"hitl.iteration_{item['iteration']}",
                "status": item["decision"],
                "comment": item.get("comment", ""),
            }
        )
    steps.extend(
        [
            {"name": "review_finalize", "status": final_status, "recommendation": recommendation},
            {"name": "assemble_document", "status": "completed" if final_status == "completed" else "skipped"},
            {"name": "export_artifact", "status": "completed" if final_status == "completed" else "skipped"},
        ]
    )
    return steps
