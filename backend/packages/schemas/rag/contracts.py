from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalFilter(BaseModel):
    """Фильтры retrieval по метаданным и контексту задачи."""

    project_id: str | None = None
    document_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SourceRef(BaseModel):
    """Ссылка на источник в knowledge corpus."""

    doc_id: str
    version: str
    block_id: str


class RetrievedBlock(BaseModel):
    """Найденный блок до rerank."""

    text: str
    source: SourceRef
    score: float
    metadata: dict = Field(default_factory=dict)


class RerankedBlock(BaseModel):
    """Блок после rerank-переоценки."""

    text: str
    source: SourceRef
    score: float
    metadata: dict = Field(default_factory=dict)


class EvidencePack(BaseModel):
    """Стандартизованный артефакт между retrieval и authoring."""

    selected_sources: list[SourceRef] = Field(default_factory=list)
    selected_blocks: list[RerankedBlock] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class RetrievalTrace(BaseModel):
    """Трассировка иерархического retrieval для workflow state."""

    summary_candidates: list[RetrievedBlock] = Field(default_factory=list)
    detail_candidates: list[RetrievedBlock] = Field(default_factory=list)
    reranked_blocks: list[RerankedBlock] = Field(default_factory=list)
    evidence_pack: EvidencePack