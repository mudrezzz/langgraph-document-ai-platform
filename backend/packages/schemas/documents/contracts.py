from __future__ import annotations

from pydantic import BaseModel, Field


class CanonicalDocument(BaseModel):
    """Каноническое представление исходного документа."""

    doc_id: str
    source_path: str
    version: str
    file_type: str
    metadata_profile: dict = Field(default_factory=dict)
    structure_tree: dict = Field(default_factory=dict)
    content_blocks: list[dict] = Field(default_factory=list)
    extracted_tables: list[dict] = Field(default_factory=list)
    section_summaries: list[dict] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)


class TemplateSpec(BaseModel):
    """Формализованная спецификация шаблона документа."""

    template_id: str
    version: str
    sections: list[dict] = Field(default_factory=list)
    validation_rules: list[dict] = Field(default_factory=list)


class SectionDigest(BaseModel):
    """Краткий семантический digest раздела."""

    entities: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    covered_requirements: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)
