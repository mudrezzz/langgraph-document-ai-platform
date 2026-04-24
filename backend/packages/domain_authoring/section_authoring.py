from __future__ import annotations

from typing import Any

from schemas.authoring.contracts import SectionArtifact, SectionContract, SectionPacket
from schemas.documents.contracts import SectionDigest
from schemas.rag.contracts import RerankedBlock


class SectionAuthoringService:
    """Builds deterministic section drafts and digests from typed section packets."""

    def author_sections(
        self,
        *,
        contracts: list[SectionContract],
        query: str,
        project_context: dict[str, Any],
        evidence_pack,
        research_summary: str | None = None,
        relevant_state: dict[str, Any] | None = None,
    ) -> list[SectionArtifact]:
        state = dict(relevant_state or {})
        return [
            self.author_section(
                SectionPacket(
                    section_contract=contract,
                    query=query,
                    project_context=project_context,
                    evidence_pack=evidence_pack,
                    research_summary=research_summary,
                    relevant_state=state,
                )
            )
            for contract in contracts
        ]

    def author_section(self, packet: SectionPacket) -> SectionArtifact:
        contract = packet.section_contract
        relevant_blocks = self._select_relevant_blocks(packet)
        source_refs = self._build_source_refs(packet=packet, relevant_blocks=relevant_blocks)

        lines = [f"### {contract.title}"]
        if contract.objective.strip():
            lines.extend(["", f"Objective: {contract.objective.strip()}"])
        if packet.research_summary:
            lines.extend(["", f"Research context: {packet.research_summary.strip()[:180]}"])
        lines.append("")
        lines.append("Evidence highlights:")

        if relevant_blocks:
            for block in relevant_blocks[:4]:
                snippet = block.text.strip()
                if len(snippet) > 220:
                    snippet = snippet[:217] + "..."
                lines.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")
        else:
            lines.append("- No direct evidence matched this section contract; manual follow-up may be required.")

        digest = self._build_digest(contract=contract, relevant_blocks=relevant_blocks, source_refs=source_refs)
        return SectionArtifact(
            section_id=contract.section_id,
            title=contract.title,
            content="\n".join(lines),
            digest=digest,
            source_refs=source_refs,
            review_status=str(contract.metadata.get("review_status", "not_reviewed")),
            metadata={
                "matched_blocks": len(relevant_blocks),
                "required_keywords": list(contract.required_keywords),
                "project_context_keys": sorted(packet.project_context.keys()),
            },
        )

    def _select_relevant_blocks(self, packet: SectionPacket) -> list[RerankedBlock]:
        preferred_keys = {
            (item.get("doc_id", ""), item.get("version", ""), item.get("block_id", ""))
            for item in packet.section_contract.preferred_source_refs
        }
        keyword_blocks: list[RerankedBlock] = []
        preferred_blocks: list[RerankedBlock] = []

        for block in packet.evidence_pack.selected_blocks:
            key = (block.source.doc_id, block.source.version, block.source.block_id)
            if key in preferred_keys:
                preferred_blocks.append(block)
                continue
            lowered = block.text.lower()
            if packet.section_contract.required_keywords and any(
                keyword in lowered for keyword in packet.section_contract.required_keywords
            ):
                keyword_blocks.append(block)

        if preferred_blocks:
            return preferred_blocks[:4]
        if keyword_blocks:
            return keyword_blocks[:4]
        return packet.evidence_pack.selected_blocks[:3]

    def _build_source_refs(
        self,
        *,
        packet: SectionPacket,
        relevant_blocks: list[RerankedBlock],
    ) -> list[dict[str, str]]:
        if relevant_blocks:
            deduped: list[dict[str, str]] = []
            seen: set[tuple[str, str, str]] = set()
            for block in relevant_blocks:
                key = (block.source.doc_id, block.source.version, block.source.block_id)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(
                    {
                        "doc_id": block.source.doc_id,
                        "version": block.source.version,
                        "block_id": block.source.block_id,
                    }
                )
            return deduped
        return list(packet.section_contract.preferred_source_refs)

    def _build_digest(
        self,
        *,
        contract: SectionContract,
        relevant_blocks: list[RerankedBlock],
        source_refs: list[dict[str, str]],
    ) -> SectionDigest:
        entities = sorted({block.source.doc_id for block in relevant_blocks})
        decisions: list[str] = []
        constraints: list[str] = []
        open_questions: list[str] = []

        for block in relevant_blocks[:4]:
            lowered = block.text.lower()
            snippet = block.text.strip()
            if len(snippet) > 140:
                snippet = snippet[:137] + "..."
            if any(word in lowered for word in ("approve", "approval", "go", "no-go", "decision")):
                decisions.append(snippet)
            if any(word in lowered for word in ("risk", "block", "pending", "critical", "constraint")):
                constraints.append(snippet)

        if not relevant_blocks:
            open_questions.append(f"Section {contract.section_id} needs additional evidence or reviewer input.")

        return SectionDigest(
            entities=entities,
            decisions=decisions[:3],
            assumptions=[],
            constraints=constraints[:3],
            covered_requirements=entities,
            open_questions=open_questions,
            source_refs=source_refs,
        )
