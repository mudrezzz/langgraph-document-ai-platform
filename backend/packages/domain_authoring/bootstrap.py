from __future__ import annotations

from domain_authoring import (
    ArtifactExporter,
    DocumentAssemblyWorkflow,
    DocumentAssembler,
    OutlinePlanner,
    ResearchSummaryBuilder,
    SectionAuthoringService,
    SectionAuthoringWorkflow,
    SectionContractBuilder,
    SectionReviewService,
    WriterDraftService,
)


def build_domain_authoring_services() -> tuple[
    OutlinePlanner,
    SectionReviewService,
    DocumentAssembler,
    ArtifactExporter,
    ResearchSummaryBuilder,
    WriterDraftService,
    SectionContractBuilder,
    SectionAuthoringService,
    SectionAuthoringWorkflow,
    DocumentAssemblyWorkflow,
]:
    """Builds the current domain_authoring service set for application wiring."""

    outline_planner = OutlinePlanner()
    section_review_service = SectionReviewService()
    document_assembler = DocumentAssembler()
    artifact_exporter = ArtifactExporter()
    research_summary_builder = ResearchSummaryBuilder()
    writer_draft_service = WriterDraftService()
    section_contract_builder = SectionContractBuilder()
    section_authoring_service = SectionAuthoringService()
    section_authoring_workflow = SectionAuthoringWorkflow(
        section_authoring_service=section_authoring_service,
        section_review_service=section_review_service,
    )
    document_assembly_workflow = DocumentAssemblyWorkflow(
        document_assembler=document_assembler,
        artifact_exporter=artifact_exporter,
    )

    return (
        outline_planner,
        section_review_service,
        document_assembler,
        artifact_exporter,
        research_summary_builder,
        writer_draft_service,
        section_contract_builder,
        section_authoring_service,
        section_authoring_workflow,
        document_assembly_workflow,
    )
