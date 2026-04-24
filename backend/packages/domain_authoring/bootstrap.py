from __future__ import annotations

from domain_authoring import DocumentAssembler, OutlinePlanner, SectionReviewService


def build_domain_authoring_services() -> tuple[OutlinePlanner, SectionReviewService, DocumentAssembler]:
    """Builds the minimal domain_authoring service set for application wiring."""

    return OutlinePlanner(), SectionReviewService(), DocumentAssembler()
