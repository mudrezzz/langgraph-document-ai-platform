from __future__ import annotations

from typing import Any

import pytest

from application.canonical_document_service import CanonicalDocumentApplicationService
from infra.fastmcp.retrieval_service import FastMcpRetrievalService
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore
from schemas.api.contracts import EvidencePackResponse, StartTaskResponse, TaskStatusResponse
from schemas.documents.contracts import CanonicalContentBlock, CanonicalDocument, CanonicalSectionSummary
from schemas.rag.contracts import EvidencePack, RerankedBlock, SourceRef


class _FakeEmbeddingGateway:
    def embed(self, text: str) -> list[float]:
        if "security" in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]


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
    assert metadata["transport"] == "fastmcp"
    assert metadata["policy_version"] == "mcp-policy-v1"
    assert metadata["service_scope"] == "retrieval"
    assert metadata["operation_scopes"] == {"build_evidence_pack": "action", "lookup_source": "read", "search_blocks": "read", "search_summaries": "read"}
    assert "build_evidence_pack" in metadata["tool_names"]
    assert "search_summaries" in metadata["tool_names"]
    assert "search_blocks" in metadata["tool_names"]
    assert "lookup_source" in metadata["tool_names"]


def test_fastmcp_retrieval_service_search_summaries_returns_summary_candidates() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.search_summaries(
        {
            "query": "security approval",
            "project_id": "p1",
            "document_types": ["security"],
            "canonical_doc_ids": ["DOC-1"],
            "limit": 5,
        }
    )

    assert result["query"] == "security approval"
    assert result["total_returned"] == 1
    candidate = result["candidates"][0]
    assert candidate["text"] == "Security summary says approval is pending."
    assert candidate["source"]["doc_id"] == "DOC-1"
    assert candidate["metadata"]["block_kind"] == "section_summary"
    assert candidate["metadata"]["retrieval_backend"] == "pgvector"


def test_fastmcp_retrieval_service_search_blocks_returns_detail_candidates() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.search_blocks(
        {
            "query": "security approval",
            "project_id": "p1",
            "document_types": ["security"],
            "canonical_doc_ids": ["DOC-1"],
            "limit": 5,
        }
    )

    assert result["total_returned"] == 1
    candidate = result["candidates"][0]
    assert candidate["text"] == "Security approval is still pending."
    assert candidate["source"]["block_id"] == "B-1"
    assert candidate["metadata"]["block_kind"] == "content_block"
    assert candidate["metadata"]["block_ref"] == "DOC-1:1:B-1"
    assert candidate["metadata"]["source_kind"] == "page_block"
    assert candidate["metadata"]["page_number"] == 2
    assert candidate["metadata"]["layout_source"] == "pdf_blocks"
    assert candidate["metadata"]["bbox"] == [10.0, 20.0, 200.0, 40.0]


def test_fastmcp_retrieval_service_search_blocks_returns_table_row_provenance() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.search_blocks(
        {
            "query": "customer notification approved",
            "project_id": "p1",
            "document_types": ["governance"],
            "canonical_doc_ids": ["DOC-TABLE"],
            "limit": 5,
        }
    )

    assert result["total_returned"] == 1
    candidate = result["candidates"][0]
    assert candidate["metadata"]["source_kind"] == "table_row"
    assert candidate["metadata"]["table_id"] == "T-1"
    assert candidate["metadata"]["table_title"] == "Approval Matrix"
    assert candidate["metadata"]["row_index"] == 2
    assert candidate["metadata"]["row_values"]["Status"] == "APPROVED"


def test_fastmcp_retrieval_service_search_blocks_applies_tags_filter() -> None:
    mcp_service = _build_indexed_mcp_service()

    matching = mcp_service.search_blocks(
        {
            "query": "security approval",
            "project_id": "p1",
            "document_types": ["security"],
            "tags": ["release"],
            "canonical_doc_ids": ["DOC-1"],
            "limit": 5,
        }
    )
    non_matching = mcp_service.search_blocks(
        {
            "query": "security approval",
            "project_id": "p1",
            "document_types": ["security"],
            "tags": ["finance"],
            "canonical_doc_ids": ["DOC-1"],
            "limit": 5,
        }
    )

    assert matching["total_returned"] == 1
    assert non_matching["total_returned"] == 0
    assert non_matching["candidates"] == []


