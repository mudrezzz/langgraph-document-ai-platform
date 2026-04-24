from __future__ import annotations

from domain_authoring import (
    ArtifactExporter,
    DocumentAssembler,
    OutlinePlanner,
    ResearchSummaryBuilder,
    SectionContractBuilder,
    SectionAuthoringService,
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
]:
    """Builds the current domain_authoring service set for application wiring."""

    return (
        OutlinePlanner(),
        SectionReviewService(),
        DocumentAssembler(),
        ArtifactExporter(),
        ResearchSummaryBuilder(),
        WriterDraftService(),
        SectionContractBuilder(),
        SectionAuthoringService(),
    )
