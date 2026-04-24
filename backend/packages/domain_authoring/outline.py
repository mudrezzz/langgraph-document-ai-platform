from __future__ import annotations

from typing import Any

from schemas.rag.contracts import EvidencePack, SourceRef


class OutlinePlanner:
    """Domain service for section outline and traceability planning."""

    def build_section_traceability(
        self,
        *,
        evidence_pack: EvidencePack,
        review_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        unique_sources = self.dedup_source_refs(evidence_pack.selected_sources)
        risk_sources = self.select_sources_by_keywords(
            evidence_pack=evidence_pack,
            keywords=("risk", "block", "critical", "pending", "no-go"),
            limit=3,
        )
        approval_sources = self.select_sources_by_keywords(
            evidence_pack=evidence_pack,
            keywords=("approval", "governance", "security", "policy", "pending"),
            limit=3,
        )

        return [
            {
                "section_id": "risk_assessment",
                "title": "Risk Assessment",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": risk_sources or unique_sources[:2],
            },
            {
                "section_id": "pending_approvals",
                "title": "Pending Approvals",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": approval_sources or unique_sources[:2],
            },
            {
                "section_id": "final_recommendation",
                "title": "Final Recommendation",
                "review_status": review_result.get("status", "not_reviewed"),
                "source_refs": unique_sources[:3],
            },
            {
                "section_id": "evidence_register",
                "title": "Evidence Register",
                "review_status": "informational",
                "source_refs": unique_sources,
            },
        ]

    def build_traceability(
        self,
        *,
        retrieval_task_id: str,
        evidence_pack: EvidencePack,
        section_traceability: list[dict[str, Any]],
        workflow_steps: list[Any],
    ) -> dict[str, Any]:
        return {
            "retrieval_task_id": retrieval_task_id,
            "source_refs": self.dedup_source_refs(evidence_pack.selected_sources),
            "sections": section_traceability,
            "workflow_steps": [self._normalize_step(step) for step in workflow_steps],
        }

    def collect_source_refs_from_sections(self, sections: list[dict[str, Any]]) -> list[SourceRef]:
        refs: list[SourceRef] = []
        seen: set[tuple[str, str, str]] = set()
        for section in sections:
            for item in section.get("source_refs", []):
                doc_id = str(item.get("doc_id", ""))
                version = str(item.get("version", ""))
                block_id = str(item.get("block_id", ""))
                key = (doc_id, version, block_id)
                if key in seen:
                    continue
                seen.add(key)
                refs.append(SourceRef(doc_id=doc_id, version=version, block_id=block_id))
        return refs

    def dedup_source_refs(self, sources: list[SourceRef]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for source in sources:
            key = (source.doc_id, source.version, source.block_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "doc_id": source.doc_id,
                    "version": source.version,
                    "block_id": source.block_id,
                }
            )
        return deduped

    def select_sources_by_keywords(
        self,
        *,
        evidence_pack: EvidencePack,
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for block in evidence_pack.selected_blocks:
            lowered = block.text.lower()
            if not any(keyword in lowered for keyword in keywords):
                continue
            key = (block.source.doc_id, block.source.version, block.source.block_id)
            if key in seen:
                continue
            seen.add(key)
            selected.append(
                {
                    "doc_id": block.source.doc_id,
                    "version": block.source.version,
                    "block_id": block.source.block_id,
                }
            )
            if len(selected) >= limit:
                break
        return selected

    def _normalize_step(self, step: Any) -> dict[str, Any]:
        if hasattr(step, "model_dump"):
            return dict(step.model_dump(mode="json"))
        if isinstance(step, dict):
            return dict(step)
        return {"value": str(step)}
