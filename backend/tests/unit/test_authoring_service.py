from __future__ import annotations

import json
from typing import Any

import pytest

from application.authoring_service import AuthoringApplicationService, TaskArtifactLinkRecord
from application.template_library_service import TemplateLibraryApplicationService
from application.async_dispatcher import InlineAuthoringAsyncDispatcher
from application.errors import InvalidTaskStateError, WorkflowExecutionError
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from domain_docs import TemplateCompiler
from domain_authoring import ResearchSummaryBuilder, WriterDraftService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.template_store import PostgresTemplateStore
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


class _TrackingDocumentAssemblyWorkflow:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke(self, payload: Any):
        data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else dict(payload)
        self.calls.append(data)
        return {
            **data,
            "assembled_content": "# Tracked Assembly\n\nTracked content",
            "export_result": {
                "content": "# Tracked Assembly\n\nTracked content",
                "format": "markdown",
                "metadata": {
                    "export_format_requested": data.get("artifact_format"),
                    "export_format_resolved": "markdown",
                    "assembly_workflow": "tracked",
                },
            },
            "final_document": {
                "content": "# Tracked Assembly\n\nTracked content",
                "format": "markdown",
                "metadata": {
                    "assembly_workflow": "tracked",
                },
            },
        }


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
    task = task_service.get_task(response.task_id)
    assert artifact.metadata["draft_generation_mode"] == "llm"
    assert artifact.metadata["draft_model_provider"] == "openrouter"
    assert artifact.metadata["llm_tokens_prompt"] > 0
    assert artifact.metadata["llm_tokens_completion"] > 0
    assert artifact.metadata["llm_tokens_total"] == (
        artifact.metadata["llm_tokens_prompt"] + artifact.metadata["llm_tokens_completion"]
    )
    assert task.details["llm_tokens_prompt"] == artifact.metadata["llm_tokens_prompt"]
    assert task.details["llm_tokens_completion"] == artifact.metadata["llm_tokens_completion"]
    assert task.details["llm_tokens_total"] == artifact.metadata["llm_tokens_total"]
    assert artifact.metadata["workflow_mode"] == "multi_step"
    assert len(artifact.metadata["steps_summary"]) == 4
    assert "Generated by model." in artifact.content


def test_authoring_service_accepts_template_context_for_custom_sections() -> None:
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
            query="prepare decision memo",
            artifact_type="decision_memo",
            artifact_title="Template Aware Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "decision_memo",
                "template_payload": {
                    "version": "2",
                    "sections": [
                        {
                            "section_id": "executive_summary",
                            "title": "Executive Summary",
                            "objective": "Summarize the key executive decision.",
                            "required_keywords": ["approval", "decision"],
                        },
                        {
                            "section_id": "risk_log",
                            "title": "Risk Log",
                            "objective": "List current risks and pending blockers.",
                            "required_keywords": ["risk", "pending"],
                        },
                    ],
                },
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["template_id"] == "decision_memo"
    assert artifact.metadata["template_spec"]["version"] == "2"
    assert artifact.metadata["template_spec"]["assembly_rules"]
    assert artifact.metadata["section_contracts"][0]["section_id"] == "executive_summary"
    assert artifact.metadata["section_artifacts"][0]["section_id"] == "executive_summary"
    assert "# Decision Memo" in artifact.content
    assert "## Executive Summary" in artifact.content


def test_authoring_service_applies_template_assembly_visibility_flags() -> None:
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
            query="prepare board memo",
            artifact_type="board_memo",
            artifact_title="Compact Board Memo",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "board_memo",
                "template_payload": {
                    "version": "1",
                    "sections": [
                        {
                            "section_id": "decision",
                            "title": "Decision",
                            "objective": "Summarize the board decision.",
                            "required_keywords": ["approval", "decision"],
                        }
                    ],
                    "assembly_rules": [
                        {
                            "rule_id": "board_compact",
                            "mode": "section_order",
                            "section_order": ["decision"],
                            "include_writer_draft": False,
                            "include_traceability": False,
                        }
                    ],
                },
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["assembly_rules"][0]["include_writer_draft"] is False
    assert artifact.metadata["template_spec"]["assembly_rules"][0]["include_traceability"] is False
    assert "## Decision" in artifact.content
    assert "## Reviewer" in artifact.content
    assert "## Writer Draft" not in artifact.content
    assert "## Section Traceability" not in artifact.content


def test_authoring_service_exports_json_artifact_when_requested() -> None:
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
            query="prepare board memo",
            artifact_type="board_memo",
            artifact_title="Board Memo JSON",
            artifact_format="json",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "board_memo",
                "template_payload": {
                    "version": "1",
                    "sections": [
                        {
                            "section_id": "decision",
                            "title": "Decision",
                            "objective": "Summarize the board decision.",
                            "required_keywords": ["approval", "decision"],
                        }
                    ],
                    "assembly_rules": [
                        {
                            "rule_id": "board_json",
                            "mode": "section_order",
                            "section_order": ["decision"],
                            "include_writer_draft": False,
                            "include_traceability": False,
                        }
                    ],
                },
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.format == "json"
    assert artifact.metadata["export_format_requested"] == "json"
    assert artifact.metadata["export_format_resolved"] == "json"
    assert '"sections"' in artifact.content
    assert '"writer_draft"' not in artifact.content
    assert '"traceability"' not in artifact.content


