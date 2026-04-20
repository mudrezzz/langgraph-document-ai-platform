from __future__ import annotations

from typing import Any

from infra.fastmcp.retrieval_service import FastMcpRetrievalService
from schemas.api.contracts import EvidencePackResponse, StartTaskResponse, TaskStatusResponse
from schemas.rag.contracts import EvidencePack, RerankedBlock, SourceRef


class _FakeRetrievalService:
    def __init__(self) -> None:
        self.started_request: Any | None = None

    def start(self, request: Any) -> StartTaskResponse:
        self.started_request = request
        return StartTaskResponse(task_id="task-mcp-1", status="completed")

    def status(self, task_id: str) -> TaskStatusResponse:
        assert task_id == "task-mcp-1"
        return TaskStatusResponse(task_id=task_id, status="completed", details={"source": "mcp"})

    def evidence(self, task_id: str) -> EvidencePackResponse:
        assert task_id == "task-mcp-1"
        pack = EvidencePack(
            selected_sources=[SourceRef(doc_id="SEC-001", version="1", block_id="D-1")],
            selected_blocks=[
                RerankedBlock(
                    text="Security approval: PENDING",
                    source=SourceRef(doc_id="SEC-001", version="1", block_id="D-1"),
                    score=0.95,
                    metadata={"project_id": "p1", "document_type": "security"},
                )
            ],
            unresolved_gaps=[],
            confidence_notes=["mcp-test"],
        )
        return EvidencePackResponse(task_id=task_id, evidence_pack=pack)


def test_fastmcp_retrieval_service_build_evidence_pack() -> None:
    fake_service = _FakeRetrievalService()
    mcp_service = FastMcpRetrievalService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    result = mcp_service.build_evidence_pack(
        {
            "query": "what blocks release",
            "project_id": "p1",
            "document_types": ["security", "governance"],
            "task_context": {"requester": "unit-mcp"},
        }
    )

    assert result["task_id"] == "task-mcp-1"
    assert result["status"] == "completed"
    assert len(result["evidence_pack"]["selected_blocks"]) == 1

    assert fake_service.started_request is not None
    assert fake_service.started_request.filters.project_id == "p1"
    assert fake_service.started_request.task_context["requester"] == "unit-mcp"


def test_fastmcp_retrieval_service_metadata_contains_tools() -> None:
    mcp_service = FastMcpRetrievalService(_FakeRetrievalService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    metadata = mcp_service.metadata()

    assert metadata["service_name"] == "retrieval-mcp"
    assert "build_evidence_pack" in metadata["tool_names"]
