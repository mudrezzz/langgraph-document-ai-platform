from __future__ import annotations

from typing import Any

from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.workflows.base import BaseWorkflow
from schemas.workflow.states import RetrievalWorkflowState


class RetrievalPackWorkflow(BaseWorkflow):
    """Первый рабочий вертикальный срез retrieval workflow."""

    def __init__(self, pipeline: HierarchicalRAGPipeline) -> None:
        super().__init__()
        self._pipeline = pipeline

    def state_schema(self) -> type[RetrievalWorkflowState]:
        return RetrievalWorkflowState

    def invoke(self, payload: RetrievalWorkflowState | dict[str, Any]) -> RetrievalWorkflowState:
        state = self.state_schema().model_validate(payload)
        trace = self._pipeline.run_with_trace(query=state.query, filters=state.filters)

        confidence = self._calculate_confidence([item.score for item in trace.reranked_blocks])

        return state.model_copy(
            update={
                "selected_summaries": trace.summary_candidates,
                "selected_blocks": trace.detail_candidates,
                "reranked_blocks": trace.reranked_blocks,
                "evidence_pack": trace.evidence_pack,
                "confidence": confidence,
                "unresolved_gaps": trace.evidence_pack.unresolved_gaps,
            }
        )

    def resume(self, payload: RetrievalWorkflowState | dict[str, Any]) -> RetrievalWorkflowState:
        # В retrieval-сценарии базовый resume пока только валидирует состояние.
        return self.state_schema().model_validate(payload)

    @staticmethod
    def _calculate_confidence(scores: list[float]) -> float:
        if not scores:
            return 0.0

        top_scores = sorted(scores, reverse=True)[:3]
        return sum(top_scores) / float(len(top_scores))