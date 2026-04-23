from __future__ import annotations

from pathlib import Path

from application.document_service import DocumentApplicationService
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from domain_docs.indexing.workflows import KnowledgeIndexingWorkflow
from domain_docs.parsing import CanonicalDocumentParser
from infra.postgres.document_repository import PostgresDocumentRepository
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
    repository = PostgresDocumentRepository(use_fallback_if_unset=True)
    document_service = DocumentApplicationService(repository=repository)

    service = KnowledgeIndexingApplicationService(document_service=document_service)
    result = service.index_paths([dataset_dir])

    assert len(result.indexed_doc_ids) == 4
    loaded = document_service.get_document(result.indexed_doc_ids[0])
    assert loaded.payload["doc_id"] == result.indexed_doc_ids[0]
    assert loaded.payload["content_blocks"]
