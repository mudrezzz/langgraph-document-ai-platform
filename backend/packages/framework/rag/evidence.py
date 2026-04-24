from __future__ import annotations

from dataclasses import dataclass, field

from framework.rag.interfaces import IEvidenceBuilder
from schemas.rag.contracts import EvidencePack, RerankedBlock


@dataclass(frozen=True)
class RetrievalQualityPolicy:
    """Quality gates applied to a built evidence pack."""

    min_evidence_count: int = 1
    min_confidence_score: float = 0.0
    required_document_types: tuple[str, ...] = field(default_factory=tuple)


class EvidenceBuilder(IEvidenceBuilder):
    """Базовый сборщик evidence pack из reranked-блоков."""

    def __init__(self, quality_policy: RetrievalQualityPolicy | None = None) -> None:
        self._quality_policy = quality_policy or RetrievalQualityPolicy()

    def build(self, reranked_blocks: list[RerankedBlock]) -> EvidencePack:
        selected_sources = [block.source for block in reranked_blocks]
        unresolved_gaps, confidence_notes = self._evaluate_quality(reranked_blocks)
        return EvidencePack(
            selected_sources=selected_sources,
            selected_blocks=reranked_blocks,
            unresolved_gaps=unresolved_gaps,
            confidence_notes=confidence_notes,
        )

    def _evaluate_quality(self, blocks: list[RerankedBlock]) -> tuple[list[str], list[str]]:
        policy = self._quality_policy
        unresolved_gaps: list[str] = []
        confidence_notes: list[str] = []

        if len(blocks) < policy.min_evidence_count:
            unresolved_gaps.append(
                f"low_evidence_count: selected {len(blocks)} blocks, required {policy.min_evidence_count}"
            )

        confidence = _top_confidence(blocks)
        if confidence < policy.min_confidence_score:
            unresolved_gaps.append(
                f"low_confidence: top confidence {confidence:.3f}, required {policy.min_confidence_score:.3f}"
            )
        confidence_notes.append(f"top_confidence={confidence:.3f}")

        missing_document_types = [
            document_type
            for document_type in policy.required_document_types
            if document_type not in _document_types(blocks)
        ]
        if missing_document_types:
            unresolved_gaps.append(
                "missing_required_document_types: " + ", ".join(sorted(missing_document_types))
            )

        missing_source_refs = [
            block
            for block in blocks
            if not block.source.doc_id.strip()
            or not block.source.version.strip()
            or not block.source.block_id.strip()
        ]
        if missing_source_refs:
            unresolved_gaps.append(f"missing_source_refs: {len(missing_source_refs)} blocks")

        return unresolved_gaps, confidence_notes


def _top_confidence(blocks: list[RerankedBlock]) -> float:
    if not blocks:
        return 0.0
    top_scores = sorted((block.score for block in blocks), reverse=True)[:3]
    return sum(top_scores) / float(len(top_scores))


def _document_types(blocks: list[RerankedBlock]) -> set[str]:
    return {
        str(block.metadata.get("document_type", "")).strip()
        for block in blocks
        if str(block.metadata.get("document_type", "")).strip()
    }
