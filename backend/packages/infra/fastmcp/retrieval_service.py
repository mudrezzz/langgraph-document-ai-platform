from __future__ import annotations

from typing import Any, Callable

from application.canonical_document_service import CanonicalDocumentApplicationService
from application.errors import DocumentNotFoundError
from application.retrieval_service import RetrievalApplicationService
from framework.mcp import BaseFastMcpService
from framework.models.interfaces import IEmbeddingGateway
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.retrieval.canonical_retrievers import CanonicalSummaryVectorRetriever, CanonicalVectorRetriever
from schemas.api.contracts import StartRetrievalTaskRequest
from schemas.mcp.retrieval import (
    RetrievalMcpBuildEvidencePackInput,
    RetrievalMcpBuildEvidencePackOutput,
    RetrievalMcpLookupSourceBlock,
    RetrievalMcpLookupSourceInput,
    RetrievalMcpLookupSourceOutput,
    RetrievalMcpLookupSourceTable,
    RetrievalMcpSourceProvenance,
    RetrievalMcpSearchInput,
    RetrievalMcpSearchOutput,
)
from schemas.rag.contracts import RetrievalFilter


class FastMcpRetrievalService(BaseFastMcpService):
    """MVP MCP-сервис retrieval домена с минимальным набором tool-ов."""

    def __init__(
        self,
        retrieval_service: RetrievalApplicationService,
        *,
        canonical_document_service: CanonicalDocumentApplicationService | None = None,
        embedding_gateway: IEmbeddingGateway | None = None,
        vector_store: PgVectorStoreAdapter | None = None,
    ) -> None:
        super().__init__(service_name="retrieval-mcp", version="0.1.0")
        self._retrieval_service = retrieval_service
        self._canonical_document_service = canonical_document_service
        self._embedding_gateway = embedding_gateway
        self._vector_store = vector_store
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = self._register_toolset(
            {
                "build_evidence_pack": self.build_evidence_pack,
                "lookup_source": self.lookup_source,
                "search_blocks": self.search_blocks,
                "search_summaries": self.search_summaries,
            },
            operation_scopes={
                "build_evidence_pack": "action",
            },
        )

    def build_evidence_pack(self, payload: RetrievalMcpBuildEvidencePackInput | dict[str, Any]) -> dict[str, Any]:
        """Запускает retrieval задачу и сразу возвращает собранный evidence pack."""

        if isinstance(payload, dict):
            validated_payload = RetrievalMcpBuildEvidencePackInput.model_validate(payload)
        else:
            validated_payload = payload

        request = StartRetrievalTaskRequest(
            query=validated_payload.query,
            filters=RetrievalFilter(
                project_id=validated_payload.project_id,
                document_types=validated_payload.document_types,
            ),
            task_context=validated_payload.task_context,
        )

        started = self._retrieval_service.start(request)
        status = self._retrieval_service.status(started.task_id)
        evidence = self._retrieval_service.evidence(started.task_id)

        response = RetrievalMcpBuildEvidencePackOutput(
            task_id=started.task_id,
            status=status.status,
            details=status.details,
            evidence_pack=evidence.evidence_pack,
        )
        return response.model_dump(mode="json")

    def search_summaries(self, payload: RetrievalMcpSearchInput | dict[str, Any]) -> dict[str, Any]:
        """Ищет indexed canonical section summaries через pgvector-backed retriever."""

        validated_payload = _validate_search_payload(payload)
        self._ensure_indexed_retrieval_ready()
        retriever = CanonicalSummaryVectorRetriever(
            embedding_gateway=self._embedding_gateway,
            vector_store=self._vector_store,
            doc_ids=validated_payload.canonical_doc_ids or None,
            search_limit=validated_payload.limit,
        )
        candidates = retriever.retrieve(validated_payload.query, _retrieval_filter(validated_payload))
        response = RetrievalMcpSearchOutput(
            query=validated_payload.query,
            candidates=candidates[: validated_payload.limit],
            total_returned=min(len(candidates), validated_payload.limit),
            retrieval_backend="pgvector",
        )
        return response.model_dump(mode="json")

    def search_blocks(self, payload: RetrievalMcpSearchInput | dict[str, Any]) -> dict[str, Any]:
        """Ищет indexed canonical content blocks через pgvector-backed retriever."""

        validated_payload = _validate_search_payload(payload)
        self._ensure_indexed_retrieval_ready()
        retriever = CanonicalVectorRetriever(
            embedding_gateway=self._embedding_gateway,
            vector_store=self._vector_store,
            doc_ids=validated_payload.canonical_doc_ids or None,
            search_limit=validated_payload.limit,
        )
        candidates = retriever.retrieve(validated_payload.query, _retrieval_filter(validated_payload))
        response = RetrievalMcpSearchOutput(
            query=validated_payload.query,
            candidates=candidates[: validated_payload.limit],
            total_returned=min(len(candidates), validated_payload.limit),
            retrieval_backend="pgvector",
        )
        return response.model_dump(mode="json")

    def lookup_source(self, payload: RetrievalMcpLookupSourceInput | dict[str, Any]) -> dict[str, Any]:
        """Возвращает canonical document/source mapping по doc_id/block_id или block_ref."""

        if isinstance(payload, dict):
            validated_payload = RetrievalMcpLookupSourceInput.model_validate(payload)
        else:
            validated_payload = payload

        if self._canonical_document_service is None:
            return RetrievalMcpLookupSourceOutput(
                found=False,
                error="canonical_document_service is not configured",
            ).model_dump(mode="json")

        doc_id = validated_payload.doc_id
        version = validated_payload.version
        block_id = validated_payload.block_id
        block_ref = validated_payload.block_ref
        if block_ref:
            parsed_doc_id, parsed_version, parsed_block_id = _parse_block_ref(block_ref)
            doc_id = doc_id or parsed_doc_id
            version = version or parsed_version
            block_id = block_id or parsed_block_id

        if not doc_id:
            return RetrievalMcpLookupSourceOutput(
                found=False,
                error="doc_id or block_ref is required",
            ).model_dump(mode="json")

        try:
            document = self._canonical_document_service.get_document(doc_id, version=version)
        except DocumentNotFoundError:
            return RetrievalMcpLookupSourceOutput(
                found=False,
                error=f"canonical document {doc_id}{'@' + version if version else ''} not found",
                doc_id=doc_id,
                version=version,
                block_id=block_id,
                block_ref=block_ref,
            ).model_dump(mode="json")

        block_payload: RetrievalMcpLookupSourceBlock | None = None
        table_payload: RetrievalMcpLookupSourceTable | None = None
        source_provenance = RetrievalMcpSourceProvenance(source_kind="document")
        resolved_block_ref = block_ref
        if block_id:
            block = next((item for item in document.content_blocks if item.block_id == block_id), None)
            if block is None:
                return RetrievalMcpLookupSourceOutput(
                    found=False,
                    error=f"canonical block {block_id} not found",
                    doc_id=document.doc_id,
                    version=document.version,
                    block_id=block_id,
                    block_ref=block_ref,
                    source_path=document.source_path,
                    file_type=document.file_type,
                    document_metadata=document.metadata_profile,
                ).model_dump(mode="json")
            resolved_block_ref = resolved_block_ref or _build_block_ref(document.doc_id, document.version, block.block_id)
            source_provenance = _build_source_provenance(document=document, block=block)
            if block.block_type == "table_row":
                table_payload = _build_lookup_table(document=document, block=block)
            block_payload = RetrievalMcpLookupSourceBlock(
                block_id=block.block_id,
                block_ref=resolved_block_ref,
                block_type=block.block_type,
                text=block.text,
                heading_path=list(block.heading_path),
                metadata=dict(block.metadata),
                source_provenance=source_provenance,
            )
        else:
            source_provenance = RetrievalMcpSourceProvenance(
                source_kind="document",
                heading_path=[],
            )

        response = RetrievalMcpLookupSourceOutput(
            found=True,
            doc_id=document.doc_id,
            version=document.version,
            block_id=block_id,
            block_ref=resolved_block_ref,
            source_path=document.source_path,
            file_type=document.file_type,
            document_metadata={
                **document.metadata_profile,
                "quality_flags": document.quality_flags,
                "parser_quality": document.parser_quality.model_dump(mode="json"),
            },
            source_provenance=source_provenance,
            block=block_payload,
            table=table_payload,
        )
        return response.model_dump(mode="json")

    def _ensure_indexed_retrieval_ready(self) -> None:
        if self._embedding_gateway is None or self._vector_store is None:
            raise RuntimeError("indexed canonical retrieval requires embedding_gateway and vector_store")