def test_fastmcp_retrieval_service_lookup_source_returns_block_mapping() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.lookup_source({"block_ref": "DOC-1:1:B-1"})

    assert result["found"] is True
    assert result["doc_id"] == "DOC-1"
    assert result["version"] == "1"
    assert result["block_id"] == "B-1"
    assert result["block_ref"] == "DOC-1:1:B-1"
    assert result["source_path"] == "input/security.md"
    assert result["file_type"] == "md"
    assert result["document_metadata"]["document_type"] == "security"
    assert result["block"]["text"] == "Security approval is still pending."
    assert result["source_provenance"]["source_kind"] == "page_block"
    assert result["source_provenance"]["page_number"] == 2
    assert result["source_provenance"]["layout_source"] == "pdf_blocks"
    assert result["source_provenance"]["bbox"] == [10.0, 20.0, 200.0, 40.0]


def test_fastmcp_retrieval_service_lookup_source_returns_table_row_mapping() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.lookup_source({"block_ref": "DOC-TABLE:1:B-2"})

    assert result["found"] is True
    assert result["block"]["block_type"] == "table_row"
    assert result["source_provenance"]["source_kind"] == "table_row"
    assert result["source_provenance"]["table_id"] == "T-1"
    assert result["source_provenance"]["table_title"] == "Approval Matrix"
    assert result["source_provenance"]["row_index"] == 2
    assert result["source_provenance"]["row_values"]["Owner"] == "Product Owner"
    assert result["table"]["table_id"] == "T-1"
    assert result["table"]["columns"] == ["Check", "Owner", "Status"]
    assert result["table"]["row_values"]["Status"] == "APPROVED"


def test_fastmcp_retrieval_service_lookup_source_resolves_explicit_version() -> None:
    mcp_service = _build_indexed_mcp_service_with_versions()

    latest = mcp_service.lookup_source({"doc_id": "DOC-1"})
    explicit = mcp_service.lookup_source({"doc_id": "DOC-1", "version": "1"})
    by_ref = mcp_service.lookup_source({"block_ref": "DOC-1:1:B-1"})

    assert latest["found"] is True
    assert latest["version"] == "2"
    assert latest["block"] is None
    assert explicit["found"] is True
    assert explicit["version"] == "1"
    assert explicit["block"] is None
    assert by_ref["found"] is True
    assert by_ref["version"] == "1"
    assert by_ref["block"]["text"] == "Security approval is still pending."


def test_fastmcp_retrieval_service_lookup_source_returns_document_mapping_for_doc_id() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.lookup_source({"doc_id": "DOC-1"})

    assert result["found"] is True
    assert result["doc_id"] == "DOC-1"
    assert result["block"] is None
    assert result["source_path"] == "input/security.md"
    assert result["document_metadata"]["quality_flags"] == []
    assert result["document_metadata"]["parser_quality"]["parser_family"] == "text"


def test_fastmcp_retrieval_service_lookup_source_returns_clear_empty_result() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.lookup_source({"doc_id": "DOC-1", "block_id": "missing"})

    assert result["found"] is False
    assert result["error"] == "canonical block missing not found"
    assert result["doc_id"] == "DOC-1"


def test_fastmcp_retrieval_service_lookup_source_handles_invalid_block_ref() -> None:
    mcp_service = _build_indexed_mcp_service()

    result = mcp_service.lookup_source({"block_ref": "invalid-ref"})

    assert result["found"] is False
    assert result["error"] == "doc_id or block_ref is required"


