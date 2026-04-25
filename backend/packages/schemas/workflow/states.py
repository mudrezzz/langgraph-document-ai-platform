from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.authoring.contracts import SectionArtifact, SectionContract
from schemas.documents.contracts import CanonicalDocument
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
    query: str = ""
    section_contract: SectionContract | None = None
    project_context: dict = Field(default_factory=dict)
    evidence_pack: EvidencePack | None = None
    research_summary: str | None = None
    draft: str | None = None
    review_result: dict | None = None
    human_feedback: dict | None = None
    iteration_count: int = 0
    final_section_artifact: SectionArtifact | None = None


class AssemblyWorkflowState(BaseModel):
    """Состояние детерминированной сборки итогового документа."""

    task_context: dict = Field(default_factory=dict)
    query: str = ""
    artifact_type: str = "release_report"
    artifact_title: str | None = None
    artifact_format: str = "markdown"
    workflow_mode: str = "multi_step"
    research_summary: str | None = None
    writer_draft: str | None = None
    review_result: dict = Field(default_factory=dict)
    template_spec: dict = Field(default_factory=dict)
    section_artifacts: list[SectionArtifact] = Field(default_factory=list)
    section_traceability: list[dict] = Field(default_factory=list)
    chapter_summaries: list[str] = Field(default_factory=list)
    consistency_report: dict | None = None
    assembled_content: str | None = None
    final_document: dict | None = None
    export_result: dict | None = None


class KnowledgeIndexingState(BaseModel):
    """Состояние workflow canonical ingestion/indexing."""

    task_context: dict = Field(default_factory=dict)
    source_paths: list[str] = Field(default_factory=list)
    documents: list[CanonicalDocument] = Field(default_factory=list)
    indexed_doc_ids: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    error_message: str | None = None


class AuthoringTaskState(BaseModel):
    """Состояние authoring task поверх retrieval + artifact writer MVP."""

    task_context: dict = Field(default_factory=dict)
    query: str
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    retrieval_task_id: str | None = None
    artifact_id: str | None = None
    artifact_type: str = "release_report"
    artifact_title: str | None = None
    artifact_format: str = "markdown"
    draft_strategy: str = "auto"
    workflow_mode: str = "multi_step"
    hitl_required: bool = False
    current_step: str | None = None
    steps_summary: list[dict] = Field(default_factory=list)
    research_summary: str | None = None
    draft: str | None = None
    review_result: dict = Field(default_factory=dict)
    hitl_status: str | None = None
    hitl_iteration: int = 1
    hitl_max_iterations: int = 1
    hitl_deadline_at: str | None = None
    hitl_pending_action_id: str | None = None
    hitl_actions: list[dict] = Field(default_factory=list)
    template_spec: dict = Field(default_factory=dict)
    section_contracts: list[SectionContract] = Field(default_factory=list)
    section_artifacts: list[SectionArtifact] = Field(default_factory=list)
    section_traceability: list[dict] = Field(default_factory=list)
    hitl_phase: str | None = None
    draft_generation_mode: str = "deterministic"
    draft_generation_metadata: dict = Field(default_factory=dict)
    traceability: dict = Field(default_factory=dict)
    error_message: str | None = None
