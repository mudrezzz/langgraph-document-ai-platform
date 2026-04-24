from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from domain_rag.retrieval import build_retrieval_workflow
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore
from infra.tei.embedding_gateway import TeiEmbeddingGateway
from schemas.rag.contracts import RetrievalFilter
from schemas.workflow.states import RetrievalWorkflowState


def test_retrieval_pack_workflow_fills_state_fields() -> None:
    workflow = build_retrieval_workflow()

    state = RetrievalWorkflowState(
        query="evidence pack",
        filters=RetrievalFilter(project_id="p1", document_types=["requirements", "methodology"]),
    )

    result = workflow.invoke(state)

    assert result.evidence_pack is not None
    assert result.confidence is not None
    assert result.evidence_pack.confidence_notes
    assert len(result.selected_summaries) >= 1
    assert len(result.selected_blocks) >= 1
    assert len(result.reranked_blocks) >= 1


def test_retrieval_pack_workflow_resume_validates_state() -> None:
    workflow = build_retrieval_workflow()

    payload = {
        "query": "langgraph",
        "filters": {"project_id": "p1"},
    }

    resumed = workflow.resume(payload)

    assert resumed.query == "langgraph"
    assert resumed.filters.project_id == "p1"


def test_canonical_retrieval_workflow_uses_pgvector_summary_and_detail_layers(tmp_path: Path) -> None:
    source = tmp_path / "release_decision.md"
    source.write_text(
        "## Release Decision\n\n"
        "- Security approval is pending.\n"
        "- Rollback plan is ready.\n",
        encoding="utf-8",
    )
    canonical_document_service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )
    embedding_gateway = TeiEmbeddingGateway(vector_dim=16)
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    indexing_service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        embedding_gateway=embedding_gateway,
        vector_store=vector_store,
    )
    indexing_result = indexing_service.index_paths([source])

    workflow = build_retrieval_workflow(
        knowledge_source="canonical",
        canonical_document_service=canonical_document_service,
        canonical_doc_ids=indexing_result.indexed_doc_ids,
        embedding_gateway=embedding_gateway,
        vector_store=vector_store,
    )
    result = workflow.invoke(
        RetrievalWorkflowState(
            query="security approval",
            filters=RetrievalFilter(project_id="p1"),
        )
    )

    assert result.selected_summaries
    assert result.selected_blocks
    assert all(block.metadata["retrieval_backend"] == "pgvector" for block in result.selected_summaries)
    assert all(block.metadata["retrieval_backend"] == "pgvector" for block in result.selected_blocks)
    assert {block.metadata["block_kind"] for block in result.selected_summaries} == {"section_summary"}
    assert {block.metadata["block_kind"] for block in result.selected_blocks} == {"content_block"}
