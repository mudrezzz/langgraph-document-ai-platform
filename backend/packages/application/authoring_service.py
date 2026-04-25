from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from application.async_dispatcher import AuthoringAsyncDispatcher
from application.artifact_service import ArtifactApplicationService
from application.template_library_service import TemplateLibraryApplicationService, TemplateLibraryCatalogAdapter
from domain_authoring import (
    ArtifactExportResult,
    ArtifactExporter,
    DocumentAssemblyWorkflow,
    DocumentAssembler,
    OutlinePlanner,
    ResearchSummaryBuilder,
    SectionContractBuilder,
    SectionAuthoringService,
    SectionAuthoringWorkflow,
    SectionReviewService,
    WriterDraftService,
)
from application.errors import (
    InvalidTaskStateError,
    TaskArtifactLinkNotFoundError,
    WorkflowExecutionError,
)
from application.hitl_action_store import HitlActionRecord, HitlActionStore, InMemoryHitlActionStore
from application.retrieval_service import RetrievalApplicationService
from application.task_service import TaskApplicationService
from framework.models.interfaces import IChatModelGateway
from schemas.api.contracts import (
    HitlOutlineResponse,
    HitlOutlineSectionResponse,
    HitlReviewActionResponse,
    HitlActionsResponse,
    HitlReviewStatusResponse,
    SubmitHitlReviewRequest,
    StartAuthoringTaskRequest,
    StartRetrievalTaskRequest,
    StartTaskResponse,
    TaskArtifactResponse,
    TaskArtifactSectionTraceabilityResponse,
    TaskStatusResponse,
    TaskArtifactTraceabilityResponse,
)
from schemas.authoring.contracts import SectionArtifact, SectionContract
from schemas.documents.contracts import TemplateSpec
from schemas.rag.contracts import EvidencePack, SourceRef
from schemas.workflow.states import AssemblyWorkflowState, AuthoringTaskState, SectionAuthoringState


class TaskArtifactLinkRecord(BaseModel):
    """Связь authoring task с итоговым артефактом."""

    task_id: str
    artifact_id: str
    retrieval_task_id: str
    traceability: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskArtifactRegistry(Protocol):
    """Контракт хранения связи task -> artifact."""

    def save_link(
        self,
        *,
        task_id: str,
        artifact_id: str,
        retrieval_task_id: str,
        traceability: dict,
    ) -> None:
        """Сохраняет связь authoring task и артефакта."""

    def get_link(self, task_id: str) -> TaskArtifactLinkRecord:
        """Возвращает связь authoring task и артефакта."""


