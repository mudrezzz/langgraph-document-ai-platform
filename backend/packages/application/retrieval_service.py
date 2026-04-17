from __future__ import annotations

from application.errors import InvalidTaskStateError
from application.task_service import TaskApplicationService
from domain_rag.retrieval import RetrievalPackWorkflow, build_retrieval_workflow
from schemas.api.contracts import (
    EvidencePackResponse,
    ResumeTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskStatusResponse,
)
from schemas.workflow.states import RetrievalWorkflowState


class RetrievalApplicationService:
    """Application service для retrieval task lifecycle."""

    def __init__(self, task_service: TaskApplicationService) -> None:
        self._task_service = task_service

    def _build_workflow(self) -> RetrievalPackWorkflow:
        return build_retrieval_workflow()

    def start(self, request: StartRetrievalTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="retrieval_pack")
        workflow = self._build_workflow()

        initial_state = RetrievalWorkflowState(
            query=request.query,
            filters=request.filters,
            task_context=request.task_context,
        )

        result_state = workflow.invoke(initial_state)

        details = {
            "confidence": result_state.confidence,
            "selected_summary_count": len(result_state.selected_summaries),
            "selected_block_count": len(result_state.selected_blocks),
            "reranked_count": len(result_state.reranked_blocks),
        }

        self._task_service.complete_task(
            task_id=task.task_id,
            state_payload=result_state.model_dump(mode="json"),
            details=details,
        )

        return StartTaskResponse(task_id=task.task_id, status="completed")

    def status(self, task_id: str) -> TaskStatusResponse:
        task = self._task_service.get_task(task_id)
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            current_node=task.current_node,
            details=task.details,
        )

    def evidence(self, task_id: str) -> EvidencePackResponse:
        payload = self._task_service.get_state_payload(task_id)
        state = RetrievalWorkflowState.model_validate(payload)

        if state.evidence_pack is None:
            raise InvalidTaskStateError("Evidence pack отсутствует в состоянии retrieval workflow")

        return EvidencePackResponse(task_id=task_id, evidence_pack=state.evidence_pack)

    def resume(self, task_id: str, request: ResumeTaskRequest) -> TaskStatusResponse:
        payload = self._task_service.get_state_payload(task_id)
        state = RetrievalWorkflowState.model_validate(payload)
        workflow = self._build_workflow()

        # Для retrieval: поддерживаем повторный запуск по команде "rerun".
        if request.decision.lower() in {"rerun", "retry"}:
            merged_context = {**state.task_context, **request.metadata}
            rerun_state = state.model_copy(update={"task_context": merged_context})
            result = workflow.invoke(rerun_state)
            details = {
                "confidence": result.confidence,
                "selected_summary_count": len(result.selected_summaries),
                "selected_block_count": len(result.selected_blocks),
                "reranked_count": len(result.reranked_blocks),
                "resume_decision": request.decision,
            }
            self._task_service.complete_task(
                task_id=task_id,
                state_payload=result.model_dump(mode="json"),
                details=details,
            )
        else:
            # В остальных случаях просто подтверждаем валидность checkpoint-состояния.
            validated = workflow.resume(state)
            details = {
                "resume_decision": request.decision,
                "resume_comment": request.comment,
            }
            self._task_service.complete_task(
                task_id=task_id,
                state_payload=validated.model_dump(mode="json"),
                details=details,
            )

        return self.status(task_id)