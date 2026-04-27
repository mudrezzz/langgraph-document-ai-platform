from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from application.async_dispatcher import KnowledgeIndexingAsyncDispatcher
from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import WorkflowExecutionError
from application.task_service import TaskApplicationService
from domain_docs.indexing.bootstrap import build_knowledge_indexing_workflow
from domain_docs.parsing import CanonicalDocumentParser
from framework.models.interfaces import IEmbeddingGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from schemas.api.contracts import StartKnowledgeIndexingTaskRequest, StartTaskResponse
from schemas.documents.contracts import CanonicalDocument
from schemas.workflow.states import KnowledgeIndexingState

_BLOCKING_QUALITY_FLAGS = {"empty_document", "no_content_blocks", "pdf_no_extractable_text", "ocr_text_not_recovered"}


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

    def start_task_async(
        self,
        request: StartKnowledgeIndexingTaskRequest,
        *,
        dispatcher: KnowledgeIndexingAsyncDispatcher,
    ) -> StartTaskResponse:
        if self._task_service is None:
            raise WorkflowExecutionError("Knowledge indexing async lifecycle требует TaskApplicationService")

        task = self._task_service.create_task(
            task_type="knowledge_indexing",
            initial_status="queued",
            initial_node="queued",
            details={
                "execution_mode": "async",
                "source_paths_total": len(request.source_paths),
            },
        )
        effective_context = {**request.task_context, "task_id": task.task_id}

        try:
            dispatch_id = dispatcher.enqueue_knowledge_indexing_start(
                task_id=task.task_id,
                request_payload={
                    "source_paths": [str(path) for path in request.source_paths],
                    "task_context": effective_context,
                },
            )
        except Exception as exc:
            self._task_service.update_task(
                task.task_id,
                status="failed",
                current_node="failed",
                details={"error": str(exc), "execution_mode": "async"},
            )
            raise WorkflowExecutionError(f"Не удалось поставить knowledge indexing задачу в async очередь: {exc}") from exc

        current = self._task_service.get_task(task.task_id)
        next_status = current.status if current.status != "queued" else "queued"
        next_node = current.current_node if current.status != "queued" else "queued"
        queue_name = getattr(dispatcher, "queue_name", current.details.get("queue_name", "inline"))
        self._task_service.update_task(
            task.task_id,
            status=next_status,
            current_node=next_node,
            details={
                **current.details,
                "dispatch_id": dispatch_id,
                "execution_mode": "async",
                "queue_name": queue_name,
                "queued_at": current.created_at.isoformat() if current.created_at else None,
                "source_paths_total": len(request.source_paths),
            },
        )
        return StartTaskResponse(task_id=task.task_id, status="queued")

    def run_existing_task(self, *, task_id: str, request: StartKnowledgeIndexingTaskRequest) -> StartTaskResponse:
        if self._task_service is None:
            raise WorkflowExecutionError("Knowledge indexing task lifecycle требует TaskApplicationService")

        current = self._task_service.get_task(task_id)
        if current.task_type != "knowledge_indexing":
            raise WorkflowExecutionError(
                f"Ожидался task_type=knowledge_indexing для run_existing_task, получен {current.task_type}"
            )

        self._task_service.update_task(
            task_id,
            status="running",
            current_node="start",
            details={
                **current.details,
                "source_paths_total": len(request.source_paths),
                "execution_mode": current.details.get("execution_mode", "sync"),
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        effective_context = {**request.task_context, "task_id": task_id}
        initial_payload = {
            "task_context": effective_context,
            "source_paths": [str(path) for path in request.source_paths],
        }

        try:
            result = self.index_paths(request.source_paths, task_context=effective_context)
        except Exception as exc:
            self._task_service.fail_task(
                task_id=task_id,
                state_payload=initial_payload,
                error_message=str(exc),
            )
            raise WorkflowExecutionError(str(exc)) from exc

        details = {
            **_build_task_details(result),
            "execution_mode": current.details.get("execution_mode", "sync"),
            "dispatch_id": current.details.get("dispatch_id"),
        }
        self._task_service.complete_task(
            task_id=task_id,
            state_payload=_build_state_payload(result=result, task_context=effective_context, paths=request.source_paths),
            details=details,
        )
        return StartTaskResponse(task_id=task_id, status="completed")

    def index_paths(self, paths: list[str | Path], *, task_context: dict | None = None) -> KnowledgeIndexingResult:
        documents: list[CanonicalDocument] = []
        for path in paths:
            source_path = Path(path)
            if source_path.is_dir():
                documents.extend(self._parser.parse_dir(source_path))
            else:
                documents.append(self._parser.parse_path(source_path))

        workflow = build_knowledge_indexing_workflow(
            canonical_document_service=self._canonical_document_service,
            node_event_sink=self._task_service.build_workflow_node_event_sink() if self._task_service else None,
        )
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
                table_metadata = _table_metadata_for_block(document=document, block=block)
                self._vector_store.upsert_vector(
                    vector_key,
                    self._embedding_gateway.embed(block.text),
                    {
                        **metadata_by_doc,
                        **table_metadata,
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
            for summary in document.section_summaries:
                block_id = f"summary:{summary.section_id}"
                block_ref = f"{document.doc_id}:{document.version}:{block_id}"
                vector_key = f"knowledge_summary:{block_ref}"
                self._vector_store.upsert_vector(
                    vector_key,
                    self._embedding_gateway.embed(summary.summary),
                    {
                        **metadata_by_doc,
                        **summary.metadata,
                        "kind": "knowledge_summary_embedding",
                        "block_ref": block_ref,
                        "doc_id": document.doc_id,
                        "version": document.version,
                        "block_id": block_id,
                        "section_id": summary.section_id,
                        "section_title": summary.title,
                        "source_block_ids": list(summary.source_block_ids),
                        "text": summary.summary,
                    },
                )
                indexed += 1
        return indexed


def _table_metadata_for_block(*, document: CanonicalDocument, block: CanonicalContentBlock) -> dict:
    if block.block_type != "table_row":
        return {}

    table_id = str(block.metadata.get("table_id", "") or "").strip()
    row_index = block.metadata.get("row_index")
    if not table_id:
        return {"source_kind": "table_row"}

    table = next((item for item in document.extracted_tables if item.table_id == table_id), None)
    if table is None:
        return {
            "source_kind": "table_row",
            "table_title": block.heading_path[-1] if block.heading_path else None,
        }

    row_values = {}
    if isinstance(row_index, int) and 1 <= row_index <= len(table.rows):
        row_values = dict(table.rows[row_index - 1])

    return {
        "source_kind": "table_row",
        "section_title": block.heading_path[-1] if block.heading_path else None,
        "table_title": table.title,
        "table_columns": list(table.columns),
        "row_values": row_values,
    }

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
    parser_quality = {
        document.doc_id: document.parser_quality.model_dump(mode="json") for document in result.documents
    }
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
        "parser_quality": parser_quality,
    }

def _build_quality_summary(documents: list[CanonicalDocument], quality_flags: list[str]) -> dict:
    flagged_doc_ids: set[str] = set()
    blocking_flags: list[str] = []
    warning_flags: list[str] = []
    flags_by_doc: dict[str, set[str]] = {}

    for flag in quality_flags:
        doc_id, flag_code = _split_quality_flag(flag)
        if doc_id:
            flags_by_doc.setdefault(doc_id, set()).add(flag_code)

    for flag in quality_flags:
        doc_id, flag_code = _split_quality_flag(flag)
        if doc_id:
            flagged_doc_ids.add(doc_id)
        if flag_code == "pdf_no_extractable_text" and doc_id and "ocr_applied" in flags_by_doc.get(doc_id, set()):
            warning_flags.append(flag)
            continue
        if flag_code in _BLOCKING_QUALITY_FLAGS:
            blocking_flags.append(flag)
        else:
            warning_flags.append(flag)

    gate_status = "failed" if blocking_flags else "warning" if warning_flags else "passed"
    parser_families = sorted({document.parser_quality.parser_family for document in documents})
    extraction_modes = sorted({document.parser_quality.extraction_mode for document in documents})
    total_issues = sum(len(document.parser_quality.issues) for document in documents)
    documents_with_tables = sum(1 for document in documents if document.parser_quality.tables_total > 0)
    documents_needing_ocr = sum(1 for document in documents if "ocr_required" in document.parser_quality.flags)
    return {
        "gate_status": gate_status,
        "documents_total": len(documents),
        "documents_with_flags": len(flagged_doc_ids),
        "quality_flags_total": len(quality_flags),
        "blocking_flags": blocking_flags,
        "warning_flags": warning_flags,
        "parser_families": parser_families,
        "extraction_modes": extraction_modes,
        "parser_issues_total": total_issues,
        "documents_with_tables": documents_with_tables,
        "documents_needing_ocr": documents_needing_ocr,
    }

def _split_quality_flag(flag: str) -> tuple[str | None, str]:
    if ":" not in flag:
        return None, flag
    doc_id, flag_code = flag.split(":", 1)
    return doc_id or None, flag_code
