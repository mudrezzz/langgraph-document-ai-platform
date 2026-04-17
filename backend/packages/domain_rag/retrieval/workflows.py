from __future__ import annotations

from framework.rag.pipeline import HierarchicalRAGPipeline
from framework.workflows.base import BaseWorkflow
from schemas.workflow.states import RetrievalWorkflowState


class RetrievalPackWorkflow(BaseWorkflow):
    """Первый рабочий вертикальный срез retrieval workflow."""

    def __init__(self, pipeline: HierarchicalRAGPipeline) -> None:
        super().__init__(use_langgraph_runtime=True)
        self._pipeline = pipeline
        self.compile()

    def state_schema(self) -> type[RetrievalWorkflowState]:
        return RetrievalWorkflowState

    def execute(self, state: RetrievalWorkflowState) -> RetrievalWorkflowState:
        # Базовая валидация входного запроса для error-ветки API.
        if not state.query.strip():
            raise ValueError("Пустой query недопустим для retrieval workflow")

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

    def execute_resume(self, state: RetrievalWorkflowState) -> RetrievalWorkflowState:
        # Для retrieval-сценария resume выполняет ту же бизнес-логику пересборки evidence.
        return self.execute(state)

    @staticmethod
    def _calculate_confidence(scores: list[float]) -> float:
        if not scores:
            return 0.0

        top_scores = sorted(scores, reverse=True)[:3]
        return sum(top_scores) / float(len(top_scores))