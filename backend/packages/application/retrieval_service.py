from __future__ import annotations

from datetime import datetime, timezone

from application.async_dispatcher import RetrievalAsyncDispatcher
from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import InvalidTaskStateError, WorkflowExecutionError
from application.task_service import TaskApplicationService
from domain_rag.retrieval import RetrievalPackWorkflow, build_retrieval_workflow
from framework.models.interfaces import IEmbeddingGateway, IRerankGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from schemas.api.contracts import (
    EvidencePackResponse,
    ResumeTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskEventItem,
    TaskEventTimeBucketSummaryItem,
    TaskEventTransitionSummaryItem,
    TaskEventsResponse,
    TaskEventsSummaryResponse,
    TaskHistoryItem,
    TaskObservabilityResponse,
    TaskObservabilityTimeBucketSummaryItem,
    TaskStatusSummaryItem,
    TaskTypeObservabilitySummaryItem,
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
        embedding_gateway: IEmbeddingGateway | None = None,
        vector_store: PgVectorStoreAdapter | None = None,
        rerank_gateway: IRerankGateway | None = None,
    ) -> None:
        self._task_service = task_service
        self._canonical_document_service = canonical_document_service
        self._embedding_gateway = embedding_gateway
        self._vector_store = vector_store
        self._rerank_gateway = rerank_gateway

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
            embedding_gateway=self._embedding_gateway,
            vector_store=self._vector_store,
            rerank_gateway=self._rerank_gateway,
            checkpointer=self._task_service.get_langgraph_checkpointer(),
            node_event_sink=self._task_service.build_workflow_node_event_sink(),
        )

    def start(self, request: StartRetrievalTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="retrieval_pack")
        return self.run_existing_task(task_id=task.task_id, request=request)

    def start_async(
        self,
        request: StartRetrievalTaskRequest,
        *,
        dispatcher: RetrievalAsyncDispatcher,
    ) -> StartTaskResponse:
        task = self._task_service.create_task(
            task_type="retrieval_pack",
            initial_status="queued",
            initial_node="queued",
            details={
                "execution_mode": "async",
                "knowledge_source": request.task_context.get("knowledge_source", "case_dataset"),
            },
        )
        effective_context = {**request.task_context, "task_id": task.task_id}

        try:
            dispatch_id = dispatcher.enqueue_retrieval_start(
                task_id=task.task_id,
                request_payload={
                    "query": request.query,
                    "filters": request.filters.model_dump(mode="json"),
                    "task_context": effective_context,
                },
            )
        except Exception as exc:
            self._task_service.update_task(
                task.task_id,
                status="failed",
                current_node="failed",
                details={"error": str(exc), "execution_mode": "async"},
            )
            raise WorkflowExecutionError(f"Не удалось поставить retrieval задачу в async очередь: {exc}") from exc

        current = self._task_service.get_task(task.task_id)
        next_status = current.status if current.status != "queued" else "queued"
        next_node = current.current_node if current.status != "queued" else "queued"
        queue_name = getattr(dispatcher, "queue_name", current.details.get("queue_name", "inline"))
        self._task_service.update_task(
            task.task_id,
            status=next_status,
            current_node=next_node,
            details={
                **current.details,
                "dispatch_id": dispatch_id,
                "execution_mode": "async",
                "queue_name": queue_name,
                "queued_at": current.created_at.isoformat() if current.created_at else None,
                "knowledge_source": effective_context.get("knowledge_source", "case_dataset"),
            },
        )
        return StartTaskResponse(task_id=task.task_id, status="queued")

    def run_existing_task(self, *, task_id: str, request: StartRetrievalTaskRequest) -> StartTaskResponse:
        current = self._task_service.get_task(task_id)
        if current.task_type != "retrieval_pack":
            raise InvalidTaskStateError(
                f"Ожидался task_type=retrieval_pack для run_existing_task, получен {current.task_type}"
            )

        task_context = {**request.task_context, "task_id": task_id}
        knowledge_source = task_context.get("knowledge_source")

        self._task_service.update_task(
            task_id,
            status="running",
            current_node="start",
            details={
                **current.details,
                "execution_mode": current.details.get("execution_mode", "sync"),
                "knowledge_source": knowledge_source or current.details.get("knowledge_source", "case_dataset"),
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        case_dataset_id = task_context.get("case_dataset_id")
        case_dataset_path = task_context.get("case_dataset_path")
        case_dataset_dir = task_context.get("case_dataset_dir")
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

        if bool(task_context.get("force_interrupt", False)):
            self._task_service.save_checkpoint(task_id, initial_state.model_dump(mode="json"))
            self._task_service.update_task(
                task_id,
                status="interrupted",
                current_node="human_gate",
                details={
                    **current.details,
                    "reason": "forced_interrupt",
                    "resume_required": True,
                    "execution_mode": current.details.get("execution_mode", "sync"),
                    "knowledge_source": knowledge_source or current.details.get("knowledge_source", "case_dataset"),
                    "dispatch_id": current.details.get("dispatch_id"),
                },
            )
            return StartTaskResponse(task_id=task_id, status="interrupted")

        try:
            result_state = workflow.invoke(initial_state)
        except Exception as exc:
            self._task_service.fail_task(
                task_id=task_id,
                state_payload=initial_state.model_dump(mode="json"),
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

        details = {
            "confidence": result_state.confidence,
            "selected_summary_count": len(result_state.selected_summaries),
            "selected_block_count": len(result_state.selected_blocks),
            "reranked_count": len(result_state.reranked_blocks),
            "quality_gate_status": _quality_gate_status(result_state.unresolved_gaps),
            "unresolved_gaps": result_state.unresolved_gaps,
            "confidence_notes": (
                result_state.evidence_pack.confidence_notes if result_state.evidence_pack is not None else []
            ),
            "knowledge_source": knowledge_source or "case_dataset",
            "retrieval_backend": "pgvector" if knowledge_source == "canonical" and self._vector_store else "in_memory",
            "execution_mode": current.details.get("execution_mode", "sync"),
            "dispatch_id": current.details.get("dispatch_id"),
        }

        self._task_service.complete_task(
            task_id=task_id,
            state_payload=result_state.model_dump(mode="json"),
            details=details,
        )

        return StartTaskResponse(task_id=task_id, status="completed")

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
            daily=[
                TaskEventTimeBucketSummaryItem(
                    bucket_start=item.bucket_start,
                    total_events=item.total_events,
                    unique_tasks=item.unique_tasks,
                )
                for item in summary.daily
            ],
            weekly=[
                TaskEventTimeBucketSummaryItem(
                    bucket_start=item.bucket_start,
                    total_events=item.total_events,
                    unique_tasks=item.unique_tasks,
                )
                for item in summary.weekly
            ],
        )

    def observability_summary(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
    ) -> TaskObservabilityResponse:
        summary = self._task_service.summarize_tasks(
            status=status,
            task_type=task_type,
            updated_from=updated_from,
            updated_to=updated_to,
        )
        return TaskObservabilityResponse(
            total_tasks=summary.total_tasks,
            queued_tasks=summary.queued_tasks,
            running_tasks=summary.running_tasks,
            waiting_human_tasks=summary.waiting_human_tasks,
            completed_tasks=summary.completed_tasks,
            failed_tasks=summary.failed_tasks,
            async_tasks=summary.async_tasks,
            avg_duration_ms=summary.avg_duration_ms,
            p50_duration_ms=summary.p50_duration_ms,
            p95_duration_ms=summary.p95_duration_ms,
            max_duration_ms=summary.max_duration_ms,
            duration_sla_threshold_ms=summary.duration_sla_threshold_ms,
            duration_sla_breaches_total=summary.duration_sla_breaches_total,
            avg_queue_wait_ms=summary.avg_queue_wait_ms,
            p50_queue_wait_ms=summary.p50_queue_wait_ms,
            p95_queue_wait_ms=summary.p95_queue_wait_ms,
            queue_wait_sla_threshold_ms=summary.queue_wait_sla_threshold_ms,
            queue_wait_sla_breaches_total=summary.queue_wait_sla_breaches_total,
            avg_selected_block_count=summary.avg_selected_block_count,
            avg_confidence=summary.avg_confidence,
            tasks_with_unresolved_gaps=summary.tasks_with_unresolved_gaps,
            unresolved_gaps_total=summary.unresolved_gaps_total,
            llm_tokens_prompt_total=summary.llm_tokens_prompt_total,
            llm_tokens_completion_total=summary.llm_tokens_completion_total,
            llm_tokens_total=summary.llm_tokens_total,
            daily=[
                TaskObservabilityTimeBucketSummaryItem(
                    bucket_start=item.bucket_start,
                    total_tasks=item.total_tasks,
                    completed_tasks=item.completed_tasks,
                    failed_tasks=item.failed_tasks,
                    waiting_human_tasks=item.waiting_human_tasks,
                    duration_sla_breaches_total=item.duration_sla_breaches_total,
                    queue_wait_sla_breaches_total=item.queue_wait_sla_breaches_total,
                )
                for item in summary.daily
            ],
            weekly=[
                TaskObservabilityTimeBucketSummaryItem(
                    bucket_start=item.bucket_start,
                    total_tasks=item.total_tasks,
                    completed_tasks=item.completed_tasks,
                    failed_tasks=item.failed_tasks,
                    waiting_human_tasks=item.waiting_human_tasks,
                    duration_sla_breaches_total=item.duration_sla_breaches_total,
                    queue_wait_sla_breaches_total=item.queue_wait_sla_breaches_total,
                )
                for item in summary.weekly
            ],
            statuses=[TaskStatusSummaryItem(status=item.status, total=item.total) for item in summary.statuses],
            task_types=[
                TaskTypeObservabilitySummaryItem(
                    task_type=item.task_type,
                    total=item.total,
                    async_total=item.async_total,
                    completed_total=item.completed_total,
                    failed_total=item.failed_total,
                    avg_duration_ms=item.avg_duration_ms,
                    p50_duration_ms=item.p50_duration_ms,
                    p95_duration_ms=item.p95_duration_ms,
                    duration_sla_breaches_total=item.duration_sla_breaches_total,
                    avg_queue_wait_ms=item.avg_queue_wait_ms,
                    p50_queue_wait_ms=item.p50_queue_wait_ms,
                    p95_queue_wait_ms=item.p95_queue_wait_ms,
                    queue_wait_sla_breaches_total=item.queue_wait_sla_breaches_total,
                    avg_selected_block_count=item.avg_selected_block_count,
                    avg_confidence=item.avg_confidence,
                    unresolved_gaps_total=item.unresolved_gaps_total,
                    llm_tokens_prompt_total=item.llm_tokens_prompt_total,
                    llm_tokens_completion_total=item.llm_tokens_completion_total,
                    llm_tokens_total=item.llm_tokens_total,
                )
                for item in summary.task_types
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
                "quality_gate_status": _quality_gate_status(result.unresolved_gaps),
                "unresolved_gaps": result.unresolved_gaps,
                "confidence_notes": result.evidence_pack.confidence_notes if result.evidence_pack is not None else [],
                "resume_decision": request.decision,
                "knowledge_source": knowledge_source or "case_dataset",
                "retrieval_backend": "pgvector" if knowledge_source == "canonical" and self._vector_store else "in_memory",
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


def _quality_gate_status(unresolved_gaps: list[str]) -> str:
    if any(gap.startswith("low_evidence_count: selected 0") for gap in unresolved_gaps):
        return "failed"
    return "warning" if unresolved_gaps else "passed"
