from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.rag.contracts import EvidencePack


class RetrievalMcpBuildEvidencePackInput(BaseModel):
    """Контракт входа MCP tool для запуска retrieval и получения evidence pack."""

    query: str
    project_id: str | None = "p1"
    document_types: list[str] = Field(
        default_factory=lambda: ["requirements", "methodology", "security", "operations", "governance"]
    )
    task_context: dict = Field(default_factory=dict)


class RetrievalMcpBuildEvidencePackOutput(BaseModel):
    """Контракт ответа MCP tool по результату retrieval запуска."""

    task_id: str
    status: str
    details: dict = Field(default_factory=dict)
    evidence_pack: EvidencePack
