from __future__ import annotations

from pathlib import Path

import pytest

from application.async_dispatcher import InlineKnowledgeIndexingAsyncDispatcher
from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import WorkflowExecutionError
from application.knowledge_indexing_service import KnowledgeIndexingApplicationService
from application.task_service import InMemoryTaskRegistry, TaskApplicationService
from domain_docs.indexing.quality_policy import KnowledgeIndexingQualityPolicy
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
    pytest.importorskip("openpyxl")
    pytest.importorskip("pptx")
    build_binary_demo_documents(output_dir=dataset_dir, overwrite=True)
    store = PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    canonical_document_service = CanonicalDocumentApplicationService(store=store)

    service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        parser=CanonicalDocumentParser(pdf_ocr_gateway=SidecarPdfOcrGateway()),
    )
    result = service.index_paths([dataset_dir])

    assert len(result.indexed_doc_ids) == 9
    assert result.quality_summary["gate_status"] in {"passed", "warning"}
    assert result.quality_summary["documents_total"] == 9
    assert "parser_families" in result.quality_summary
    assert result.quality_summary["parser_issues_total"] >= 0
    assert result.quality_summary["documents_needing_ocr"] >= 1
    assert result.quality_summary["documents_with_pdf_form_confidence_low"] >= 0
    loaded = canonical_document_service.get_document(result.indexed_doc_ids[0])
    assert loaded.doc_id == result.indexed_doc_ids[0]
    assert loaded.content_blocks
    assert loaded.parser_quality.blocks_total >= 0
    assert canonical_document_service.list_blocks(limit=100).total_returned >= 9
    docx_document = next(document for document in result.documents if document.file_type == "docx")
    assert docx_document.extracted_tables
    assert any(block.block_type == "table_row" for block in docx_document.content_blocks)
    xlsx_document = next(document for document in result.documents if document.file_type == "xlsx")
    assert xlsx_document.extracted_tables
    assert any(block.block_type == "table_row" for block in xlsx_document.content_blocks)
    pptx_document = next(document for document in result.documents if document.file_type == "pptx")
    assert pptx_document.content_blocks
    assert any(block.block_type == "slide_title" for block in pptx_document.content_blocks)


def test_knowledge_indexing_quality_policy_rejects_blocking_documents(tmp_path: Path) -> None:
    valid = tmp_path / "valid.md"
    empty = tmp_path / "empty.txt"
    valid.write_text("## Release readiness\n\nSecurity sign-off: ready", encoding="utf-8")
    empty.write_text("", encoding="utf-8")

    canonical_document_service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        quality_policy=KnowledgeIndexingQualityPolicy(),
    )

    result = service.index_paths([tmp_path])
    decisions = result.quality_summary["documents"]
    rejected = [doc_id for doc_id, decision in decisions.items() if not decision["accepted"]]
    accepted = [doc_id for doc_id, decision in decisions.items() if decision["accepted"]]

    assert result.quality_summary["gate_status"] == "failed"
    assert result.quality_summary["rejected_documents_total"] == 1
    assert result.quality_summary["accepted_documents_total"] == 1
    assert len(result.indexed_doc_ids) == 1
    assert result.indexed_doc_ids == accepted
    assert rejected
    assert any(flag.endswith(":empty_document") for flag in result.quality_summary["blocking_flags"])

    persisted = canonical_document_service.list_documents(limit=10)
    assert persisted.total_returned == 1


def test_knowledge_indexing_application_service_reindexes_latest_version_and_keeps_history(tmp_path: Path) -> None:
    source = tmp_path / "security_findings.md"
    source.write_text("## Security\n\n- Approval is pending", encoding="utf-8")
    canonical_document_service = CanonicalDocumentApplicationService(
        store=PostgresCanonicalDocumentStore(use_fallback_if_unset=True)
    )
    vector_store = PgVectorStoreAdapter(use_fallback_if_unset=True)
    service = KnowledgeIndexingApplicationService(
        canonical_document_service=canonical_document_service,
        embedding_gateway=TeiEmbeddingGateway(vector_dim=8),
        vector_store=vector_store,
    )

    first = service.index_paths([source], document_version="1")
    doc_id = first.indexed_doc_ids[0]
    v1_block_ref = f"{doc_id}:1:B-1"
    source.write_text("## Security\n\n- Approval is approved", encoding="utf-8")
    second = service.index_paths([source], document_version="2")
    v2_block_ref = f"{doc_id}:2:B-1"

    latest = canonical_document_service.get_document(doc_id)
    explicit_v1 = canonical_document_service.get_document(doc_id, version="1")
    versions = canonical_document_service.list_versions(doc_id, limit=10)
    latest_blocks = canonical_document_service.list_blocks(limit=10, doc_id=doc_id)
    versioned_blocks = canonical_document_service.list_blocks(limit=10, doc_id=doc_id, version="1")

    assert first.embeddings_indexed == second.embeddings_indexed == 2
    assert latest.version == "2"
    assert latest.content_blocks[0].text == "Approval is approved"
    assert explicit_v1.version == "1"
    assert explicit_v1.content_blocks[0].text == "Approval is pending"
    assert [item.version for item in versions.items] == ["2", "1"]
    assert versions.items[0].is_latest is True
    assert versions.items[1].is_latest is False
    assert [item.block_ref for item in latest_blocks.items] == [v2_block_ref]
    assert latest_blocks.items[0].is_latest is True
    assert [item.block_ref for item in versioned_blocks.items] == [v1_block_ref]
    assert versioned_blocks.items[0].is_latest is False
    assert vector_store.get_vector(f"knowledge_block:{v1_block_ref}") is None
    assert vector_store.get_vector(f"knowledge_block:{v2_block_ref}") is not None


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
            document_version="3",
        ),
        dispatcher=dispatcher,
    )

    assert started.status == "queued"
    task = task_service.get_task(started.task_id)
    assert task.status == "completed"
    assert task.details["execution_mode"] == "async"
    assert task.details["dispatch_id"] == f"inline-knowledge-indexing-{started.task_id}"
    assert task.details["document_versions"]

    payload = task_service.get_state_payload(started.task_id)
    assert payload["task_context"]["task_id"] == started.task_id
    assert payload["source_paths"] == [str(source)]
    assert payload["document_version"] == "3"
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
                document_version="7",
            ),
            dispatcher=_FailingDispatcher(),
        )

    tasks = task_service.list_tasks(limit=10, task_type="knowledge_indexing")
    assert tasks.total_returned == 1
    task = tasks.items[0]
    assert task.status == "failed"
    assert task.details["execution_mode"] == "async"
    assert task.details["document_version"] == "7"
    assert task.details["error"] == "broker unavailable"
