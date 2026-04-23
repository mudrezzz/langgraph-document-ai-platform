from __future__ import annotations

from pathlib import Path

from application.document_service import DocumentApplicationService
from domain_docs.indexing.bootstrap import build_knowledge_indexing_workflow
from domain_docs.parsing import CanonicalDocumentParser
from schemas.documents.contracts import CanonicalDocument
from schemas.workflow.states import KnowledgeIndexingState


class KnowledgeIndexingResult:
    """Result object for canonical ingestion/indexing."""

    def __init__(
        self,
        *,
        documents: list[CanonicalDocument],
        indexed_doc_ids: list[str],
        quality_flags: list[str],
    ) -> None:
        self.documents = documents
        self.indexed_doc_ids = indexed_doc_ids
        self.quality_flags = quality_flags


class KnowledgeIndexingApplicationService:
    """Application boundary for canonical document ingestion."""

    def __init__(
        self,
        *,
        document_service: DocumentApplicationService,
        parser: CanonicalDocumentParser | None = None,
    ) -> None:
        self._document_service = document_service
        self._parser = parser or CanonicalDocumentParser()

    def index_paths(self, paths: list[str | Path], *, task_context: dict | None = None) -> KnowledgeIndexingResult:
        documents: list[CanonicalDocument] = []
        for path in paths:
            source_path = Path(path)
            if source_path.is_dir():
                documents.extend(self._parser.parse_dir(source_path))
            else:
                documents.append(self._parser.parse_path(source_path))

        workflow = build_knowledge_indexing_workflow(document_service=self._document_service)
        result_state = workflow.invoke(
            KnowledgeIndexingState(
                task_context=task_context or {},
                source_paths=[str(path) for path in paths],
                documents=documents,
            )
        )
        return KnowledgeIndexingResult(
            documents=result_state.documents,
            indexed_doc_ids=result_state.indexed_doc_ids,
            quality_flags=result_state.quality_flags,
        )
