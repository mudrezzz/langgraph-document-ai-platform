from __future__ import annotations

from typing import Any

import pytest

from application.authoring_service import AuthoringApplicationService, TaskArtifactLinkRecord
from application.async_dispatcher import InlineAuthoringAsyncDispatcher
from application.errors import InvalidTaskStateError
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from domain_authoring import ResearchSummaryBuilder, WriterDraftService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from schemas.api.contracts import (
    EvidencePackResponse,
    StartAuthoringTaskRequest,
    StartTaskResponse,
    SubmitHitlReviewRequest,
)
from schemas.rag.contracts import EvidencePack, RerankedBlock, SourceRef


class _FakeRetrievalService:
    def start(self, request: Any) -> StartTaskResponse:
        _ = request
        return StartTaskResponse(task_id="retrieval-task-1", status="completed")

    def evidence(self, task_id: str) -> EvidencePackResponse:
        assert task_id == "retrieval-task-1"
        pack = EvidencePack(
            selected_sources=[
                SourceRef(doc_id="REQ-001", version="1", block_id="D-1"),
                SourceRef(doc_id="SEC-002", version="2", block_id="D-3"),
            ],
            selected_blocks=[
                RerankedBlock(
                    text="Critical approval is pending",
                    source=SourceRef(doc_id="REQ-001", version="1", block_id="D-1"),
                    score=0.93,
                    metadata={"project_id": "p1", "document_type": "requirements"},
                )
            ],
            unresolved_gaps=[],
            confidence_notes=["unit-authoring"],
        )
        return EvidencePackResponse(task_id=task_id, evidence_pack=pack)


class _FakeArtifactService:
    def __init__(self) -> None:
        self._storage: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def write_artifact(self, *, payload: dict[str, Any], artifact_id: str | None = None, artifact_type: str = "generic"):
        self._counter += 1
        resolved_id = artifact_id or f"artifact-{self._counter}"
        stored_payload = dict(payload)
        stored_payload["artifact_id"] = resolved_id
        stored_payload["artifact_type"] = artifact_type
        self._storage[resolved_id] = stored_payload
        return type("ArtifactRecord", (), {"artifact_id": resolved_id, "artifact_type": artifact_type, "payload": stored_payload})()

    def get_artifact(self, artifact_id: str):
        if artifact_id not in self._storage:
            raise KeyError(artifact_id)
        payload = self._storage[artifact_id]
        return type(
            "ArtifactRecord",
            (),
            {"artifact_id": artifact_id, "artifact_type": payload["artifact_type"], "payload": payload},
        )()


class _InMemoryTaskArtifactRegistry:
    def __init__(self) -> None:
        self._links: dict[str, TaskArtifactLinkRecord] = {}

    def save_link(self, *, task_id: str, artifact_id: str, retrieval_task_id: str, traceability: dict) -> None:
        self._links[task_id] = TaskArtifactLinkRecord(
            task_id=task_id,
            artifact_id=artifact_id,
            retrieval_task_id=retrieval_task_id,
            traceability=dict(traceability),
        )

    def get_link(self, task_id: str) -> TaskArtifactLinkRecord:
        if task_id not in self._links:
            raise KeyError(task_id)
        return self._links[task_id]


