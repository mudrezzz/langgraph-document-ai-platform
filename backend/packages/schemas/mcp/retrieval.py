from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.rag.contracts import EvidencePack
from schemas.rag.contracts import RetrievedBlock


class RetrievalMcpBuildEvidencePackInput(BaseModel):
    """Контракт входа MCP tool для запуска retrieval и получения evidence pack."""

    query: str
    project_id: str | None = "p1"
    document_types: list[str] = Field(
        default_factory=lambda: ["requirements", "methodology", "security", "operations", "governance"]
    )
    task_context: dict = Field(default_factory=dict)


class RetrievalMcpBuildEvidencePackOutput(BaseModel):
    """Контракт ответа MCP tool по результату retrieval запуска."""

    task_id: str
    status: str
    details: dict = Field(default_factory=dict)
    evidence_pack: EvidencePack


class RetrievalMcpSearchInput(BaseModel):
    """Контракт входа MCP search tools для indexed canonical corpus."""

    query: str
    project_id: str | None = "p1"
    document_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    canonical_doc_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)


class RetrievalMcpSearchOutput(BaseModel):
    """Контракт ответа MCP search tools."""

    query: str
    candidates: list[RetrievedBlock] = Field(default_factory=list)
    total_returned: int
    retrieval_backend: str = "pgvector"


class RetrievalMcpSourceProvenance(BaseModel):
    """Нормализованная provenance-сводка для source/block lookup."""

    source_kind: str = "document"
    heading_path: list[str] = Field(default_factory=list)
    section_title: str | None = None
    table_id: str | None = None
    table_title: str | None = None
    table_columns: list[str] = Field(default_factory=list)
    row_index: int | None = None
    row_values: dict = Field(default_factory=dict)
    page_number: int | None = None
    reading_order_index: int | None = None
    layout_kind: str | None = None
    bbox: list[float] = Field(default_factory=list)
    layout_source: str | None = None
    source_block_ids: list[str] = Field(default_factory=list)


class RetrievalMcpLookupSourceBlock(BaseModel):
    """Typed block payload для lookup_source ответа."""

    block_id: str
    block_ref: str
    block_type: str
    text: str
    heading_path: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    source_provenance: RetrievalMcpSourceProvenance | None = None


class RetrievalMcpLookupSourceTable(BaseModel):
    """Typed table payload для lookup_source ответа."""

    table_id: str
    title: str | None = None
    columns: list[str] = Field(default_factory=list)
    row_index: int | None = None
    row_values: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class RetrievalMcpLookupSourceInput(BaseModel):
    """Контракт входа MCP lookup_source tool."""

    doc_id: str | None = None
    version: str | None = None
    block_id: str | None = None
    block_ref: str | None = None


class RetrievalMcpLookupSourceOutput(BaseModel):
    """Контракт ответа MCP lookup_source tool."""

    found: bool
    error: str | None = None
    doc_id: str | None = None
    version: str | None = None
    block_id: str | None = None
    block_ref: str | None = None
    source_path: str | None = None
    file_type: str | None = None
    document_metadata: dict = Field(default_factory=dict)
    source_provenance: RetrievalMcpSourceProvenance | None = None
    block: RetrievalMcpLookupSourceBlock | None = None
    table: RetrievalMcpLookupSourceTable | None = None
