from __future__ import annotations

from domain_authoring import (
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
        ResearchSummaryBuilder(),
        WriterDraftService(),
        SectionContractBuilder(),
        SectionAuthoringService(),
    )