def test_authoring_service_applies_conditional_template_assembly_policy_to_json_export() -> None:
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
            query="prepare appendix board memo",
            artifact_type="board_memo",
            artifact_title="Conditional Appendix Board Memo",
            artifact_format="json",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "board_memo",
                "template_payload": {
                    "version": "1",
                    "sections": [
                        {
                            "section_id": "decision",
                            "title": "Decision",
                            "objective": "Summarize the board decision.",
                            "required": True,
                            "section_group": "core",
                            "required_keywords": ["approval", "decision"],
                        },
                        {
                            "section_id": "evidence_register",
                            "title": "Evidence Register",
                            "objective": "Show evidence-backed appendix.",
                            "required": False,
                            "include_if_has_evidence": True,
                            "section_group": "appendix",
                        },
                        {
                            "section_id": "reviewer_appendix",
                            "title": "Reviewer Appendix",
                            "objective": "Show completed reviewer appendix.",
                            "required": False,
                            "include_if_review_status": ["completed"],
                            "section_group": "appendix",
                        },
                    ],
                    "assembly_rules": [
                        {
                            "rule_id": "appendix_only_json",
                            "mode": "section_order",
                            "section_order": ["decision", "evidence_register", "reviewer_appendix"],
                            "allowed_section_groups": ["appendix"],
                            "include_writer_draft": False,
                            "include_traceability": True,
                        }
                    ],
                },
            },
        )
    )

    artifact = service.artifact(response.task_id)
    payload = json.loads(artifact.content)

    assert artifact.format == "json"
    assert [section["section_id"] for section in payload["sections"]] == [
        "evidence_register",
        "reviewer_appendix",
    ]
    assert [section["section_id"] for section in payload["traceability"]["sections"]] == [
        "evidence_register",
        "reviewer_appendix",
    ]
    assert "writer_draft" not in payload
    assert artifact.metadata["template_spec"]["assembly_rules"][0]["allowed_section_groups"] == ["appendix"]


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


def test_authoring_service_uses_injected_document_assembly_workflow() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    tracking_workflow = _TrackingDocumentAssemblyWorkflow()
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        document_assembly_workflow=tracking_workflow,  # type: ignore[arg-type]
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="workflow assembled draft",
            artifact_type="release_report",
            artifact_title="Tracked Assembly Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={"requester": "unit-test"},
        )
    )

    artifact = service.artifact(response.task_id)
    assert len(tracking_workflow.calls) == 1
    assert tracking_workflow.calls[0]["artifact_title"] == "Tracked Assembly Draft"
    assert tracking_workflow.calls[0]["section_artifacts"]
    assert artifact.metadata["assembly_workflow"] == "tracked"
    assert "Tracked content" in artifact.content


def test_authoring_service_hitl_wait_state_exposes_outline_snapshot() -> None:
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
            query="outline approval draft",
            artifact_type="release_report",
            artifact_title="Unit HITL Outline Draft",
            artifact_format="markdown",
            draft_strategy="deterministic",
            workflow_mode="multi_step",
            hitl_required=True,
            task_context={"requester": "unit-test"},
        )
    )
    assert started.status == "waiting_human"

    hitl_status = service.hitl_status(started.task_id)
    assert hitl_status.phase == "outline_review"
    assert hitl_status.outline is not None
    assert hitl_status.outline.template_id == "release_readiness"
    assert hitl_status.outline.sections[0].section_id == "risk_assessment"
    assert hitl_status.outline.sections[0].source_refs


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
    assert "### Human Feedback" not in artifact.content


def test_authoring_service_hitl_observability_summary() -> None:
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
            query="hitl summary draft",
            artifact_type="release_report",
            artifact_title="Unit HITL Summary Draft",
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
            comment="добавь approvals",
            metadata={"reviewer": "unit"},
            idempotency_key="summary-k-1",
            expected_iteration=1,
        ),
        dispatcher=dispatcher,
    )
    assert first_submit.status == "waiting_human"

    second_submit = service.submit_hitl(
        started.task_id,
        SubmitHitlReviewRequest(
            decision="approve",
            comment="теперь ок",
            metadata={"reviewer": "unit"},
            idempotency_key="summary-k-2",
            expected_iteration=2,
        ),
        dispatcher=dispatcher,
    )
    assert second_submit.status == "completed"

    summary = service.hitl_observability_summary(reviewer="unit")
    assert summary.total_actions == 2
    assert summary.unique_tasks == 1
    assert summary.pending_actions == 0
    assert summary.completed_actions == 2
    assert summary.approve_total == 1
    assert summary.needs_changes_total == 1
    assert summary.max_iteration == 2
    assert summary.reviewers[0].reviewer == "unit"


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


