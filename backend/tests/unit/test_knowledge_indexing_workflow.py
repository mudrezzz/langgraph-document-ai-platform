from __future__ import annotations

from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from domain_docs.indexing.workflows import KnowledgeIndexingWorkflow
from domain_docs.parsing import CanonicalDocumentParser
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore
from infra.tei.embedding_gateway import TeiEmbeddingGateway
from schemas.workflow.states import KnowledgeIndexingState


class _MemoryCanonicalStore:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    def save_document(self, document) -> str:
        self.saved[document.doc_id] = document.model_dump(mode="json")
        return document.doc_id


def test_knowledge_indexing_workflow_persists_documents(tmp_path: Path) -> None:
    source = tmp_path / "ops_readiness.txt"
    source.write_text("Rollback plan is ready.\nMonitoring dashboard is active.", encoding="utf-8")
    document = CanonicalDocumentParser().parse_path(source)
    store = _MemoryCanonicalStore()

    workflow = KnowledgeIndexingWorkflow(store=store)
    result = workflow.invoke(KnowledgeIndexingState(documents=[document]))

    assert result.indexed_doc_ids == [document.doc_id]
    assert document.doc_id in store.saved


def test_knowledge_indexing_application_service_indexes_demo_dir() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dataset_dir = repo_root / "backend" / "examples" / "cases" / "release_go_no_go_multifile_case" / "input"
    store = PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    canonical_document_service = CanonicalDocumentApplicationService(store=store)

    service = KnowledgeIndexingApplicationService(canonical_document_service=canonical_document_service)
    result = service.index_paths([dataset_dir])

    assert len(result.indexed_doc_ids) == 6
    loaded = canonical_document_service.get_document(result.indexed_doc_ids[0])
    assert loaded.doc_id == result.indexed_doc_ids[0]
    assert loaded.content_blocks
    assert canonical_document_service.list_blocks(limit=100).total_returned >= 8


def test_knowledge_indexing_application_service_indexes_embeddings(tmp_path: Path) -> None:
    source = tmp_path / "security_findings.md"
    source.write_text("## Security\n\n- Critical vulnerability is fixed\n- Approval is pending", encoding="utf-8")
    canonical_document_service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        embedding_gateway=TeiEmbeddingGateway(vector_dim=8),
        vector_store=vector_store,
    )

    result = service.index_paths([source])
    block = canonical_document_service.list_blocks(limit=1).items[0]
    stored = vector_store.get_vector(f"knowledge_block:{block.block_ref}")

    assert result.embeddings_indexed == 2
    assert stored is not None
    vector, metadata = stored
    assert len(vector) == 8
    assert metadata["kind"] == "knowledge_block_embedding"
    assert metadata["block_ref"] == block.block_ref
