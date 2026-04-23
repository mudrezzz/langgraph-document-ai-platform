from __future__ import annotations

from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import WorkflowExecutionError
from application.task_service import TaskApplicationService
from domain_docs.indexing.bootstrap import build_knowledge_indexing_workflow
from domain_docs.parsing import CanonicalDocumentParser
from framework.models.interfaces import IEmbeddingGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from schemas.api.contracts import StartTaskResponse
from schemas.documents.contracts import CanonicalDocument
from schemas.workflow.states import KnowledgeIndexingState

_BLOCKING_QUALITY_FLAGS = {"empty_document", "no_content_blocks", "pdf_no_extractable_text"}


class KnowledgeIndexingResult:
    """Result object for canonical ingestion/indexing."""

    def __init__(
        self,
        *,
        documents: list[CanonicalDocument],
        indexed_doc_ids: list[str],
        quality_flags: list[str],
        embeddings_indexed: int = 0,
        quality_summary: dict | None = None,
    ) -> None:
        self.documents = documents
        self.indexed_doc_ids = indexed_doc_ids
        self.quality_flags = quality_flags
        self.embeddings_indexed = embeddings_indexed
        self.quality_summary = quality_summary or {}


class KnowledgeIndexingApplicationService:
    """Application boundary for canonical document ingestion."""

    def __init__(
        self,
        *,
        canonical_document_service: CanonicalDocumentApplicationService,
        parser: CanonicalDocumentParser | None = None,
        embedding_gateway: IEmbeddingGateway | None = None,
        vector_store: PgVectorStoreAdapter | None = None,
        task_service: TaskApplicationService | None = None,
    ) -> None:
        self._canonical_document_service = canonical_document_service
        self._parser = parser or CanonicalDocumentParser()
        self._embedding_gateway = embedding_gateway
        self._vector_store = vector_store
        self._task_service = task_service

    def start_task(self, paths: list[str | Path], *, task_context: dict | None = None) -> StartTaskResponse:
        if self._task_service is None:
            raise WorkflowExecutionError("Knowledge indexing task lifecycle требует TaskApplicationService")

        task = self._task_service.create_task(task_type="knowledge_indexing")
        effective_context = {**(task_context or {}), "task_id": task.task_id}
        initial_payload = {
            "task_context": effective_context,
            "source_paths": [str(path) for path in paths],
        }

        try:
            result = self.index_paths(paths, task_context=effective_context)
        except Exception as exc:
            self._task_service.fail_task(
                task_id=task.task_id,
                state_payload=initial_payload,
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

        self._task_service.complete_task(
            task_id=task.task_id,
            state_payload=_build_state_payload(result=result, task_context=effective_context, paths=paths),
            details=_build_task_details(result),
        )
        return StartTaskResponse(task_id=task.task_id, status="completed")

    def index_paths(self, paths: list[str | Path], *, task_context: dict | None = None) -> KnowledgeIndexingResult:
        documents: list[CanonicalDocument] = []
        for path in paths:
            source_path = Path(path)
            if source_path.is_dir():
                documents.extend(self._parser.parse_dir(source_path))
            else:
                documents.append(self._parser.parse_path(source_path))

        workflow = build_knowledge_indexing_workflow(canonical_document_service=self._canonical_document_service)
        result_state = workflow.invoke(
            KnowledgeIndexingState(
                task_context=task_context or {},
                source_paths=[str(path) for path in paths],
                documents=documents,
            )
        )
        embeddings_indexed = self._index_embeddings(result_state.documents)
        return KnowledgeIndexingResult(
            documents=result_state.documents,
            indexed_doc_ids=result_state.indexed_doc_ids,
            quality_flags=result_state.quality_flags,
            embeddings_indexed=embeddings_indexed,
            quality_summary=_build_quality_summary(result_state.documents, result_state.quality_flags),
        )

    def _index_embeddings(self, documents: list[CanonicalDocument]) -> int:
        if self._embedding_gateway is None or self._vector_store is None:
            return 0

        indexed = 0
        for document in documents:
            metadata_by_doc = {
                "project_id": document.metadata_profile.get("project_id", "p1"),
                "document_type": document.metadata_profile.get("document_type", "requirements"),
                "tags": document.metadata_profile.get("tags", []),
                "doc_title": document.metadata_profile.get("doc_title")
                or document.metadata_profile.get("file_name")
                or document.doc_id,
                "source_path": document.source_path,
                "file_type": document.file_type,
                "quality_flags": list(document.quality_flags),
            }
            for block in document.content_blocks:
                block_ref = f"{document.doc_id}:{document.version}:{block.block_id}"
                vector_key = f"knowledge_block:{block_ref}"
                self._vector_store.upsert_vector(
                    vector_key,
                    self._embedding_gateway.embed(block.text),
                    {
                        **metadata_by_doc,
                        **block.metadata,
                        "kind": "knowledge_block_embedding",
                        "block_ref": block_ref,
                        "doc_id": document.doc_id,
                        "version": document.version,
                        "block_id": block.block_id,
                        "block_type": block.block_type,
                        "heading_path": block.heading_path,
                        "text": block.text,
                    },
                )
                indexed += 1
        return indexed


def _build_state_payload(
    *,
    result: KnowledgeIndexingResult,
    task_context: dict,
    paths: list[str | Path],
) -> dict:
    return {
        "task_context": task_context,
        "source_paths": [str(path) for path in paths],
        "documents": [document.model_dump(mode="json") for document in result.documents],
        "indexed_doc_ids": result.indexed_doc_ids,
        "quality_flags": result.quality_flags,
        "quality_summary": result.quality_summary,
        "embeddings_indexed": result.embeddings_indexed,
    }


def _build_task_details(result: KnowledgeIndexingResult) -> dict:
    return {
        "documents_total": len(result.documents),
        "indexed_doc_ids": result.indexed_doc_ids,
        "content_blocks_total": sum(len(document.content_blocks) for document in result.documents),
        "section_summaries_total": sum(len(document.section_summaries) for document in result.documents),
        "file_types": sorted({document.file_type for document in result.documents}),
        "stored_blocks_total": sum(len(document.content_blocks) for document in result.documents),
        "embeddings_indexed": result.embeddings_indexed,
        "quality_flags": result.quality_flags,
        "quality_summary": result.quality_summary,
        "quality_gate_status": result.quality_summary.get("gate_status", "passed"),
    }


def _build_quality_summary(documents: list[CanonicalDocument], quality_flags: list[str]) -> dict:
    flagged_doc_ids: set[str] = set()
    blocking_flags: list[str] = []
    warning_flags: list[str] = []

    for flag in quality_flags:
        doc_id, flag_code = _split_quality_flag(flag)
        if doc_id:
            flagged_doc_ids.add(doc_id)
        if flag_code in _BLOCKING_QUALITY_FLAGS:
            blocking_flags.append(flag)
        else:
            warning_flags.append(flag)

    gate_status = "failed" if blocking_flags else "warning" if warning_flags else "passed"
    return {
        "gate_status": gate_status,
        "documents_total": len(documents),
        "documents_with_flags": len(flagged_doc_ids),
        "quality_flags_total": len(quality_flags),
        "blocking_flags": blocking_flags,
        "warning_flags": warning_flags,
    }


def _split_quality_flag(flag: str) -> tuple[str | None, str]:
    if ":" not in flag:
        return None, flag
    doc_id, flag_code = flag.split(":", 1)
    return doc_id or None, flag_code