def test_authoring_service_loads_template_from_library_when_payload_missing() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    template_library.upsert_template(
        TemplateCompiler().compile(
            template_id="decision_memo",
            template_payload={
                "version": "7",
                "sections": [
                    {
                        "section_id": "executive_summary",
                        "title": "Executive Summary",
                        "objective": "Summarize executive decision.",
                        "required_keywords": ["approval", "decision"],
                    }
                ],
                "assembly_rules": [
                    {
                        "rule_id": "decision_order",
                        "mode": "section_order",
                        "section_order": ["executive_summary"],
                        "include_writer_draft": False,
                        "include_traceability": True,
                    }
                ],
            },
        ),
        metadata={"owner": "unit-test"},
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare decision memo from library",
            artifact_type="decision_memo",
            artifact_title="Library Decision Memo",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "decision_memo",
                "template_version": "7",
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["version"] == "7"
    assert artifact.metadata["section_contracts"][0]["section_id"] == "executive_summary"
    assert "## Executive Summary" in artifact.content


def test_authoring_service_prefers_inline_template_payload_over_library() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    template_library.upsert_template(
        TemplateCompiler().compile(
            template_id="board_memo",
            template_payload={
                "version": "4",
                "sections": [{"section_id": "library_section", "title": "Library Section"}],
            },
        )
    )
    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare board memo with override",
            artifact_type="board_memo",
            artifact_title="Override Board Memo",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "board_memo",
                "template_version": "4",
                "template_payload": {
                    "version": "9",
                    "sections": [{"section_id": "inline_section", "title": "Inline Section"}],
                },
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["version"] == "9"
    assert artifact.metadata["section_contracts"][0]["section_id"] == "inline_section"


def test_authoring_service_prefers_published_template_when_version_missing() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    compiler = TemplateCompiler()
    template_library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={
                "version": "7",
                "sections": [{"section_id": "draft_only", "title": "Draft Only"}],
            },
        )
    )
    template_library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={
                "version": "6",
                "sections": [{"section_id": "published_section", "title": "Published Section"}],
            },
        )
    )
    template_library.publish_template("decision_memo", "6")

    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare decision memo using published template",
            artifact_type="decision_memo",
            artifact_title="Published Decision Memo",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "decision_memo",
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["version"] == "6"
    assert artifact.metadata["section_contracts"][0]["section_id"] == "published_section"


def test_authoring_service_requires_published_template_when_version_missing() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    compiler = TemplateCompiler()
    template_library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={
                "version": "10",
                "sections": [{"section_id": "deprecated_only", "title": "Deprecated Only"}],
            },
        )
    )
    template_library.set_template_status("decision_memo", "10", "deprecated")

    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    with pytest.raises(WorkflowExecutionError, match="published version"):
        service.start(
            StartAuthoringTaskRequest(
                query="prepare decision memo using default published template",
                artifact_type="decision_memo",
                artifact_title="Missing Published Decision Memo",
                artifact_format="markdown",
                draft_strategy="deterministic",
                task_context={
                    "requester": "unit-test",
                    "template_id": "decision_memo",
                },
            )
        )


def test_authoring_service_rejects_archived_template_version() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    compiler = TemplateCompiler()
    template_library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={
                "version": "8",
                "sections": [{"section_id": "archived_section", "title": "Archived Section"}],
            },
        )
    )
    template_library.set_template_status("decision_memo", "8", "archived")

    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    with pytest.raises(WorkflowExecutionError, match="archived"):
        service.start(
            StartAuthoringTaskRequest(
                query="prepare decision memo using archived template",
                artifact_type="decision_memo",
                artifact_title="Archived Decision Memo",
                artifact_format="markdown",
                draft_strategy="deterministic",
                task_context={
                    "requester": "unit-test",
                    "template_id": "decision_memo",
                    "template_version": "8",
                },
            )
        )


def test_authoring_service_allows_explicit_deprecated_template_version() -> None:
    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    template_library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )
    compiler = TemplateCompiler()
    template_library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={
                "version": "9",
                "sections": [{"section_id": "deprecated_section", "title": "Deprecated Section"}],
            },
        )
    )
    template_library.set_template_status("decision_memo", "9", "deprecated")

    service = AuthoringApplicationService(
        task_service=task_service,
        retrieval_service=_FakeRetrievalService(),  # type: ignore[arg-type]
        artifact_service=_FakeArtifactService(),  # type: ignore[arg-type]
        task_artifact_registry=_InMemoryTaskArtifactRegistry(),  # type: ignore[arg-type]
        template_library_service=template_library,
    )

    response = service.start(
        StartAuthoringTaskRequest(
            query="prepare decision memo using deprecated template",
            artifact_type="decision_memo",
            artifact_title="Deprecated Decision Memo",
            artifact_format="markdown",
            draft_strategy="deterministic",
            task_context={
                "requester": "unit-test",
                "template_id": "decision_memo",
                "template_version": "9",
            },
        )
    )

    artifact = service.artifact(response.task_id)
    assert artifact.metadata["template_spec"]["version"] == "9"
    assert artifact.metadata["section_contracts"][0]["section_id"] == "deprecated_section"
