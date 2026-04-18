from __future__ import annotations

from application.errors import InvalidTaskStateError, WorkflowExecutionError
from application.task_service import TaskApplicationService
from domain_rag.retrieval import RetrievalPackWorkflow, build_retrieval_workflow
from schemas.api.contracts import (
    EvidencePackResponse,
    ResumeTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskHistoryItem,
    TaskHistoryResponse,
    TaskStatusResponse,
)
from schemas.workflow.states import RetrievalWorkflowState


class RetrievalApplicationService:
    """Application service для retrieval task lifecycle."""

    def __init__(self, task_service: TaskApplicationService) -> None:
        self._task_service = task_service

    def _build_workflow(self, *, case_dataset_id: str | None = None, case_dataset_path: str | None = None) -> RetrievalPackWorkflow:
        return build_retrieval_workflow(
            case_dataset_id=case_dataset_id,
            case_dataset_path=case_dataset_path,
        )

    def start(self, request: StartRetrievalTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="retrieval_pack")

        case_dataset_id = request.task_context.get("case_dataset_id")
        case_dataset_path = request.task_context.get("case_dataset_path")
        workflow = self._build_workflow(case_dataset_id=case_dataset_id, case_dataset_path=case_dataset_path)

        initial_state = RetrievalWorkflowState(
            query=request.query,
            filters=request.filters,
            task_context=request.task_context,
        )

        # Ветка interrupt: фиксируем checkpoint и ожидаем resume-решение от человека.
        if bool(request.task_context.get("force_interrupt", False)):
            self._task_service.save_checkpoint(task.task_id, initial_state.model_dump(mode="json"))
            self._task_service.update_task(
                task.task_id,
                status="interrupted",
                current_node="human_gate",
                details={"reason": "forced_interrupt", "resume_required": True},
            )
            return StartTaskResponse(task_id=task.task_id, status="interrupted")

        try:
            result_state = workflow.invoke(initial_state)
        except Exception as exc:
            self._task_service.fail_task(
                task_id=task.task_id,
                state_payload=initial_state.model_dump(mode="json"),
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

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

    def history(self, limit: int = 50, offset: int = 0) -> TaskHistoryResponse:
        records = self._task_service.list_tasks(limit=limit, offset=offset)
        items = [
            TaskHistoryItem(
                task_id=item.task_id,
                task_type=item.task_type,
                status=item.status,
                current_node=item.current_node,
                details=item.details,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in records
        ]
        return TaskHistoryResponse(items=items, limit=limit, offset=offset, total_returned=len(items))

    def evidence(self, task_id: str) -> EvidencePackResponse:
        payload = self._task_service.get_state_payload(task_id)
        state = RetrievalWorkflowState.model_validate(payload)

        if state.evidence_pack is None:
            raise InvalidTaskStateError("Evidence pack отсутствует в состоянии retrieval workflow")

        return EvidencePackResponse(task_id=task_id, evidence_pack=state.evidence_pack)

    def resume(self, task_id: str, request: ResumeTaskRequest) -> TaskStatusResponse:
        payload = self._task_service.get_state_payload(task_id)
        state = RetrievalWorkflowState.model_validate(payload)

        case_dataset_id = state.task_context.get("case_dataset_id")
        case_dataset_path = state.task_context.get("case_dataset_path")
        workflow = self._build_workflow(case_dataset_id=case_dataset_id, case_dataset_path=case_dataset_path)

        decision = request.decision.lower()

        if decision in {"rerun", "retry", "resume", "continue", "approve"}:
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
