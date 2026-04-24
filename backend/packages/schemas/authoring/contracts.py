from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.documents.contracts import SectionDigest
from schemas.rag.contracts import EvidencePack


class SectionContract(BaseModel):
    """Typed contract for one authoring section."""

    section_id: str
    title: str
    objective: str
    required_keywords: list[str] = Field(default_factory=list)
    preferred_source_refs: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SectionPacket(BaseModel):
    """Typed packet passed to a section-oriented authoring step."""

    section_contract: SectionContract
    query: str
    project_context: dict[str, Any] = Field(default_factory=dict)
    evidence_pack: EvidencePack
    research_summary: str | None = None
    relevant_state: dict[str, Any] = Field(default_factory=dict)


class SectionArtifact(BaseModel):
    """Deterministic section draft artifact plus typed digest."""

    section_id: str
    title: str
    content: str
    digest: SectionDigest = Field(default_factory=SectionDigest)
    source_refs: list[dict[str, str]] = Field(default_factory=list)
    review_status: str = "not_reviewed"
    metadata: dict[str, Any] = Field(default_factory=dict)
