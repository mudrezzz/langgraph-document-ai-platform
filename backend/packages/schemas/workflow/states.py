from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.rag.contracts import EvidencePack, RetrievalFilter, RerankedBlock, RetrievedBlock


class RetrievalWorkflowState(BaseModel):
    """Состояние workflow построения evidence pack."""

    task_context: dict = Field(default_factory=dict)
    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    selected_summaries: list[RetrievedBlock] = Field(default_factory=list)
    selected_blocks: list[RetrievedBlock] = Field(default_factory=list)
    reranked_blocks: list[RerankedBlock] = Field(default_factory=list)
    evidence_pack: EvidencePack | None = None
    confidence: float | None = None
    unresolved_gaps: list[str] = Field(default_factory=list)


class SectionAuthoringState(BaseModel):
    """Состояние workflow генерации одного раздела."""

    task_context: dict = Field(default_factory=dict)
    section_contract: dict = Field(default_factory=dict)
    project_context: dict = Field(default_factory=dict)
    evidence_pack: EvidencePack | None = None
    research_summary: str | None = None
    draft: str | None = None
    review_result: dict | None = None
    human_feedback: dict | None = None
    iteration_count: int = 0
    final_section_artifact: dict | None = None


class AssemblyWorkflowState(BaseModel):
    """Состояние детерминированной сборки итогового документа."""

    template_spec: dict = Field(default_factory=dict)
    section_artifacts: list[dict] = Field(default_factory=list)
    chapter_summaries: list[str] = Field(default_factory=list)
    consistency_report: dict | None = None
    final_document: dict | None = None
    export_result: dict | None = None
