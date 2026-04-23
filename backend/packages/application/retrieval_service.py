from __future__ import annotations

from datetime import datetime

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import InvalidTaskStateError, WorkflowExecutionError
from application.task_service import TaskApplicationService
from domain_rag.retrieval import RetrievalPackWorkflow, build_retrieval_workflow
from schemas.api.contracts import (
    EvidencePackResponse,
    ResumeTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskEventItem,
    TaskEventTransitionSummaryItem,
    TaskEventsResponse,
    TaskEventsSummaryResponse,
    TaskHistoryItem,
    TaskHistoryResponse,
    TaskStatusResponse,
)
from schemas.workflow.states import RetrievalWorkflowState


class RetrievalApplicationService:
    """Application service для retrieval task lifecycle."""

    def __init__(
        self,
        task_service: TaskApplicationService,
        canonical_document_service: CanonicalDocumentApplicationService | None = None,
    ) -> None:
        self._task_service = task_service
        self._canonical_document_service = canonical_document_service

    def _build_workflow(
        self,
        *,
        case_dataset_id: str | None = None,
        case_dataset_path: str | None = None,
        case_dataset_dir: str | None = None,
        knowledge_source: str | None = None,
        canonical_doc_ids: list[str] | None = None,
    ) -> RetrievalPackWorkflow:
        return build_retrieval_workflow(
            case_dataset_id=case_dataset_id,
            case_dataset_path=case_dataset_path,
            case_dataset_dir=case_dataset_dir,
            knowledge_source=knowledge_source,
            canonical_document_service=self._canonical_document_service,
            canonical_doc_ids=canonical_doc_ids,
            checkpointer=self._task_service.get_langgraph_checkpointer(),
        )

    def start(self, request: StartRetrievalTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="retrieval_pack")

        task_context = {**request.task_context, "task_id": task.task_id}
        case_dataset_id = task_context.get("case_dataset_id")
        case_dataset_path = task_context.get("case_dataset_path")
        case_dataset_dir = task_context.get("case_dataset_dir")
        knowledge_source = task_context.get("knowledge_source")
        canonical_doc_ids = _normalize_doc_ids(task_context.get("canonical_doc_ids"))
        workflow = self._build_workflow(
            case_dataset_id=case_dataset_id,
            case_dataset_path=case_dataset_path,
            case_dataset_dir=case_dataset_dir,
            knowledge_source=knowledge_source,
            canonical_doc_ids=canonical_doc_ids,
        )

        initial_state = RetrievalWorkflowState(
            query=request.query,
            filters=request.filters,
            task_context=task_context,
        )

        # Ветка interrupt: фиксируем checkpoint и ожидаем resume-решение от человека.
        if bool(task_context.get("force_interrupt", False)):
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
            "knowledge_source": knowledge_source or "case_dataset",
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

    def history(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskHistoryResponse:
        page = self._task_service.list_tasks(
            limit=limit,
            cursor=cursor,
            status=status,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )
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
            for item in page.items
        ]
        return TaskHistoryResponse(
            items=items,
            limit=page.limit,
            total_returned=page.total_returned,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    def events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventsResponse:
        page = self._task_service.list_task_events(
            limit=limit,
            cursor=cursor,
            task_id=task_id,
            task_type=task_type,
            from_status=from_status,
            to_status=to_status,
            created_from=created_from,
            created_to=created_to,
        )
        items = [
            TaskEventItem(
                event_id=item.event_id,
                task_id=item.task_id,
                task_type=item.task_type,
                from_status=item.from_status,
                to_status=item.to_status,
                from_current_node=item.from_current_node,
                to_current_node=item.to_current_node,
                event_payload=item.event_payload,
                created_at=item.created_at,
            )
            for item in page.items
        ]
        return TaskEventsResponse(
            items=items,
            limit=page.limit,
            total_returned=page.total_returned,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    def events_summary(
        self,
        *,
        task_id: str | None = None,
        task_type: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskEventsSummaryResponse:
        summary = self._task_service.summarize_task_events(
            task_id=task_id,
            task_type=task_type,
            from_status=from_status,
            to_status=to_status,
            created_from=created_from,
            created_to=created_to,
        )
        return TaskEventsSummaryResponse(
            total_events=summary.total_events,
            unique_tasks=summary.unique_tasks,
            transitions=[
                TaskEventTransitionSummaryItem(
                    from_status=item.from_status,
                    to_status=item.to_status,
                    total=item.total,
                )
                for item in summary.transitions
            ],
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
        merged_task_context = {**state.task_context}
        merged_task_context.setdefault("task_id", task_id)
        state = state.model_copy(update={"task_context": merged_task_context})

        case_dataset_id = state.task_context.get("case_dataset_id")
        case_dataset_path = state.task_context.get("case_dataset_path")
        case_dataset_dir = state.task_context.get("case_dataset_dir")
        knowledge_source = state.task_context.get("knowledge_source")
        canonical_doc_ids = _normalize_doc_ids(state.task_context.get("canonical_doc_ids"))
        workflow = self._build_workflow(
            case_dataset_id=case_dataset_id,
            case_dataset_path=case_dataset_path,
            case_dataset_dir=case_dataset_dir,
            knowledge_source=knowledge_source,
            canonical_doc_ids=canonical_doc_ids,
        )

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
                "knowledge_source": knowledge_source or "case_dataset",
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


def _normalize_doc_ids(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else None
    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized or None
    return None
