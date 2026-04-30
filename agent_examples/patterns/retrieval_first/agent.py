from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_examples.patterns.retrieval_first.config import RetrievalFirstConfig
from agent_examples.patterns.retrieval_first.prompts import DEFAULT_QUERY
from agent_examples.patterns.retrieval_first.tools import build_default_filters
from agent_examples.patterns.retrieval_first.workflow import RetrievalWorkflowInput, run_retrieval_workflow


@dataclass
class RetrievalFirstAgent:
    """Minimal in-process retrieval agent.

    This demo shows the intended developer experience:
    build an agent as Python composition over framework contracts,
    not as an external HTTP client.
    """

    config: RetrievalFirstConfig

    def run(self, query: str = DEFAULT_QUERY) -> dict[str, Any]:
        workflow_state = run_retrieval_workflow(
            RetrievalWorkflowInput(
                query=query,
                filters=build_default_filters(),
                case_dataset_id=self.config.case_dataset_id,
                requester=self.config.requester,
            )
        )

        evidence_pack = workflow_state.evidence_pack
        if evidence_pack is None:
            selected_blocks = []
            selected_sources = []
            confidence_notes = []
        else:
            selected_blocks = evidence_pack.selected_blocks
            selected_sources = evidence_pack.selected_sources
            confidence_notes = evidence_pack.confidence_notes

        return {
            "pattern": "retrieval_first",
            "execution_model": "in_process_framework_workflow",
            "query": query,
            "case_dataset_id": self.config.case_dataset_id,
            "confidence": workflow_state.confidence,
            "evidence_blocks": len(selected_blocks),
            "top_sources": [
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
                for source in selected_sources[:3]
            ],
            "unresolved_gaps": workflow_state.unresolved_gaps,
            "confidence_notes": confidence_notes,
        }
