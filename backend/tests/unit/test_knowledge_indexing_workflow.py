from __future__ import annotations

from pathlib import Path

import pytest

from application.async_dispatcher import InlineKnowledgeIndexingAsyncDispatcher
from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import WorkflowExecutionError
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from domain_docs.indexing.workflows import KnowledgeIndexingWorkflow
from domain_docs.parsing import CanonicalDocumentParser
from infra.docs.ocr_gateway import SidecarPdfOcrGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.canonical_document_store import PostgresCanonicalDocumentStore
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.tei.embedding_gateway import TeiEmbeddingGateway
from scripts.build_binary_demo_documents import build_binary_demo_documents
from schemas.api.contracts import StartKnowledgeIndexingTaskRequest
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
    build_binary_demo_documents(output_dir=dataset_dir, overwrite=True)
    store = PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    canonical_document_service = CanonicalDocumentApplicationService(store=store)

    service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        parser=CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()),
    )
    result = service.index_paths([dataset_dir])

    assert len(result.indexed_doc_ids) == 7
    assert result.quality_summary["gate_status"] in {"passed", "warning"}
    assert result.quality_summary["documents_total"] == 7
    assert "parser_families" in result.quality_summary
    assert result.quality_summary["parser_issues_total"] >= 0
    assert result.quality_summary["documents_needing_ocr"] >= 1
    loaded = canonical_document_service.get_document(result.indexed_doc_ids[0])
    assert loaded.doc_id == result.indexed_doc_ids[0]
    assert loaded.content_blocks
    assert loaded.parser_quality.blocks_total >= 0
    assert canonical_document_service.list_blocks(limit=100).total_returned >= 8
    docx_document = next(document for document in result.documents if document.file_type == "docx")
    assert docx_document.extracted_tables
    assert any(block.block_type == "table_row" for block in docx_document.content_blocks)


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

    assert result.embeddings_indexed == 3
    assert stored is not None
    vector, metadata = stored
    assert len(vector) == 8
    assert metadata["kind"] == "knowledge_block_embedding"
    assert metadata["block_ref"] == block.block_ref
    document = canonical_document_service.get_document(result.indexed_doc_ids[0])
    summary_key = (
        f"knowledge_summary:{document.doc_id}:{document.version}:"
        f"summary:{document.section_summaries[0].section_id}"
    )
    summary_stored = vector_store.get_vector(summary_key)
    assert summary_stored is not None
    _, summary_metadata = summary_stored
    assert summary_metadata["kind"] == "knowledge_summary_embedding"
    assert summary_metadata["block_id"].startswith("summary:")


def test_knowledge_indexing_application_service_start_async_with_inline_dispatcher(tmp_path: Path) -> None:
    source = tmp_path / "ops_readiness.txt"
    source.write_text("Rollback plan is ready.\nMonitoring dashboard is active.", encoding="utf-8")

    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=CanonicalDocumentApplicationService(
            store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
        ),
        task_service=task_service,
    )
    dispatcher = InlineKnowledgeIndexingAsyncDispatcher(
        runner=lambda task_id, payload: service.run_existing_task(
            task_id=task_id,
            request=StartKnowledgeIndexingTaskRequest.model_validate(payload),
        )
    )

    started = service.start_task_async(
        StartKnowledgeIndexingTaskRequest(
            source_paths=[str(source)],
            task_context={"requester": "unit-test"},
        ),
        dispatcher=dispatcher,
    )

    assert started.status == "queued"
    task = task_service.get_task(started.task_id)
    assert task.status == "completed"
    assert task.details["execution_mode"] == "async"
    assert task.details["dispatch_id"] == f"inline-knowledge-indexing-{started.task_id}"

    payload = task_service.get_state_payload(started.task_id)
    assert payload["task_context"]["task_id"] == started.task_id
    assert payload["source_paths"] == [str(source)]
    assert task.details["parser_quality"]


def test_knowledge_indexing_application_service_start_async_marks_task_failed_on_dispatch_error(tmp_path: Path) -> None:
    source = tmp_path / "ops_readiness.txt"
    source.write_text("Rollback plan is ready.", encoding="utf-8")

    task_service = TaskApplicationService(
        registry=InMemoryTaskRegistry(),
        checkpoint_store=LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True),
    )
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=CanonicalDocumentApplicationService(
            store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
        ),
        task_service=task_service,
    )

    class _FailingDispatcher:
        def enqueue_knowledge_indexing_start(self, *, task_id: str, request_payload: dict) -> str:
            _ = task_id, request_payload
            raise RuntimeError("broker unavailable")

    with pytest.raises(WorkflowExecutionError, match="async очередь"):
        service.start_task_async(
            StartKnowledgeIndexingTaskRequest(
                source_paths=[str(source)],
                task_context={"requester": "unit-test"},
            ),
            dispatcher=_FailingDispatcher(),
        )

    tasks = task_service.list_tasks(limit=10, task_type="knowledge_indexing")
    assert tasks.total_returned == 1
    task = tasks.items[0]
    assert task.status == "failed"
    assert task.details["execution_mode"] == "async"
    assert task.details["error"] == "broker unavailable"