def test_fastmcp_retrieval_service_lookup_source_without_canonical_service_returns_clear_error() -> None:
    mcp_service = FastMcpRetrievalService(_FakeRetrievalService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    result = mcp_service.lookup_source({"doc_id": "DOC-1"})

    assert result["found"] is False
    assert result["error"] == "canonical_document_service is not configured"


def test_fastmcp_retrieval_service_search_requires_indexed_dependencies() -> None:
    mcp_service = FastMcpRetrievalService(_FakeRetrievalService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(RuntimeError, match="embedding_gateway and vector_store"):
        mcp_service.search_summaries({"query": "security approval", "limit": 5})


def _build_indexed_mcp_service_with_versions() -> FastMcpRetrievalService:
    canonical_store = PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    canonical_service = CanonicalDocumentApplicationService(store=canonical_store)
    canonical_service.save_document(
        CanonicalDocument(
            doc_id="DOC-1",
            source_path="input/security-v1.md",
            version="1",
            file_type="md",
            metadata_profile={"project_id": "p1", "document_type": "security", "title": "Security Readiness V1"},
            content_blocks=[
                CanonicalContentBlock(
                    block_id="B-1",
                    block_type="paragraph",
                    text="Security approval is still pending.",
                    heading_path=["Security"],
                    metadata={
                        "project_id": "p1",
                        "document_type": "security",
                        "tags": ["release"],
                        "source_kind": "page_block",
                        "page_number": 2,
                        "layout_source": "pdf_blocks",
                        "bbox": [10.0, 20.0, 200.0, 40.0],
                    },
                )
            ],
            section_summaries=[],
            quality_flags=[],
            parser_quality={"parser_family": "text", "extraction_mode": "text", "blocks_total": 1},
        )
    )
    canonical_service.save_document(
        CanonicalDocument(
            doc_id="DOC-1",
            source_path="input/security-v2.md",
            version="2",
            file_type="md",
            metadata_profile={"project_id": "p1", "document_type": "security", "title": "Security Readiness V2"},
            content_blocks=[
                CanonicalContentBlock(
                    block_id="B-2",
                    block_type="paragraph",
                    text="Security approval is approved.",
                    heading_path=["Security"],
                    metadata={"project_id": "p1", "document_type": "security", "tags": ["release"]},
                )
            ],
            section_summaries=[],
            quality_flags=[],
            parser_quality={"parser_family": "text", "extraction_mode": "text", "blocks_total": 1},
        )
    )
    mcp_service = FastMcpRetrievalService(
        _FakeRetrievalService(),  # type: ignore[arg-type]
        canonical_document_service=canonical_service,
    )
    mcp_service.register_tools()
    return mcp_service


def _build_indexed_mcp_service() -> FastMcpRetrievalService:
    canonical_store = PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    canonical_service = CanonicalDocumentApplicationService(store=canonical_store)
    canonical_service.save_document(
        CanonicalDocument(
            doc_id="DOC-1",
            source_path="input/security.md",
            version="1",
            file_type="md",
            metadata_profile={"project_id": "p1", "document_type": "security", "title": "Security Readiness"},
            content_blocks=[
                CanonicalContentBlock(
                    block_id="B-1",
                    block_type="paragraph",
                    text="Security approval is still pending.",
                    heading_path=["Security"],
                    metadata={
                        "project_id": "p1",
                        "document_type": "security",
                        "tags": ["release"],
                        "source_kind": "page_block",
                        "page_number": 2,
                        "layout_source": "pdf_blocks",
                        "bbox": [10.0, 20.0, 200.0, 40.0],
                    },
                )
            ],
            section_summaries=[
                CanonicalSectionSummary(
                    section_id="S-1",
                    title="Security",
                    summary="Security summary says approval is pending.",
                    source_block_ids=["B-1"],
                    metadata={"project_id": "p1", "document_type": "security", "tags": ["release"]},
                )
            ],
            quality_flags=[],
            parser_quality={"parser_family": "text", "extraction_mode": "text", "blocks_total": 1},
        )
    )
    canonical_service.save_document(
        CanonicalDocument(
            doc_id="DOC-TABLE",
            source_path="input/05_release_notes.docx",
            version="1",
            file_type="docx",
            metadata_profile={"project_id": "p1", "document_type": "governance", "title": "Release Notes"},
            content_blocks=[
                CanonicalContentBlock(
                    block_id="B-2",
                    block_type="table_row",
                    text="Check: Customer notification; Owner: Product Owner; Status: APPROVED",
                    heading_path=["Approval Matrix"],
                    metadata={"table_id": "T-1", "row_index": 2},
                )
            ],
            extracted_tables=[
                {
                    "table_id": "T-1",
                    "title": "Approval Matrix",
                    "columns": ["Check", "Owner", "Status"],
                    "rows": [
                        {"Check": "Rollback readiness", "Owner": "SRE", "Status": "READY"},
                        {"Check": "Customer notification", "Owner": "Product Owner", "Status": "APPROVED"},
                    ],
                    "metadata": {"heading_path": ["Approval Matrix"], "table_index": 1},
                }
            ],
            section_summaries=[
                CanonicalSectionSummary(
                    section_id="S-T1",
                    title="Approval Matrix",
                    summary="Approval matrix includes customer notification approved.",
                    source_block_ids=["B-2"],
                    metadata={"project_id": "p1", "document_type": "governance", "tags": ["approval"]},
                )
            ],
            quality_flags=["docx_tables_detected"],
            parser_quality={"parser_family": "docx", "extraction_mode": "structured", "blocks_total": 1, "tables_total": 1},
        )
    )
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    vector_store.upsert_vector(
        "summary:DOC-1:S-1",
        [1.0, 0.0],
        {
            "kind": "knowledge_summary_embedding",
            "doc_id": "DOC-1",
            "version": "1",
            "block_id": "S-1",
            "text": "Security summary says approval is pending.",
            "project_id": "p1",
            "document_type": "security",
            "tags": ["release"],
            "doc_title": "Security Readiness",
            "source_path": "input/security.md",
            "file_type": "md",
            "section_id": "S-1",
            "section_title": "Security",
            "source_block_ids": ["B-1"],
        },
    )
    vector_store.upsert_vector(
        "block:DOC-1:B-1",
        [1.0, 0.0],
        {
            "kind": "knowledge_block_embedding",
            "doc_id": "DOC-1",
            "version": "1",
            "block_id": "B-1",
            "block_ref": "DOC-1:1:B-1",
            "text": "Security approval is still pending.",
            "project_id": "p1",
            "document_type": "security",
            "tags": ["release"],
            "doc_title": "Security Readiness",
            "source_path": "input/security.md",
            "file_type": "md",
            "block_type": "paragraph",
            "heading_path": ["Security"],
            "source_kind": "page_block",
            "page_number": 2,
            "layout_source": "pdf_blocks",
            "bbox": [10.0, 20.0, 200.0, 40.0],
        },
    )
    vector_store.upsert_vector(
        "block:DOC-TABLE:B-2",
        [0.0, 1.0],
        {
            "kind": "knowledge_block_embedding",
            "block_ref": "DOC-TABLE:1:B-2",
            "doc_id": "DOC-TABLE",
            "version": "1",
            "block_id": "B-2",
            "text": "Check: Customer notification; Owner: Product Owner; Status: APPROVED",
            "project_id": "p1",
            "document_type": "governance",
            "tags": ["approval"],
            "doc_title": "Release Notes",
            "source_path": "input/05_release_notes.docx",
            "file_type": "docx",
            "block_type": "table_row",
            "heading_path": ["Approval Matrix"],
            "source_kind": "table_row",
            "section_title": "Approval Matrix",
            "table_id": "T-1",
            "table_title": "Approval Matrix",
            "table_columns": ["Check", "Owner", "Status"],
            "row_index": 2,
            "row_values": {"Check": "Customer notification", "Owner": "Product Owner", "Status": "APPROVED"},
        },
    )
    mcp_service = FastMcpRetrievalService(
        _FakeRetrievalService(),  # type: ignore[arg-type]
        canonical_document_service=canonical_service,
        embedding_gateway=_FakeEmbeddingGateway(),
        vector_store=vector_store,
    )
    mcp_service.register_tools()
    return mcp_service
