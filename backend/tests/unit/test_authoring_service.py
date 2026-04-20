from __future__ import annotations

from typing import Any

import pytest

from application.authoring_service import AuthoringApplicationService, TaskArtifactLinkRecord
from application.errors import InvalidTaskStateError
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from schemas.api.contracts import EvidencePackResponse, StartAuthoringTaskRequest, StartTaskResponse
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

    artifact = service.artifact(response.task_id)
    assert artifact.task_id == response.task_id
    assert artifact.artifact_type == "release_report"
    assert artifact.title == "Unit Authoring Draft"
    assert len(artifact.traceability.source_refs) == 2


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
    assert "Decision pending manual review." in artifact.content


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