def create_fastmcp_retrieval_server(service: FastMcpRetrievalService) -> Any:
    """Создает FastMCP runtime-сервер для retrieval service.

    Импорт FastMCP выполняется лениво, чтобы backend-контур не зависел от пакета,
    если MCP-сервис не запускается в текущем окружении.
    """

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - зависит от внешнего пакета в runtime.
        raise RuntimeError(
            "Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса."
        ) from exc

    service.register_tools()
    server = FastMCP("retrieval-mcp")

    @server.tool()
    def build_evidence_pack(
        query: str,
        project_id: str = "p1",
        document_types: list[str] | None = None,
        task_context: dict | None = None,
    ) -> dict[str, Any]:
        """MCP tool: build_evidence_pack."""

        payload = RetrievalMcpBuildEvidencePackInput(
            query=query,
            project_id=project_id,
            document_types=document_types or [
                "requirements",
                "methodology",
                "security",
                "operations",
                "governance",
            ],
            task_context=task_context or {},
        )
        return service.build_evidence_pack(payload)

    @server.tool()
    def search_summaries(
        query: str,
        project_id: str = "p1",
        document_types: list[str] | None = None,
        tags: list[str] | None = None,
        canonical_doc_ids: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """MCP tool: search_summaries."""

        payload = RetrievalMcpSearchInput(
            query=query,
            project_id=project_id,
            document_types=document_types or [],
            tags=tags or [],
            canonical_doc_ids=canonical_doc_ids or [],
            limit=limit,
        )
        return service.search_summaries(payload)

    @server.tool()
    def search_blocks(
        query: str,
        project_id: str = "p1",
        document_types: list[str] | None = None,
        tags: list[str] | None = None,
        canonical_doc_ids: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """MCP tool: search_blocks."""

        payload = RetrievalMcpSearchInput(
            query=query,
            project_id=project_id,
            document_types=document_types or [],
            tags=tags or [],
            canonical_doc_ids=canonical_doc_ids or [],
            limit=limit,
        )
        return service.search_blocks(payload)

    @server.tool()
    def lookup_source(
        doc_id: str | None = None,
        version: str | None = None,
        block_id: str | None = None,
        block_ref: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: lookup_source."""

        payload = RetrievalMcpLookupSourceInput(
            doc_id=doc_id,
            version=version,
            block_id=block_id,
            block_ref=block_ref,
        )
        return service.lookup_source(payload)

    return server


def _validate_search_payload(payload: RetrievalMcpSearchInput | dict[str, Any]) -> RetrievalMcpSearchInput:
    if isinstance(payload, dict):
        return RetrievalMcpSearchInput.model_validate(payload)
    return payload


def _retrieval_filter(payload: RetrievalMcpSearchInput) -> RetrievalFilter:
    return RetrievalFilter(
        project_id=payload.project_id,
        document_types=payload.document_types,
        tags=payload.tags,
    )


def _parse_block_ref(block_ref: str) -> tuple[str | None, str | None, str | None]:
    parts = block_ref.split(":", 2)
    if len(parts) != 3:
        return None, None, None
    return parts[0] or None, parts[1] or None, parts[2] or None


def _build_block_ref(doc_id: str, version: str, block_id: str) -> str:
    return f"{doc_id}:{version}:{block_id}"


def _build_source_provenance(
    *,
    document: Any,
    block: Any,
) -> RetrievalMcpSourceProvenance:
    page_number = block.metadata.get("page_number") if isinstance(block.metadata.get("page_number"), int) else None
    reading_order_index = (
        block.metadata.get("reading_order_index") if isinstance(block.metadata.get("reading_order_index"), int) else None
    )
    layout_kind = str(block.metadata.get("layout_kind", "") or "").strip() or None
    bbox = _normalize_bbox(block.metadata.get("bbox"))
    layout_source = str(block.metadata.get("layout_source", "") or "").strip() or None
    if block.block_type != "table_row":
        source_kind = str(block.metadata.get("source_kind", "") or "").strip() or "content_block"
        return RetrievalMcpSourceProvenance(
            source_kind=source_kind,
            heading_path=list(block.heading_path),
            section_title=block.heading_path[-1] if block.heading_path else None,
            page_number=page_number,
            reading_order_index=reading_order_index,
            layout_kind=layout_kind,
            bbox=bbox,
            layout_source=layout_source,
        )

    table = _find_table(document, str(block.metadata.get("table_id", "") or "").strip())
    row_index = block.metadata.get("row_index") if isinstance(block.metadata.get("row_index"), int) else None
    row_values = _resolve_table_row_values(table=table, row_index=row_index)
    return RetrievalMcpSourceProvenance(
        source_kind="table_row",
        heading_path=list(block.heading_path),
        section_title=block.heading_path[-1] if block.heading_path else None,
        table_id=str(block.metadata.get("table_id", "") or "") or None,
        table_title=table.title if table is not None else (block.heading_path[-1] if block.heading_path else None),
        table_columns=list(table.columns) if table is not None else [],
        row_index=row_index,
        row_values=row_values,
        page_number=page_number,
        reading_order_index=reading_order_index,
        layout_kind=layout_kind,
        bbox=bbox,
        layout_source=layout_source,
    )


def _build_lookup_table(*, document: Any, block: Any) -> RetrievalMcpLookupSourceTable | None:
    table_id = str(block.metadata.get("table_id", "") or "").strip()
    if not table_id:
        return None
    table = _find_table(document, table_id)
    row_index = block.metadata.get("row_index") if isinstance(block.metadata.get("row_index"), int) else None
    if table is None:
        return RetrievalMcpLookupSourceTable(
            table_id=table_id,
            title=block.heading_path[-1] if block.heading_path else None,
            columns=[],
            row_index=row_index,
            row_values={},
            metadata={},
        )
    return RetrievalMcpLookupSourceTable(
        table_id=table.table_id,
        title=table.title,
        columns=list(table.columns),
        row_index=row_index,
        row_values=_resolve_table_row_values(table=table, row_index=row_index),
        metadata=dict(table.metadata),
    )


def _find_table(document: Any, table_id: str) -> Any | None:
    if not table_id:
        return None
    return next((item for item in document.extracted_tables if item.table_id == table_id), None)


def _resolve_table_row_values(*, table: Any | None, row_index: int | None) -> dict[str, Any]:
    if table is None or row_index is None or row_index < 1 or row_index > len(table.rows):
        return {}
    return dict(table.rows[row_index - 1])


def _normalize_bbox(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        return []
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return []
