from __future__ import annotations

from domain_authoring import (
    DocumentAssembler,
    OutlinePlanner,
    ResearchSummaryBuilder,
    SectionReviewService,
    WriterDraftService,
)


def build_domain_authoring_services() -> tuple[
    OutlinePlanner,
    SectionReviewService,
    DocumentAssembler,
    ResearchSummaryBuilder,
    WriterDraftService,
]:
    """Builds the current domain_authoring service set for application wiring."""

    return (
        OutlinePlanner(),
        SectionReviewService(),
        DocumentAssembler(),
        ResearchSummaryBuilder(),
        WriterDraftService(),
    )
