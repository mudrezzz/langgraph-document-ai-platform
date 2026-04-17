from __future__ import annotations

from framework.rag.interfaces import IEvidenceBuilder
from schemas.rag.contracts import EvidencePack, RerankedBlock


class EvidenceBuilder(IEvidenceBuilder):
    """Базовый сборщик evidence pack из reranked-блоков."""

    def build(self, reranked_blocks: list[RerankedBlock]) -> EvidencePack:
        return EvidencePack(
            selected_sources=[block.source for block in reranked_blocks],
            selected_blocks=reranked_blocks,
            unresolved_gaps=[],
            confidence_notes=[],
        )