class _FakeChatGateway:
    def __init__(self, response: str = "LLM generated draft", error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> str:
        _ = prompt, metadata
        if self._error is not None:
            raise self._error
        return self._response


class _TrackingResearchSummaryBuilder(ResearchSummaryBuilder):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def build_summary(self, *, query: str, evidence_pack: EvidencePack) -> str:
        self.calls.append({"query": query, "blocks": len(evidence_pack.selected_blocks)})
        return "Tracked research summary"


class _TrackingWriterDraftService(WriterDraftService):
    def __init__(self) -> None:
        self.draft_calls: list[dict[str, Any]] = []
        self.prompt_calls: list[dict[str, Any]] = []

    def build_deterministic_draft(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        self.draft_calls.append(
            {
                "query": query,
                "research_summary": research_summary,
                "blocks": len(evidence_pack.selected_blocks),
            }
        )
        return "## Writer Draft\n\nTracked deterministic draft"

    def build_llm_prompt(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        self.prompt_calls.append(
            {
                "query": query,
                "research_summary": research_summary,
                "blocks": len(evidence_pack.selected_blocks),
            }
        )
        return "Tracked llm prompt"


def _build_inline_dispatcher(service: AuthoringApplicationService) -> InlineAuthoringAsyncDispatcher:
    return InlineAuthoringAsyncDispatcher(
        runner=lambda task_id, payload: service.run_existing_task(
            task_id=task_id,
            request=StartAuthoringTaskRequest.model_validate(payload),
        ),
        hitl_runner=lambda task_id, payload: service.process_hitl_action(
            task_id=task_id,
            request=SubmitHitlReviewRequest.model_validate(payload.get("request", {})),
            action_id=str(payload.get("action_id", "")),
        ),
    )


def test_authoring_service_start_and_artifact_flow() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare release draft",
            artifact_type="release_report",
            artifact_title="Unit Authoring Draft",
            artifact_format="markdown",
            task_context={"requester": "unit-test"},
        )
    )

    assert response.status == "completed"
    status = task_service.get_task(response.task_id)
    assert status.details["artifact_id"]
    assert status.details["retrieval_task_id"] == "retrieval-task-1"
    assert status.details["workflow_mode"] == "multi_step"
    assert status.details["current_step"] == "completed"
    assert len(status.details["steps_summary"]) == 4

    artifact = service.artifact(response.task_id)
    assert artifact.task_id == response.task_id
    assert artifact.artifact_type == "release_report"
    assert artifact.title == "Unit Authoring Draft"
    assert len(artifact.metadata["section_contracts"]) == 4
    assert artifact.metadata["section_contracts"][0]["section_id"] == "risk_assessment"
    assert len(artifact.metadata["section_artifacts"]) == 4
    assert artifact.metadata["section_artifacts"][0]["section_id"] == "risk_assessment"
    assert artifact.metadata["section_artifacts"][0]["digest"]["source_refs"]
    assert len(artifact.traceability.source_refs) == 2
    assert len(artifact.traceability.sections) >= 3


def test_authoring_service_uses_llm_when_enabled() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        chat_model_gateway=_FakeChatGateway(response="# LLM Draft\n\nGenerated by model."),
        llm_enabled=True,
        llm_provider="openrouter",
        llm_model_name="openai/gpt-4o-mini",
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare release draft with llm",
            artifact_type="release_report",
            artifact_title="Unit LLM Draft",
            artifact_format="markdown",
            draft_strategy="auto",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["draft_generation_mode"] == "llm"
    assert artifact.metadata["draft_model_provider"] == "openrouter"
    assert artifact.metadata["workflow_mode"] == "multi_step"
    assert len(artifact.metadata["steps_summary"]) == 4
    assert "Generated by model." in artifact.content


def test_authoring_service_fallbacks_to_deterministic_when_llm_fails() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        chat_model_gateway=_FakeChatGateway(error=RuntimeError("gateway timeout")),
        llm_enabled=True,
        llm_strict_mode=False,
        llm_provider="openrouter",
        llm_model_name="openai/gpt-4o-mini",
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare release draft with llm fallback",
            artifact_type="release_report",
            artifact_title="Unit Fallback Draft",
            artifact_format="markdown",
            draft_strategy="auto",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["draft_generation_mode"] == "deterministic_fallback"
    assert "draft_fallback_reason" in artifact.metadata
    assert artifact.metadata["review_status"] in {"completed", "needs_revision"}
    assert "## Writer" in artifact.content


def test_authoring_service_single_pass_marks_reviewer_skipped() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="single pass draft",
            artifact_type="release_report",
            artifact_title="Unit Single Pass",
            artifact_format="markdown",
            draft_strategy="deterministic",
            workflow_mode="single_pass",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["workflow_mode"] == "single_pass"
    assert artifact.metadata["review_status"] == "skipped"


def test_authoring_service_uses_injected_research_and_writer_domain_services() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    research_builder = _TrackingResearchSummaryBuilder()
    writer_service = _TrackingWriterDraftService()
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        research_summary_builder=research_builder,
        writer_draft_service=writer_service,
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="tracked authoring draft",
            artifact_type="release_report",
            artifact_title="Tracked Domain Services",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert research_builder.calls == [{"query": "tracked authoring draft", "blocks": 1}]
    assert writer_service.draft_calls == [
        {"query": "tracked authoring draft", "research_summary": "Tracked research summary", "blocks": 1}
    ]
    assert writer_service.prompt_calls == []
    assert "Tracked deterministic draft" in artifact.content


def test_authoring_service_uses_injected_writer_service_for_llm_prompt() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    writer_service = _TrackingWriterDraftService()
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        research_summary_builder=_TrackingResearchSummaryBuilder(),
        writer_draft_service=writer_service,
        chat_model_gateway=_FakeChatGateway(response="# LLM Draft\n\nTracked model output."),
        llm_enabled=True,
        llm_provider="openrouter",
        llm_model_name="openai/gpt-4o-mini",
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="tracked llm authoring draft",
            artifact_type="release_report",
            artifact_title="Tracked LLM Prompt",
            artifact_format="markdown",
            draft_strategy="auto",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert len(writer_service.prompt_calls) == 1
    assert writer_service.prompt_calls[0]["research_summary"] == "Tracked research summary"
    assert artifact.metadata["draft_generation_mode"] == "llm"
    assert "Tracked model output." in artifact.content


def test_authoring_service_supports_hitl_wait_and_submit() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
    )

    started = service.start(
        StartAuthoringTaskRequest(
            query="hitl required draft",
            artifact_type="release_report",
            artifact_title="Unit HITL Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            workflow_mode="multi_step",
            hitl_required=True,
            task_context={"requester": "unit-test"},
        )
    )
    assert started.status == "waiting_human"

    hitl_status = service.hitl_status(started.task_id)
    assert hitl_status.status == "waiting_human"
    assert hitl_status.required is True

    submitted = service.submit_hitl(
        started.task_id,
        SubmitHitlReviewRequest(
            decision="approve",
            comment="looks good",
            metadata={"reviewer": "unit"},
        ),
        dispatcher=_build_inline_dispatcher(service),
    )
    assert submitted.status == "completed"
    artifact = service.artifact(started.task_id)
    assert artifact.metadata["hitl_decision"] == "approve"
    assert artifact.metadata["hitl_iteration"] == 1


