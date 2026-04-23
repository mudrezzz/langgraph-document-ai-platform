from __future__ import annotations

from pathlib import Path

from application.canonical_document_service import CanonicalDocumentApplicationService
from domain_docs.indexing.bootstrap import build_knowledge_indexing_workflow
from domain_docs.parsing import CanonicalDocumentParser
from framework.models.interfaces import IEmbeddingGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
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
        embeddings_indexed: int = 0,
    ) -> None:
        self.documents = documents
        self.indexed_doc_ids = indexed_doc_ids
        self.quality_flags = quality_flags
        self.embeddings_indexed = embeddings_indexed


class KnowledgeIndexingApplicationService:
    """Application boundary for canonical document ingestion."""

    def __init__(
        self,
        *,
        canonical_document_service: CanonicalDocumentApplicationService,
        parser: CanonicalDocumentParser | None = None,
        embedding_gateway: IEmbeddingGateway | None = None,
        vector_store: PgVectorStoreAdapter | None = None,
    ) -> None:
        self._canonical_document_service = canonical_document_service
        self._parser = parser or CanonicalDocumentParser()
        self._embedding_gateway = embedding_gateway
        self._vector_store = vector_store

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