class DraftGenerationResult(BaseModel):
    """Результат writer-генерации authoring draft."""

    content: str
    mode: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringStepResult(BaseModel):
    """Результат выполнения шага multi-step authoring."""

    step: str
    status: str
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringApplicationService:
    """Application service authoring: retrieval -> research -> writer -> reviewer -> assembly."""

    def __init__(
        self,
        *,
        task_service: TaskApplicationService,
        retrieval_service: RetrievalApplicationService,
        artifact_service: ArtifactApplicationService,
        task_artifact_registry: TaskArtifactRegistry,
        hitl_action_store: HitlActionStore | None = None,
        chat_model_gateway: IChatModelGateway | None = None,
        llm_enabled: bool = False,
        llm_strict_mode: bool = False,
        llm_provider: str = "deterministic",
        llm_model_name: str | None = None,
        hitl_max_iterations: int = 2,
        hitl_wait_timeout_sec: int = 1800,
        outline_planner: OutlinePlanner | None = None,
        section_review_service: SectionReviewService | None = None,
        document_assembler: DocumentAssembler | None = None,
        artifact_exporter: ArtifactExporter | None = None,
        document_assembly_workflow: DocumentAssemblyWorkflow | None = None,
        research_summary_builder: ResearchSummaryBuilder | None = None,
        writer_draft_service: WriterDraftService | None = None,
        section_contract_builder: SectionContractBuilder | None = None,
        template_library_service: TemplateLibraryApplicationService | None = None,
        section_authoring_service: SectionAuthoringService | None = None,
        section_authoring_workflow: SectionAuthoringWorkflow | None = None,
    ) -> None:
        self._task_service = task_service
        self._retrieval_service = retrieval_service
        self._artifact_service = artifact_service
        self._task_artifact_registry = task_artifact_registry
        self._hitl_action_store = hitl_action_store or InMemoryHitlActionStore()
        self._chat_model_gateway = chat_model_gateway
        self._llm_enabled = llm_enabled
        self._llm_strict_mode = llm_strict_mode
        self._llm_provider = llm_provider
        self._llm_model_name = llm_model_name
        self._hitl_max_iterations = max(1, hitl_max_iterations)
        self._hitl_wait_timeout_sec = max(60, hitl_wait_timeout_sec)
        self._outline_planner = outline_planner or OutlinePlanner()
        self._section_review_service = section_review_service or SectionReviewService()
        self._document_assembler = document_assembler or DocumentAssembler()
        self._artifact_exporter = artifact_exporter or ArtifactExporter()
        self._document_assembly_workflow = document_assembly_workflow or DocumentAssemblyWorkflow(
            document_assembler=self._document_assembler,
            artifact_exporter=self._artifact_exporter,
        )
        self._research_summary_builder = research_summary_builder or ResearchSummaryBuilder()
        self._writer_draft_service = writer_draft_service or WriterDraftService()
        self._template_library_service = template_library_service
        self._section_contract_builder = section_contract_builder or SectionContractBuilder(
            template_catalog=TemplateLibraryCatalogAdapter(template_library_service)
            if template_library_service is not None
            else None,
        )
        self._section_authoring_service = section_authoring_service or SectionAuthoringService()
        self._section_authoring_workflow = section_authoring_workflow or SectionAuthoringWorkflow(
            section_authoring_service=self._section_authoring_service,
            section_review_service=self._section_review_service,
        )

    def start(self, request: StartAuthoringTaskRequest) -> StartTaskResponse:
        task = self._task_service.create_task(task_type="authoring_pack")
        return self.run_existing_task(task_id=task.task_id, request=request)

    def start_async(
        self,
        request: StartAuthoringTaskRequest,
        *,
        dispatcher: AuthoringAsyncDispatcher,
    ) -> StartTaskResponse:
        task = self._task_service.create_task(
            task_type="authoring_pack",
            initial_status="queued",
            initial_node="queued",
            details={
                "execution_mode": "async",
                "workflow_mode": request.workflow_mode,
                "hitl_required": request.hitl_required,
            },
        )

        try:
            dispatch_id = dispatcher.enqueue_authoring_start(
                task_id=task.task_id,
                request_payload=request.model_dump(mode="json"),
            )
        except Exception as exc:
            self._task_service.update_task(
                task.task_id,
                status="failed",
                current_node="failed",
                details={"error": str(exc), "execution_mode": "async"},
            )
            raise WorkflowExecutionError(f"Не удалось поставить задачу в async очередь: {exc}") from exc

        current = self._task_service.get_task(task.task_id)
        next_status = current.status
        next_node = current.current_node
        if current.status == "queued":
            next_status = "queued"
            next_node = "queued"

        self._task_service.update_task(
            task.task_id,
            status=next_status,
            current_node=next_node,
            details={
                **current.details,
                "dispatch_id": dispatch_id,
                "workflow_mode": request.workflow_mode,
                "hitl_required": request.hitl_required,
            },
        )
        return StartTaskResponse(task_id=task.task_id, status="queued")

    def run_existing_task(self, *, task_id: str, request: StartAuthoringTaskRequest) -> StartTaskResponse:
        current = self._task_service.get_task(task_id)
        if current.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"Ожидался task_type=authoring_pack для run_existing_task, получен {current.task_type}"
            )

        self._task_service.update_task(
            task_id,
            status="running",
            current_node="start",
            details={
                **current.details,
                "workflow_mode": request.workflow_mode,
                "hitl_required": request.hitl_required,
            },
        )
        return self._run_authoring_pipeline(task_id=task_id, request=request)

    def _run_authoring_pipeline(self, *, task_id: str, request: StartAuthoringTaskRequest) -> StartTaskResponse:
        task_context = {**request.task_context, "task_id": task_id}
        initial_state = AuthoringTaskState(
            task_context=task_context,
            query=request.query,
            filters=request.filters,
            artifact_type=request.artifact_type,
            artifact_title=request.artifact_title,
            artifact_format=request.artifact_format,
            draft_strategy=request.draft_strategy,
            workflow_mode=request.workflow_mode,
            hitl_required=request.hitl_required,
            current_step="retrieval",
        )

        try:
            retrieval_request = StartRetrievalTaskRequest(
                query=request.query,
                filters=request.filters,
                task_context={**task_context, "parent_task_id": task_id},
            )
            retrieval_started = self._retrieval_service.start(retrieval_request)
            retrieval_task_id = retrieval_started.task_id
            evidence_pack = self._retrieval_service.evidence(retrieval_task_id).evidence_pack

            steps: list[AuthoringStepResult] = []

            research_summary = self._build_research_summary(query=request.query, evidence_pack=evidence_pack)
            steps.append(
                AuthoringStepResult(
                    step="research",
                    status="completed",
                    notes="Собран исследовательский summary по evidence.",
                    metadata={"summary_length": len(research_summary)},
                )
            )

            draft_result = self._generate_draft(
                query=request.query,
                evidence_pack=evidence_pack,
                draft_strategy=request.draft_strategy,
                research_summary=research_summary,
            )
            steps.append(
                AuthoringStepResult(
                    step="writer",
                    status="completed",
                    notes="Сформирован writer draft.",
                    metadata={"generation_mode": draft_result.mode},
                )
            )

            review_result = self._review_draft(
                query=request.query,
                draft=draft_result.content,
                evidence_pack=evidence_pack,
                workflow_mode=request.workflow_mode,
            )
            steps.append(
                AuthoringStepResult(
                    step="reviewer",
                    status=review_result["status"],
                    notes=review_result["notes"],
                    metadata={
                        "recommendation": review_result["recommendation"],
                        "issues_count": len(review_result.get("issues", [])),
                    },
                )
            )

            template_spec, section_contracts = self._build_section_contracts(
                task_context=task_context,
                evidence_pack=evidence_pack,
                review_result=review_result,
            )
            section_traceability = self._build_section_traceability(
                evidence_pack=evidence_pack,
                review_result=review_result,
                template_spec=template_spec,
                section_contracts=section_contracts,
            )
            if request.hitl_required and request.workflow_mode == "multi_step":
                outline_snapshot = self._build_outline_snapshot(
                    template_spec=template_spec,
                    section_contracts=section_contracts,
                    section_traceability=section_traceability,
                )
                waiting_traceability = self._build_traceability(
                    retrieval_task_id=retrieval_task_id,
                    evidence_pack=evidence_pack,
                    section_traceability=section_traceability,
                    workflow_steps=steps,
                )
                waiting_state = initial_state.model_copy(
                    update={
                        "retrieval_task_id": retrieval_task_id,
                        "research_summary": research_summary,
                        "draft": draft_result.content,
                        "review_result": review_result,
                        "template_spec": template_spec.model_dump(mode="json"),
                        "section_contracts": section_contracts,
                        "section_artifacts": [],
                        "section_traceability": section_traceability,
                        "steps_summary": [step.model_dump(mode="json") for step in steps],
                        "traceability": waiting_traceability,
                        "draft_generation_mode": draft_result.mode,
                        "draft_generation_metadata": draft_result.metadata,
                        "hitl_status": "pending",
                        "hitl_iteration": 1,
                        "hitl_max_iterations": self._hitl_max_iterations,
                        "hitl_phase": "outline_review",
                        "task_context": {
                            **initial_state.task_context,
                            "template_id": template_spec.template_id,
                            "template_spec": template_spec.model_dump(mode="json"),
                            "outline_snapshot": outline_snapshot,
                        },
                    }
                )
                self._move_to_waiting_human(
                    task_id=task_id,
                    state=waiting_state,
                    pending_action_id=None,
                    pending_reason="Требуется ручное outline approval перед section authoring.",
                )
                return StartTaskResponse(task_id=task_id, status="waiting_human")

            section_artifacts = self._build_section_artifacts(
                section_contracts=section_contracts,
                query=request.query,
                task_context=task_context,
                evidence_pack=evidence_pack,
                research_summary=research_summary,
                review_result=review_result,
            )

            return self._finalize_task(
                task_id=task_id,
                request=request,
                retrieval_task_id=retrieval_task_id,
                research_summary=research_summary,
                writer_draft=draft_result.content,
                review_result=review_result,
                template_spec=template_spec,
                section_contracts=section_contracts,
                section_artifacts=section_artifacts,
                section_traceability=section_traceability,
                steps=steps,
                draft_result=draft_result,
                initial_state=initial_state,
            )
        except Exception as exc:
            failed_state = initial_state.model_copy(update={"error_message": str(exc), "current_step": "failed"})
            self._task_service.fail_task(
                task_id=task_id,
                state_payload=failed_state.model_dump(mode="json"),
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

    def hitl_status(self, task_id: str) -> HitlReviewStatusResponse:
        task = self._task_service.get_task(task_id)
        if task.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"HITL доступен только для задач authoring_pack, получен task_type={task.task_type}"
            )

        state_payload = self._task_service.get_state_payload(task_id)
        state = AuthoringTaskState.model_validate(state_payload)
        actions_page = self._hitl_action_store.list_actions(task_id=task_id, limit=100)
        actions = [self._to_hitl_action_response(item) for item in actions_page.items]

        deadline_at = self._parse_datetime(state.hitl_deadline_at)
        can_submit = (
            task.status == "waiting_human"
            and state.hitl_required
            and (deadline_at is None or datetime.now(timezone.utc) <= deadline_at)
        )
        return HitlReviewStatusResponse(
            task_id=task_id,
            status=task.status,
            required=bool(state.hitl_required),
            current_iteration=max(1, state.hitl_iteration),
            max_iterations=max(1, state.hitl_max_iterations),
            deadline_at=deadline_at,
            can_submit=can_submit,
            pending_action_id=state.hitl_pending_action_id,
            pending_reason=task.details.get("pending_reason"),
            reviewer_notes=str(state.review_result.get("notes", "")) or None,
            phase=state.hitl_phase,
            outline=self._build_hitl_outline_response(state),
            actions=actions,
        )

    def list_hitl_actions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> HitlActionsResponse:
        """Возвращает read-model истории HITL действий с фильтрами."""

        page = self._hitl_action_store.list_actions(
            limit=limit,
            cursor=cursor,
            task_id=task_id,
            decision=decision,
            status=status,
            reviewer=reviewer,
            created_from=created_from,
            created_to=created_to,
        )
        return HitlActionsResponse(
            items=[self._to_hitl_action_response(item) for item in page.items],
            limit=page.limit,
            total_returned=page.total_returned,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    def submit_hitl(
        self,
        task_id: str,
        request: SubmitHitlReviewRequest,
        *,
        dispatcher: AuthoringAsyncDispatcher,
    ) -> TaskStatusResponse:
        task = self._task_service.get_task(task_id)
        if task.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"HITL доступен только для задач authoring_pack, получен task_type={task.task_type}"
            )
        if task.status != "waiting_human":
            raise InvalidTaskStateError(
                f"HITL submit допустим только для waiting_human, текущий статус={task.status}"
            )

        state_payload = self._task_service.get_state_payload(task_id)
        state = AuthoringTaskState.model_validate(state_payload)
        if not state.retrieval_task_id:
            raise InvalidTaskStateError("Для HITL submit отсутствует retrieval_task_id в state")

        deadline_at = self._parse_datetime(state.hitl_deadline_at)
        if deadline_at is not None and datetime.now(timezone.utc) > deadline_at:
            raise InvalidTaskStateError("Окно HITL submit истекло, требуется повторный запуск authoring.")

        current_iteration = max(1, state.hitl_iteration)
        max_iterations = max(1, state.hitl_max_iterations)
        idempotency_key = (request.idempotency_key or "").strip() or None
        if idempotency_key:
            existed = self._find_hitl_action_by_idempotency_key(state.hitl_actions, idempotency_key)
            if existed is not None:
                current = self._task_service.get_task(task_id)
                return TaskStatusResponse(
                    task_id=current.task_id,
                    status=current.status,
                    current_node=current.current_node,
                    details=current.details,
                )

        if request.expected_iteration is not None and request.expected_iteration != current_iteration:
            raise InvalidTaskStateError(
                f"Ожидалась HITL-итерация={current_iteration}, получено expected_iteration={request.expected_iteration}"
            )
        if request.decision == "needs_changes" and current_iteration >= max_iterations:
            raise InvalidTaskStateError(
                "Достигнут лимит HITL итераций: для завершения используйте approve/reject."
            )

        action_id = str(uuid4())
        action = {
            "action_id": action_id,
            "iteration": current_iteration,
            "decision": request.decision,
            "comment": request.comment,
            "metadata": request.metadata,
            "idempotency_key": idempotency_key,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        queued_state = state.model_copy(
            update={
                "hitl_status": "processing",
                "hitl_pending_action_id": action_id,
                "hitl_actions": [*state.hitl_actions, action],
            }
        )
        self._persist_hitl_action(task_id=task_id, action=action)
        self._task_service.save_checkpoint(task_id, queued_state.model_dump(mode="json"))
        self._task_service.update_task(
            task_id,
            status="queued",
            current_node="hitl_dispatch",
            details={
                **task.details,
                "current_step": "hitl_dispatch",
                "pending_reason": "HITL решение принято, ожидается async continuation.",
                "hitl_iteration": current_iteration,
                "hitl_max_iterations": max_iterations,
                "hitl_pending_action_id": action_id,
                "hitl_decision_requested": request.decision,
            },
        )

        try:
            dispatch_id = dispatcher.enqueue_hitl_action(
                task_id=task_id,
                action_payload={
                    "action_id": action_id,
                    "request": request.model_dump(mode="json"),
                },
            )
        except Exception as exc:
            failed_actions = self._update_hitl_action(
                queued_state.hitl_actions,
                action_id=action_id,
                updates={"status": "dispatch_failed", "error": str(exc)},
            )
            failed_action = self._find_hitl_action_by_id(failed_actions, action_id)
            if failed_action is not None:
                self._persist_hitl_action(task_id=task_id, action=failed_action)
            rollback_state = queued_state.model_copy(
                update={
                    "hitl_status": "pending",
                    "hitl_pending_action_id": None,
                    "hitl_actions": failed_actions,
                }
            )
            self._move_to_waiting_human(
                task_id=task_id,
                state=rollback_state,
                pending_action_id=None,
                pending_reason="Ошибка постановки HITL continuation в очередь. Повторите submit.",
            )
            raise WorkflowExecutionError(f"Не удалось поставить HITL continuation в очередь: {exc}") from exc

        current = self._task_service.get_task(task_id)
        if current.status == "queued":
            updated = self._task_service.update_task(
                task_id,
                details={**current.details, "hitl_dispatch_id": dispatch_id},
            )
            return TaskStatusResponse(
                task_id=updated.task_id,
                status=updated.status,
                current_node=updated.current_node,
                details=updated.details,
            )

        current = self._task_service.get_task(task_id)
        return TaskStatusResponse(
            task_id=current.task_id,
            status=current.status,
            current_node=current.current_node,
            details=current.details,
        )

    def process_hitl_action(
        self,
        *,
        task_id: str,
        request: SubmitHitlReviewRequest,
        action_id: str,
    ) -> TaskStatusResponse:
        task = self._task_service.get_task(task_id)
        if task.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"HITL continuation доступен только для задач authoring_pack, получен task_type={task.task_type}"
            )
        if not action_id:
            raise InvalidTaskStateError("HITL continuation требует action_id.")

        state_payload = self._task_service.get_state_payload(task_id)
        state = AuthoringTaskState.model_validate(state_payload)
        if not state.retrieval_task_id:
            raise InvalidTaskStateError("Для HITL continuation отсутствует retrieval_task_id в state")

        action = self._find_hitl_action_by_id(state.hitl_actions, action_id)
        if action is None:
            current = self._task_service.get_task(task_id)
            return TaskStatusResponse(
                task_id=current.task_id,
                status=current.status,
                current_node=current.current_node,
                details=current.details,
            )
        if action.get("status") in {"completed", "dispatch_failed", "skipped"}:
            current = self._task_service.get_task(task_id)
            return TaskStatusResponse(
                task_id=current.task_id,
                status=current.status,
                current_node=current.current_node,
                details=current.details,
            )

        processing_actions = self._update_hitl_action(
            state.hitl_actions,
            action_id=action_id,
            updates={"status": "processing", "started_at": datetime.now(timezone.utc).isoformat()},
        )
        processing_action = self._find_hitl_action_by_id(processing_actions, action_id)
        if processing_action is not None:
            self._persist_hitl_action(task_id=task_id, action=processing_action)
        processing_state = state.model_copy(
            update={
                "hitl_status": "processing",
                "hitl_pending_action_id": action_id,
                "hitl_actions": processing_actions,
            }
        )
        self._task_service.save_checkpoint(task_id, processing_state.model_dump(mode="json"))
        current_before = self._task_service.get_task(task_id)
        if current_before.status in {"queued", "waiting_human"}:
            self._task_service.update_task(
                task_id,
                status="running",
                current_node="hitl_processing",
                details={
                    **current_before.details,
                    "current_step": "hitl_processing",
                    "pending_reason": "Обработка HITL решения в async worker.",
                    "hitl_pending_action_id": action_id,
                },
            )

        if request.decision == "reject":
            failed_actions = self._update_hitl_action(
                processing_state.hitl_actions,
                action_id=action_id,
                updates={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
            )
            failed_action = self._find_hitl_action_by_id(failed_actions, action_id)
            if failed_action is not None:
                self._persist_hitl_action(task_id=task_id, action=failed_action)
            failed_state = processing_state.model_copy(
                update={
                    "hitl_status": "rejected",
                    "hitl_pending_action_id": None,
                    "hitl_actions": failed_actions,
                }
            )
            self._task_service.fail_task(
                task_id=task_id,
                state_payload=failed_state.model_dump(mode="json"),
                error_message=request.comment or "Ручной reviewer отклонил задачу",
            )
            failed = self._task_service.get_task(task_id)
            return TaskStatusResponse(
                task_id=failed.task_id,
                status=failed.status,
                current_node=failed.current_node,
                details=failed.details,
            )

        steps = [AuthoringStepResult.model_validate(item) for item in processing_state.steps_summary]
        updated_draft = processing_state.draft or ""
        updated_review_result = dict(processing_state.review_result)
        template_spec = TemplateSpec.model_validate(processing_state.task_context.get("template_spec") or {
            "template_id": processing_state.task_context.get("template_id") or "release_readiness",
            "version": "1",
            "sections": [],
            "validation_rules": [],
        })
        section_contracts = [SectionContract.model_validate(item) for item in processing_state.section_contracts]
        section_artifacts = [SectionArtifact.model_validate(item) for item in processing_state.section_artifacts]
        section_traceability = list(processing_state.section_traceability)

        if processing_state.hitl_phase == "outline_review":
            if request.decision == "needs_changes":
                completed_actions = self._update_hitl_action(
                    processing_state.hitl_actions,
                    action_id=action_id,
                    updates={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
                )
                completed_action = self._find_hitl_action_by_id(completed_actions, action_id)
                if completed_action is not None:
                    self._persist_hitl_action(task_id=task_id, action=completed_action)
                waiting_state = processing_state.model_copy(
                    update={
                        "hitl_status": "pending",
                        "hitl_iteration": processing_state.hitl_iteration + 1,
                        "hitl_pending_action_id": None,
                        "hitl_actions": completed_actions,
                    }
                )
                self._move_to_waiting_human(
                    task_id=task_id,
                    state=waiting_state,
                    pending_action_id=None,
                    pending_reason=request.comment or "Outline требует доработки evidence/template inputs перед authoring.",
                )
                waiting_task = self._task_service.get_task(task_id)
                return TaskStatusResponse(
                    task_id=waiting_task.task_id,
                    status=waiting_task.status,
                    current_node=waiting_task.current_node,
                    details=waiting_task.details,
                )

            evidence_pack = self._retrieval_service.evidence(processing_state.retrieval_task_id).evidence_pack
            section_artifacts = self._build_section_artifacts(
                section_contracts=section_contracts,
                query=processing_state.query,
                task_context=processing_state.task_context,
                evidence_pack=evidence_pack,
                research_summary=processing_state.research_summary or "",
                review_result=updated_review_result,
            )
            processing_state = processing_state.model_copy(
                update={
                    "section_artifacts": section_artifacts,
                    "hitl_phase": "final_review",
                }
            )

        if request.decision == "needs_changes":
            updated_draft = self._apply_human_feedback_to_draft(
                draft=updated_draft,
                comment=request.comment or "",
                metadata=request.metadata,
            )
            steps.append(
                AuthoringStepResult(
                    step="rewrite",
                    status="completed",
                    notes="Черновик обновлен после ручного feedback.",
                    metadata={
                        "decision": request.decision,
                        "iteration": processing_state.hitl_iteration,
                    },
                )
            )
            evidence_pack = self._retrieval_service.evidence(processing_state.retrieval_task_id).evidence_pack
            updated_review_result = self._review_draft(
                query=processing_state.query,
                draft=updated_draft,
                evidence_pack=evidence_pack,
                workflow_mode=processing_state.workflow_mode,
            )
            steps.append(
                AuthoringStepResult(
                    step="reviewer_rerun",
                    status=updated_review_result["status"],
                    notes=updated_review_result["notes"],
                    metadata={
                        "recommendation": updated_review_result["recommendation"],
                        "issues_count": len(updated_review_result.get("issues", [])),
                        "iteration": processing_state.hitl_iteration,
                    },
                )
            )
            template_spec, section_contracts = self._build_section_contracts(
                task_context=processing_state.task_context,
                evidence_pack=evidence_pack,
                review_result=updated_review_result,
            )
            section_traceability = self._build_section_traceability(
                evidence_pack=evidence_pack,
                review_result=updated_review_result,
                template_spec=template_spec,
                section_contracts=section_contracts,
            )
            section_artifacts = self._build_section_artifacts(
                section_contracts=section_contracts,
                query=processing_state.query,
                task_context=processing_state.task_context,
                evidence_pack=evidence_pack,
                research_summary=processing_state.research_summary or "",
                review_result=updated_review_result,
            )

            completed_actions = self._update_hitl_action(
                processing_state.hitl_actions,
                action_id=action_id,
                updates={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
            )
            completed_action = self._find_hitl_action_by_id(completed_actions, action_id)
            if completed_action is not None:
                self._persist_hitl_action(task_id=task_id, action=completed_action)
            waiting_state = processing_state.model_copy(
                update={
                    "draft": updated_draft,
                    "review_result": updated_review_result,
                    "template_spec": template_spec.model_dump(mode="json"),
                    "section_contracts": section_contracts,
                    "section_artifacts": section_artifacts,
                    "section_traceability": section_traceability,
                    "steps_summary": [step.model_dump(mode="json") for step in steps],
                    "hitl_status": "pending",
                    "hitl_iteration": processing_state.hitl_iteration + 1,
                    "hitl_pending_action_id": None,
                    "hitl_actions": completed_actions,
                }
            )
            self._move_to_waiting_human(
                task_id=task_id,
                state=waiting_state,
                pending_action_id=None,
            )
            waiting_task = self._task_service.get_task(task_id)
            return TaskStatusResponse(
                task_id=waiting_task.task_id,
                status=waiting_task.status,
                current_node=waiting_task.current_node,
                details=waiting_task.details,
            )

        updated_review_result["status"] = "completed"
        updated_review_result["notes"] = request.comment or "Reviewer утвердил итог."
        section_traceability = self._set_section_review_status(
            sections=section_traceability,
            review_status="approved",
        )
        steps.append(
            AuthoringStepResult(
                step="assembly",
                status="completed",
                notes="Собран финальный артефакт после HITL решения.",
                metadata={"decision": request.decision, "iteration": processing_state.hitl_iteration},
            )
        )
        assembly_result = self._run_document_assembly_workflow(
            query=processing_state.query,
            artifact_type=processing_state.artifact_type,
            artifact_title=processing_state.artifact_title,
            artifact_format=processing_state.artifact_format,
            workflow_mode=processing_state.workflow_mode,
            task_context=processing_state.task_context,
            research_summary=processing_state.research_summary or "",
            writer_draft=updated_draft,
            review_result=updated_review_result,
            template_spec=template_spec,
            section_artifacts=section_artifacts,
            section_traceability=section_traceability,
        )
        export_result = assembly_result["export_result"]
        final_content = assembly_result["final_content"]
        completed_actions = self._update_hitl_action(
            processing_state.hitl_actions,
            action_id=action_id,
            updates={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
        )
        completed_action = self._find_hitl_action_by_id(completed_actions, action_id)
        if completed_action is not None:
            self._persist_hitl_action(task_id=task_id, action=completed_action)
        return self._finalize_from_hitl(
            task_id=task_id,
            state=processing_state,
            final_content=final_content,
            export_result=export_result,
            updated_draft=updated_draft,
            review_result=updated_review_result,
            template_spec=template_spec,
            section_contracts=section_contracts,
            section_artifacts=section_artifacts,
            section_traceability=section_traceability,
            steps=steps,
            hitl_actions=completed_actions,
            decision=request.decision,
        )

    def artifact(self, task_id: str) -> TaskArtifactResponse:
        task = self._task_service.get_task(task_id)
        if task.task_type != "authoring_pack":
            raise InvalidTaskStateError(
                f"Артефакт доступен только для задач authoring_pack, получен task_type={task.task_type}"
            )

        try:
            link = self._task_artifact_registry.get_link(task_id)
        except TaskArtifactLinkNotFoundError:
            raise

        artifact = self._artifact_service.get_artifact(link.artifact_id)
        payload = artifact.payload

        source_refs = self._to_source_refs(link.traceability.get("source_refs", []))
        sections_payload = link.traceability.get("sections", [])
        sections: list[TaskArtifactSectionTraceabilityResponse] = []
        for section in sections_payload:
            sections.append(
                TaskArtifactSectionTraceabilityResponse(
                    section_id=str(section.get("section_id", "")),
                    title=str(section.get("title", "")),
                    review_status=str(section.get("review_status", "not_reviewed")),
                    source_refs=self._to_source_refs(section.get("source_refs", [])),
                )
            )

        return TaskArtifactResponse(
            task_id=task_id,
            artifact_id=artifact.artifact_id,
            artifact_type=artifact.artifact_type,
            title=payload.get("title"),
            content=str(payload.get("content", "")),
            format=str(payload.get("format", "markdown")),
            metadata=dict(payload.get("metadata") or {}),
            traceability=TaskArtifactTraceabilityResponse(
                retrieval_task_id=link.retrieval_task_id,
                source_refs=source_refs,
                sections=sections,
            ),
        )

    def _finalize_task(
        self,
        *,
        task_id: str,
        request: StartAuthoringTaskRequest,
        retrieval_task_id: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_contracts: list[SectionContract],
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
        steps: list[AuthoringStepResult],
        draft_result: DraftGenerationResult,
        initial_state: AuthoringTaskState,
    ) -> StartTaskResponse:
        assembly_result = self._run_document_assembly_workflow(
            query=request.query,
            artifact_type=request.artifact_type,
            artifact_title=request.artifact_title,
            artifact_format=request.artifact_format,
            workflow_mode=request.workflow_mode,
            task_context=initial_state.task_context,
            research_summary=research_summary,
            writer_draft=writer_draft,
            review_result=review_result,
            template_spec=template_spec,
            section_artifacts=section_artifacts,
            section_traceability=section_traceability,
        )
        export_result = assembly_result["export_result"]
        final_content = assembly_result["final_content"]
        steps.append(
            AuthoringStepResult(
                step="assembly",
                status="completed",
                notes="Собран финальный артефакт.",
                metadata={"section_count": len(section_traceability)},
            )
        )

        artifact_title = request.artifact_title or "Release Readiness Draft"
        artifact_metadata = {
            "authoring_task_id": task_id,
            "retrieval_task_id": retrieval_task_id,
            "source_count": len(self._dedup_source_dicts(self._to_source_refs_from_evidence(section_traceability))),
            "draft_generation_mode": draft_result.mode,
            "draft_generation_requested_strategy": request.draft_strategy,
            "workflow_mode": request.workflow_mode,
            "template_spec": template_spec.model_dump(mode="json"),
            "section_contracts": [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in section_contracts],
            "section_artifacts": [item.model_dump(mode="json") for item in section_artifacts],
            "review_status": review_result.get("status"),
            "final_recommendation": review_result.get("recommendation"),
            "steps_summary": [step.model_dump(mode="json") for step in steps],
            **export_result.metadata,
        }
        if draft_result.metadata.get("provider"):
            artifact_metadata["draft_model_provider"] = draft_result.metadata["provider"]
        if draft_result.metadata.get("model_name"):
            artifact_metadata["draft_model_name"] = draft_result.metadata["model_name"]
        if draft_result.metadata.get("fallback_reason"):
            artifact_metadata["draft_fallback_reason"] = draft_result.metadata["fallback_reason"]

        artifact = self._artifact_service.write_artifact(
            artifact_type=request.artifact_type,
            payload={
                "title": artifact_title,
                "content": final_content,
                "format": export_result.format,
                "metadata": artifact_metadata,
            },
        )

        traceability = {
            "retrieval_task_id": retrieval_task_id,
            "source_refs": self._dedup_source_dicts(self._to_source_refs_from_evidence(section_traceability)),
            "sections": section_traceability,
            "workflow_steps": [step.model_dump(mode="json") for step in steps],
        }
        self._task_artifact_registry.save_link(
            task_id=task_id,
            artifact_id=artifact.artifact_id,
            retrieval_task_id=retrieval_task_id,
            traceability=traceability,
        )

        completed_state = initial_state.model_copy(
            update={
                "current_step": "completed",
                "retrieval_task_id": retrieval_task_id,
                "artifact_id": artifact.artifact_id,
                "research_summary": research_summary,
                "draft": writer_draft,
                "review_result": review_result,
                "task_context": {
                    **initial_state.task_context,
                    "template_id": template_spec.template_id,
                    "template_spec": template_spec.model_dump(mode="json"),
                },
                "section_contracts": section_contracts,
                "section_artifacts": section_artifacts,
                "section_traceability": section_traceability,
                "steps_summary": [step.model_dump(mode="json") for step in steps],
                "traceability": traceability,
                "draft_generation_mode": draft_result.mode,
                "draft_generation_metadata": draft_result.metadata,
                "hitl_status": "not_required" if not request.hitl_required else "resolved",
            }
        )
        self._task_service.complete_task(
            task_id=task_id,
            state_payload=completed_state.model_dump(mode="json"),
            details={
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "retrieval_task_id": retrieval_task_id,
                "current_step": "completed",
                "workflow_mode": request.workflow_mode,
                "hitl_required": request.hitl_required,
                "traceability_sources": len(traceability.get("source_refs", [])),
                "traceability_sections": len(traceability.get("sections", [])),
                "draft_generation_mode": draft_result.mode,
                "review_status": review_result.get("status"),
                "final_recommendation": review_result.get("recommendation"),
                "steps_summary": [step.model_dump(mode="json") for step in steps],
            },
        )
        return StartTaskResponse(task_id=task_id, status="completed")

    def _finalize_from_hitl(
        self,
        *,
        task_id: str,
        state: AuthoringTaskState,
        final_content: str,
        export_result,
        updated_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_contracts: list[SectionContract],
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
        steps: list[AuthoringStepResult],
        hitl_actions: list[dict[str, Any]],
        decision: str,
    ) -> TaskStatusResponse:
        artifact_title = state.artifact_title or "Release Readiness Draft"
        artifact_metadata = {
            "authoring_task_id": task_id,
            "retrieval_task_id": state.retrieval_task_id,
            "draft_generation_mode": state.draft_generation_mode,
            "workflow_mode": state.workflow_mode,
            "hitl_iteration": state.hitl_iteration,
            "hitl_max_iterations": state.hitl_max_iterations,
            "template_spec": template_spec.model_dump(mode="json"),
            "section_contracts": [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in section_contracts],
            "section_artifacts": [item.model_dump(mode="json") for item in section_artifacts],
            "review_status": review_result.get("status"),
            "final_recommendation": review_result.get("recommendation"),
            "hitl_decision": decision,
            "steps_summary": [step.model_dump(mode="json") for step in steps],
            **export_result.metadata,
        }
        if state.draft_generation_metadata.get("provider"):
            artifact_metadata["draft_model_provider"] = state.draft_generation_metadata.get("provider")
        if state.draft_generation_metadata.get("model_name"):
            artifact_metadata["draft_model_name"] = state.draft_generation_metadata.get("model_name")

        artifact = self._artifact_service.write_artifact(
            artifact_type=state.artifact_type,
            payload={
                "title": artifact_title,
                "content": final_content,
                "format": export_result.format,
                "metadata": artifact_metadata,
            },
        )

        traceability = {
            "retrieval_task_id": state.retrieval_task_id,
            "source_refs": state.traceability.get("source_refs", []),
            "sections": section_traceability,
            "workflow_steps": [step.model_dump(mode="json") for step in steps],
        }
        self._task_artifact_registry.save_link(
            task_id=task_id,
            artifact_id=artifact.artifact_id,
            retrieval_task_id=state.retrieval_task_id or "",
            traceability=traceability,
        )

        completed_state = state.model_copy(
            update={
                "current_step": "completed",
                "artifact_id": artifact.artifact_id,
                "draft": updated_draft,
                "review_result": review_result,
                "task_context": {
                    **state.task_context,
                    "template_id": template_spec.template_id,
                    "template_spec": template_spec.model_dump(mode="json"),
                },
                "section_contracts": section_contracts,
                "section_artifacts": section_artifacts,
                "section_traceability": section_traceability,
                "steps_summary": [step.model_dump(mode="json") for step in steps],
                "traceability": traceability,
                "hitl_status": "resolved",
                "hitl_pending_action_id": None,
                "hitl_actions": hitl_actions,
            }
        )
        self._task_service.complete_task(
            task_id=task_id,
            state_payload=completed_state.model_dump(mode="json"),
            details={
                "artifact_id": artifact.artifact_id,
                "artifact_type": state.artifact_type,
                "retrieval_task_id": state.retrieval_task_id,
                "current_step": "completed",
                "workflow_mode": state.workflow_mode,
                "hitl_required": True,
                "hitl_decision": decision,
                "hitl_iteration": state.hitl_iteration,
                "hitl_max_iterations": state.hitl_max_iterations,
                "review_status": review_result.get("status"),
                "final_recommendation": review_result.get("recommendation"),
                "traceability_sources": len(traceability.get("source_refs", [])),
                "traceability_sections": len(traceability.get("sections", [])),
                "steps_summary": [step.model_dump(mode="json") for step in steps],
            },
        )
        task = self._task_service.get_task(task_id)
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            current_node=task.current_node,
            details=task.details,
        )

    def _move_to_waiting_human(
        self,
        *,
        task_id: str,
        state: AuthoringTaskState,
        pending_action_id: str | None,
        pending_reason: str | None = None,
    ) -> None:
        """Переводит задачу в waiting_human и обновляет SLA-дедлайн итерации."""

        deadline_at = datetime.now(timezone.utc) + timedelta(seconds=self._hitl_wait_timeout_sec)
        iteration = max(1, state.hitl_iteration)
        max_iterations = max(1, state.hitl_max_iterations)
        resolved_pending_reason = pending_reason or "Требуется ручное решение reviewer."
        if iteration >= max_iterations:
            resolved_pending_reason = "Достигнута финальная HITL-итерация: используйте approve/reject."

        waiting_state = state.model_copy(
            update={
                "current_step": "waiting_human",
                "hitl_status": "pending",
                "hitl_pending_action_id": pending_action_id,
                "hitl_deadline_at": deadline_at.isoformat(),
            }
        )
        self._task_service.save_checkpoint(task_id, waiting_state.model_dump(mode="json"))
        self._task_service.update_task(
            task_id,
            status="waiting_human",
            current_node="waiting_human",
            details={
                "current_step": "waiting_human",
                "workflow_mode": waiting_state.workflow_mode,
                "hitl_required": True,
                "hitl_iteration": iteration,
                "hitl_max_iterations": max_iterations,
                "hitl_deadline_at": deadline_at.isoformat(),
                "hitl_pending_action_id": pending_action_id,
                "pending_reason": resolved_pending_reason,
                "review_status": waiting_state.review_result.get("status"),
                "final_recommendation": waiting_state.review_result.get("recommendation"),
                "steps_summary": waiting_state.steps_summary,
            },
        )

    def _parse_datetime(self, raw: Any) -> datetime | None:
        """Аккуратно парсит iso-datetime из state/details payload."""

        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _find_hitl_action_by_idempotency_key(
        self,
        actions: list[dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        for action in actions:
            if str(action.get("idempotency_key", "")) == idempotency_key:
                return action
        return None

    def _find_hitl_action_by_id(self, actions: list[dict[str, Any]], action_id: str) -> dict[str, Any] | None:
        for action in actions:
            if str(action.get("action_id", "")) == action_id:
                return action
        return None

    def _update_hitl_action(
        self,
        actions: list[dict[str, Any]],
        *,
        action_id: str,
        updates: dict[str, Any],
    ) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        for action in actions:
            if str(action.get("action_id", "")) == action_id:
                current = dict(action)
                current.update(updates)
                updated.append(current)
            else:
                updated.append(dict(action))
        return updated

    def _persist_hitl_action(self, *, task_id: str, action: dict[str, Any]) -> None:
        """Сохраняет HITL action в отдельный persistence/read-model слой."""

        action_id = str(action.get("action_id", "")).strip()
        if not action_id:
            return
        iteration = action.get("iteration")
        if not isinstance(iteration, int) or iteration < 1:
            iteration = 1
        self._hitl_action_store.save_action(
            HitlActionRecord(
                action_id=action_id,
                task_id=task_id,
                iteration=iteration,
                decision=str(action.get("decision", "")),
                status=str(action.get("status", "")),
                comment=action.get("comment"),
                reviewer=str((action.get("metadata") or {}).get("reviewer", "")) or None,
                idempotency_key=str(action.get("idempotency_key", "")) or None,
                metadata=dict(action.get("metadata") or {}),
                created_at=self._parse_datetime(action.get("created_at")),
                updated_at=datetime.now(timezone.utc),
            )
        )

    def _to_hitl_action_response(self, record: HitlActionRecord) -> HitlReviewActionResponse:
        """Преобразует internal HITL action record в API response модель."""

        return HitlReviewActionResponse(
            action_id=record.action_id,
            iteration=record.iteration,
            decision=record.decision,
            comment=record.comment,
            status=record.status,
            idempotency_key=record.idempotency_key,
            metadata=record.metadata,
            created_at=record.created_at,
        )

    def _apply_human_feedback_to_draft(self, *, draft: str, comment: str, metadata: dict[str, Any]) -> str:
        return self._writer_draft_service.apply_human_feedback(
            draft=draft,
            comment=comment,
            metadata=metadata,
        )

    def _set_section_review_status(self, *, sections: list[dict[str, Any]], review_status: str) -> list[dict[str, Any]]:
        return self._section_review_service.set_section_review_status(
            sections=sections,
            review_status=review_status,
        )

    def _to_source_refs_from_evidence(self, sections: list[dict[str, Any]]) -> list[SourceRef]:
        return self._outline_planner.collect_source_refs_from_sections(sections)

    def _to_source_refs(self, raw_refs: list[dict[str, Any]]) -> list[SourceRef]:
        return self._outline_planner.to_source_refs(raw_refs)

    def _build_research_summary(self, *, query: str, evidence_pack: EvidencePack) -> str:
        return self._research_summary_builder.build_summary(query=query, evidence_pack=evidence_pack)

    def _generate_draft(
        self,
        *,
        query: str,
        evidence_pack: EvidencePack,
        draft_strategy: str,
        research_summary: str,
    ) -> DraftGenerationResult:
        if draft_strategy not in {"auto", "deterministic", "llm"}:
            raise ValueError(f"Неподдерживаемый draft_strategy: {draft_strategy}")

        should_use_llm = draft_strategy == "llm" or (draft_strategy == "auto" and self._llm_enabled)
        if not should_use_llm:
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic",
            )

        if self._chat_model_gateway is None:
            reason = "LLM gateway не сконфигурирован для выбранной стратегии"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": reason},
            )

        prompt = self._build_llm_prompt(query=query, evidence_pack=evidence_pack, research_summary=research_summary)
        try:
            generated = self._chat_model_gateway.generate(
                prompt,
                metadata={"temperature": 0.2, "max_tokens": 1100},
            )
        except Exception as exc:
            if self._llm_strict_mode or draft_strategy == "llm":
                raise
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": str(exc)},
            )

        content = generated.strip()
        if not content:
            reason = "LLM вернула пустой writer draft"
            if self._llm_strict_mode or draft_strategy == "llm":
                raise RuntimeError(reason)
            return DraftGenerationResult(
                content=self._build_writer_draft_content(
                    query=query,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                ),
                mode="deterministic_fallback",
                metadata={"fallback_reason": reason},
            )

        return DraftGenerationResult(
            content=content,
            mode="llm",
            metadata={
                "provider": self._llm_provider,
                "model_name": self._llm_model_name,
            },
        )

    def _build_writer_draft_content(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        return self._writer_draft_service.build_deterministic_draft(
            query=query,
            evidence_pack=evidence_pack,
            research_summary=research_summary,
        )

    def _review_draft(
        self,
        *,
        query: str,
        draft: str,
        evidence_pack: EvidencePack,
        workflow_mode: str,
    ) -> dict[str, Any]:
        return self._section_review_service.review_draft(
            query=query,
            draft=draft,
            evidence_pack=evidence_pack,
            workflow_mode=workflow_mode,
        )

    def _build_section_traceability(
        self,
        *,
        evidence_pack: EvidencePack,
        review_result: dict[str, Any],
        template_spec: TemplateSpec | None = None,
        section_contracts: list[SectionContract] | None = None,
    ) -> list[dict[str, Any]]:
        return self._outline_planner.build_section_traceability(
            evidence_pack=evidence_pack,
            review_result=review_result,
            template_spec=template_spec,
            section_contracts=section_contracts,
        )

    def _build_section_contracts(
        self,
        *,
        task_context: dict[str, Any],
        evidence_pack: EvidencePack,
        review_result: dict[str, Any],
    ) -> tuple[TemplateSpec, list[SectionContract]]:
        template_id = str(task_context.get("template_id") or "release_readiness").strip() or "release_readiness"
        template_version_raw = task_context.get("template_version")
        template_version = str(template_version_raw).strip() if template_version_raw is not None else None
        template_payload = task_context.get("template_payload")
        return self._section_contract_builder.build_contracts_from_template(
            template_id=template_id,
            evidence_pack=evidence_pack,
            review_status=str(review_result.get("status", "not_reviewed")),
            template_payload=template_payload if isinstance(template_payload, dict) else None,
            template_version=template_version or None,
        )

    def _build_section_artifacts(
        self,
        *,
        section_contracts: list[SectionContract],
        query: str,
        task_context: dict[str, Any],
        evidence_pack: EvidencePack,
        research_summary: str,
        review_result: dict[str, Any],
    ) -> list[SectionArtifact]:
        artifacts: list[SectionArtifact] = []
        for contract in section_contracts:
            workflow_state = SectionAuthoringState(
                task_context={
                    "task_id": str(task_context.get("task_id", "")).strip(),
                    "correlation_id": str(task_context.get("correlation_id", "")).strip(),
                    "section_id": contract.section_id,
                },
                query=query,
                section_contract=contract,
                project_context=task_context,
                evidence_pack=evidence_pack,
                research_summary=research_summary,
                review_result={"parent_review_status": review_result.get("status")},
            )
            result = SectionAuthoringState.model_validate(self._section_authoring_workflow.invoke(workflow_state))
            if result.final_section_artifact is None:
                raise WorkflowExecutionError(
                    f"SectionAuthoringWorkflow не вернул артефакт для section_id={contract.section_id}"
                )
            artifacts.append(result.final_section_artifact)
        return artifacts

    def _run_document_assembly_workflow(
        self,
        *,
        query: str,
        artifact_type: str,
        artifact_title: str | None,
        artifact_format: str,
        workflow_mode: str,
        task_context: dict[str, Any],
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
    ) -> dict[str, Any]:
        state = AssemblyWorkflowState(
            task_context={
                "task_id": str(task_context.get("task_id", "")).strip(),
                "correlation_id": str(task_context.get("correlation_id", "")).strip(),
                "template_id": template_spec.template_id,
            },
            query=query,
            artifact_type=artifact_type,
            artifact_title=artifact_title,
            artifact_format=artifact_format,
            workflow_mode=workflow_mode,
            research_summary=research_summary,
            writer_draft=writer_draft,
            review_result=review_result,
            template_spec=template_spec.model_dump(mode="json"),
            section_artifacts=section_artifacts,
            section_traceability=section_traceability,
        )
        result = AssemblyWorkflowState.model_validate(self._document_assembly_workflow.invoke(state))
        if not isinstance(result.final_document, dict):
            raise WorkflowExecutionError("DocumentAssemblyWorkflow не вернул final_document")
        export_payload = result.export_result if isinstance(result.export_result, dict) else {}
        return {
            "final_content": str(result.final_document.get("content", "")),
            "format": str(result.final_document.get("format", artifact_format)),
            "assembled_content": str(result.assembled_content or result.final_document.get("assembled_content", "")),
            "export_result": ArtifactExportResult.model_validate(export_payload),
            "final_document": result.final_document,
        }

    def _build_llm_prompt(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        return self._writer_draft_service.build_llm_prompt(
            query=query,
            evidence_pack=evidence_pack,
            research_summary=research_summary,
        )

    def _select_sources_by_keywords(
        self,
        *,
        evidence_pack: EvidencePack,
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, str]]:
        return self._outline_planner.select_sources_by_keywords(
            evidence_pack=evidence_pack,
            keywords=keywords,
            limit=limit,
        )

    def _dedup_source_dicts(self, sources: list[SourceRef]) -> list[dict[str, str]]:
        return self._outline_planner.dedup_source_refs(sources)

    def _build_traceability(
        self,
        *,
        retrieval_task_id: str,
        evidence_pack: EvidencePack,
        section_traceability: list[dict[str, Any]],
        workflow_steps: list[AuthoringStepResult],
    ) -> dict[str, Any]:
        return self._outline_planner.build_traceability(
            retrieval_task_id=retrieval_task_id,
            evidence_pack=evidence_pack,
            section_traceability=section_traceability,
            workflow_steps=workflow_steps,
        )

    def _build_outline_snapshot(
        self,
        *,
        template_spec: TemplateSpec,
        section_contracts: list[SectionContract],
        section_traceability: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._outline_planner.build_outline_snapshot(
            template_id=template_spec.template_id,
            section_contracts=section_contracts,
            section_traceability=section_traceability,
        )

    def _build_hitl_outline_response(self, state: AuthoringTaskState) -> HitlOutlineResponse | None:
        snapshot = state.task_context.get("outline_snapshot")
        if not isinstance(snapshot, dict):
            return None
        sections_payload = snapshot.get("sections") if isinstance(snapshot.get("sections"), list) else []
        return HitlOutlineResponse(
            template_id=str(snapshot.get("template_id", state.task_context.get("template_id", "release_readiness"))),
            sections=[
                HitlOutlineSectionResponse(
                    section_id=str(item.get("section_id", "")),
                    title=str(item.get("title", "")),
                    review_status=str(item.get("review_status", "not_reviewed")),
                    objective=str(item.get("objective", "") or "") or None,
                    required_keywords=[str(value) for value in item.get("required_keywords", [])],
                    source_refs=self._to_source_refs(item.get("source_refs", [])),
                )
                for item in sections_payload
            ],
        )
