from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.patterns.hitl_gate.config import HitlGateConfig
from agent_examples.patterns.hitl_gate.prompts import DEFAULT_QUERY
from agent_examples.patterns.hitl_gate.workflow import HitlWorkflowInput, run_hitl_workflow


@dataclass
class HitlGateAgent:
    """In-process HITL agent with reviewer decision loop."""

    config: HitlGateConfig

    def run(self, query: str = DEFAULT_QUERY, decisions: list[str] | None = None) -> dict[str, Any]:
        if decisions is None:
            decisions = ["needs_changes", "approve"]

        workflow_result = run_hitl_workflow(
            HitlWorkflowInput(
                query=query,
                requester=self.config.requester,
                case_dataset_id=self.config.case_dataset_id,
                decisions=list(decisions),
                template_id=self.config.template_id,
                workflow_mode=self.config.workflow_mode,
                draft_strategy=self.config.draft_strategy,
                artifact_title=self.config.artifact_title,
                artifact_format=self.config.artifact_format,
                hitl_required=self.config.hitl_required,
                hitl_max_iterations=self.config.hitl_max_iterations,
            )
        )
        final_document = dict(workflow_result.get("final_document", {}))
        content = str(final_document.get("content", ""))

        return {
            "pattern": "hitl_gate",
            "execution_model": "in_process_framework_workflow",
            "query": query,
            "task_status": workflow_result.get("task_status", "failed"),
            "hitl_decisions_applied": workflow_result.get("decision_history", []),
            "artifact_title": workflow_result.get("artifact_title"),
            "artifact_format": workflow_result.get("artifact_format"),
            "recommendation": workflow_result.get("review_result", {}).get("recommendation"),
            "steps_total": len(workflow_result.get("workflow_steps", [])),
            "traceability_sections": len(workflow_result.get("section_traceability", [])),
            "content_preview": (content[:397] + "...") if len(content) > 400 else content,
        }