def test_authoring_service_hitl_iterations_and_idempotency() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        hitl_max_iterations=2,
    )
    dispatcher = _build_inline_dispatcher(service)

    started = service.start(
        StartAuthoringTaskRequest(
            query="hitl iterative draft",
            artifact_type="release_report",
            artifact_title="Unit HITL Iterative Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            workflow_mode="multi_step",
            hitl_required=True,
            task_context={"requester": "unit-test"},
        )
    )
    assert started.status == "waiting_human"

    first_submit = service.submit_hitl(
        started.task_id,
        SubmitHitlReviewRequest(
            decision="needs_changes",
            comment="добавь больше деталей по approvals",
            idempotency_key="k-1",
            expected_iteration=1,
        ),
        dispatcher=dispatcher,
    )
    assert first_submit.status == "waiting_human"

    status_after_first = service.hitl_status(started.task_id)
    assert status_after_first.current_iteration == 2
    assert len(status_after_first.actions) == 1
    assert status_after_first.actions[0].idempotency_key == "k-1"
    assert status_after_first.actions[0].status == "completed"

    replay = service.submit_hitl(
        started.task_id,
        SubmitHitlReviewRequest(
            decision="needs_changes",
            comment="добавь больше деталей по approvals",
            idempotency_key="k-1",
            expected_iteration=2,
        ),
        dispatcher=dispatcher,
    )
    assert replay.status == "waiting_human"
    status_after_replay = service.hitl_status(started.task_id)
    assert len(status_after_replay.actions) == 1

    with pytest.raises(InvalidTaskStateError, match="лимит HITL итераций"):
        service.submit_hitl(
            started.task_id,
            SubmitHitlReviewRequest(
                decision="needs_changes",
                comment="еще правки",
                expected_iteration=2,
            ),
            dispatcher=dispatcher,
        )

    approved = service.submit_hitl(
        started.task_id,
        SubmitHitlReviewRequest(
            decision="approve",
            comment="финально ок",
            idempotency_key="k-2",
            expected_iteration=2,
        ),
        dispatcher=dispatcher,
    )
    assert approved.status == "completed"
    artifact = service.artifact(started.task_id)
    assert artifact.metadata["hitl_iteration"] == 2
    assert artifact.metadata["hitl_max_iterations"] == 2
    assert len(artifact.metadata["section_contracts"]) == 4
    assert len(artifact.metadata["section_artifacts"]) == 4
    assert "### Human Feedback" in artifact.content
    assert "добавь больше деталей по approvals" in artifact.content


def test_authoring_service_start_async_with_inline_dispatcher() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
    )
    dispatcher = _build_inline_dispatcher(service)

    started = service.start_async(
        StartAuthoringTaskRequest(
            query="async unit draft",
            artifact_type="release_report",
            artifact_title="Unit Async Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            workflow_mode="multi_step",
            hitl_required=False,
            task_context={"requester": "unit-test"},
        ),
        dispatcher=dispatcher,
    )
    assert started.status == "queued"

    task = task_service.get_task(started.task_id)
    assert task.status == "completed"


def test_authoring_artifact_endpoint_rejects_non_authoring_task() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    retrieval_task = task_service.create_task(task_type="retrieval_pack")
    task_service.complete_task(retrieval_task.task_id, state_payload={"ok": True}, details={"k": "v"})

    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidTaskStateError, match="authoring_pack"):
        _ = service.artifact(retrieval_task.task_id)
