from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CanonicalStructureNode(BaseModel):
    """Узел структурного дерева документа."""

    node_id: str
    title: str
    level: int = 0
    block_ids: list[str] = Field(default_factory=list)
    children: list["CanonicalStructureNode"] = Field(default_factory=list)


class CanonicalContentBlock(BaseModel):
    """Нормализованный semantic block исходного документа."""

    block_id: str
    block_type: str = "paragraph"
    text: str
    heading_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalTable(BaseModel):
    """Нормализованная табличная структура документа."""

    table_id: str
    title: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalSectionSummary(BaseModel):
    """Краткое описание секции canonical document."""

    section_id: str
    title: str
    summary: str
    source_block_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParserQualityIssue(BaseModel):
    """Диагностическая запись качества parser extraction."""

    code: str
    severity: Literal["info", "warning", "blocking"] = "warning"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParserQualitySummary(BaseModel):
    """Структурированная сводка parser quality для canonical document."""

    parser_family: str = "text"
    extraction_mode: str = "text"
    pages_total: int | None = None
    blocks_total: int = 0
    sections_total: int = 0
    headings_total: int = 0
    lists_total: int = 0
    tables_total: int = 0
    issues: list[ParserQualityIssue] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class CanonicalDocument(BaseModel):
    """Каноническое представление исходного документа."""

    doc_id: str
    source_path: str
    version: str
    file_type: str
    metadata_profile: dict[str, Any] = Field(default_factory=dict)
    structure_tree: CanonicalStructureNode | dict[str, Any] = Field(default_factory=dict)
    content_blocks: list[CanonicalContentBlock] = Field(default_factory=list)
    extracted_tables: list[CanonicalTable] = Field(default_factory=list)
    section_summaries: list[CanonicalSectionSummary] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    parser_quality: ParserQualitySummary = Field(default_factory=ParserQualitySummary)


class TemplateSpec(BaseModel):
    """Формализованная спецификация шаблона документа."""

    template_id: str
    version: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    assembly_rules: list[dict[str, Any]] = Field(default_factory=list)


class SectionDigest(BaseModel):
    """Краткий семантический digest раздела."""

    entities: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    covered_requirements: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
