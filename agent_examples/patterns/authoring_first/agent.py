from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.patterns.authoring_first.config import AuthoringFirstConfig
from agent_examples.patterns.authoring_first.prompts import DEFAULT_QUERY
from agent_examples.patterns.authoring_first.tools import preview_content
from agent_examples.patterns.authoring_first.workflow import (
    AuthoringWorkflowInput,
    run_authoring_workflow,
)


@dataclass
class AuthoringFirstAgent:
    """In-process authoring-first agent with explicit artifact assembly."""

    config: AuthoringFirstConfig

    def run(self, query: str = DEFAULT_QUERY) -> dict[str, Any]:
        workflow_result = run_authoring_workflow(
            AuthoringWorkflowInput(
                query=query,
                requester=self.config.requester,
                case_dataset_id=self.config.case_dataset_id,
                template_id=self.config.template_id,
                workflow_mode=self.config.workflow_mode,
                draft_strategy=self.config.draft_strategy,
                artifact_title=self.config.artifact_title,
                artifact_format=self.config.artifact_format,
            )
        )
        final_document = dict(workflow_result.get("final_document", {}))
        review_result = dict(workflow_result.get("review_result", {}))
        section_traceability = list(workflow_result.get("section_traceability", []))
        section_artifacts = list(workflow_result.get("section_artifacts", []))
        evidence_pack = workflow_result.get("evidence_pack")
        if hasattr(evidence_pack, "model_dump"):
            evidence_pack_payload = evidence_pack.model_dump(mode="json")
        elif isinstance(evidence_pack, dict):
            evidence_pack_payload = evidence_pack
        else:
            evidence_pack_payload = {}
        content = str(final_document.get("content", ""))
        return {
            "pattern": "authoring_first",
            "execution_model": "in_process_framework_workflow",
            "query": query,
            "case_dataset_id": self.config.case_dataset_id,
            "workflow_mode": workflow_result.get("workflow_mode"),
            "draft_strategy": workflow_result.get("draft_strategy"),
            "artifact_title": workflow_result.get("artifact_title"),
            "artifact_format": workflow_result.get("artifact_format"),
            "review_status": review_result.get("status"),
            "recommendation": review_result.get("recommendation"),
            "steps_total": len(workflow_result.get("workflow_steps", [])),
            "section_artifacts_total": len(section_artifacts),
            "traceability_sections": len(section_traceability),
            "evidence_blocks": len(evidence_pack_payload.get("selected_blocks", [])),
            "unresolved_gaps": workflow_result.get("unresolved_gaps", []),
            "content_preview": preview_content(content),
        }
