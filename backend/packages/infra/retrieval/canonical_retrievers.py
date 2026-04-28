from __future__ import annotations

from framework.models.interfaces import IEmbeddingGateway
from framework.rag.interfaces import IRetriever
from infra.pgvector.vector_store import PgVectorStoreAdapter
from schemas.rag.contracts import RetrievedBlock, RetrievalFilter


class CanonicalVectorRetriever(IRetriever):
    """Vector-backed retriever for canonical knowledge blocks."""

    def __init__(
        self,
        *,
        embedding_gateway: IEmbeddingGateway,
        vector_store: PgVectorStoreAdapter,
        doc_ids: list[str] | None = None,
        search_limit: int = 200,
        metadata_kind: str = "knowledge_block_embedding",
        block_kind: str = "content_block",
    ) -> None:
        self._embedding_gateway = embedding_gateway
        self._vector_store = vector_store
        self._doc_ids = list(dict.fromkeys(doc_ids or []))
        self._search_limit = search_limit
        self._metadata_kind = metadata_kind
        self._block_kind = block_kind

    def retrieve(self, query: str, filters: RetrievalFilter) -> list[RetrievedBlock]:
        query_vector = self._embedding_gateway.embed(query)
        if self._doc_ids:
            results = []
            for doc_id in self._doc_ids:
                results.extend(
                    self._vector_store.query_similar(
                        query_vector,
                        limit=self._search_limit,
                        metadata_filter={"kind": self._metadata_kind, "doc_id": doc_id},
                    )
                )
            results = sorted(results, key=lambda item: item.score, reverse=True)[: self._search_limit]
        else:
            results = self._vector_store.query_similar(
                query_vector,
                limit=self._search_limit,
                metadata_filter={"kind": self._metadata_kind},
            )
        blocks = [
            _result_to_retrieved_block(result.metadata, score=result.score, block_kind=self._block_kind)
            for result in results
        ]
        return [block for block in blocks if _matches_filter(block, filters)]


class CanonicalSummaryVectorRetriever(CanonicalVectorRetriever):
    """Vector-backed retriever for canonical section summaries."""

    def __init__(
        self,
        *,
        embedding_gateway: IEmbeddingGateway,
        vector_store: PgVectorStoreAdapter,
        doc_ids: list[str] | None = None,
        search_limit: int = 200,
    ) -> None:
        super().__init__(
            embedding_gateway=embedding_gateway,
            vector_store=vector_store,
            doc_ids=doc_ids,
            search_limit=search_limit,
            metadata_kind="knowledge_summary_embedding",
            block_kind="section_summary",
        )


def _result_to_retrieved_block(metadata: dict, *, score: float, block_kind: str) -> RetrievedBlock:
    return RetrievedBlock.model_validate(
        {
            "text": metadata.get("text", ""),
            "source": {
                "doc_id": metadata.get("doc_id", ""),
                "version": metadata.get("version", "1"),
                "block_id": metadata.get("block_id", ""),
            },
            "score": score,
            "metadata": {
                "project_id": metadata.get("project_id", "p1"),
                "document_type": metadata.get("document_type", "requirements"),
                "tags": metadata.get("tags", []),
                "doc_title": metadata.get("doc_title"),
                "source_path": metadata.get("source_path"),
                "file_type": metadata.get("file_type"),
                "block_kind": block_kind,
                "block_type": metadata.get("block_type"),
                "heading_path": metadata.get("heading_path", []),
                "block_ref": metadata.get("block_ref"),
                "source_kind": metadata.get("source_kind", block_kind),
                "section_title": metadata.get("section_title"),
                "table_id": metadata.get("table_id"),
                "table_title": metadata.get("table_title"),
                "table_columns": metadata.get("table_columns", []),
                "row_index": metadata.get("row_index"),
                "row_values": metadata.get("row_values", {}),
                "page_number": metadata.get("page_number"),
                "reading_order_index": metadata.get("reading_order_index"),
                "layout_kind": metadata.get("layout_kind"),
                "bbox": metadata.get("bbox"),
                "layout_source": metadata.get("layout_source"),
                "section_id": metadata.get("section_id"),
                "section_title": metadata.get("section_title"),
                "source_block_ids": metadata.get("source_block_ids", []),
                "retrieval_backend": "pgvector",
            },
        }
    )


def _matches_filter(block: RetrievedBlock, filters: RetrievalFilter) -> bool:
    metadata = block.metadata or {}
    if filters.project_id and metadata.get("project_id") != filters.project_id:
        return False
    if filters.document_types and metadata.get("document_type") not in filters.document_types:
        return False
    if filters.tags:
        tags = metadata.get("tags", [])
        if not any(tag in tags for tag in filters.tags):
            return False
    return True
