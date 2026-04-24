from __future__ import annotations

from schemas.rag.contracts import EvidencePack


class WriterDraftService:
    """Domain service for writer draft and LLM prompt composition."""

    def build_deterministic_draft(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        lines = [
            "## Writer Draft",
            "",
            "### Intent",
            query.strip(),
            "",
            "### Research Digest",
            research_summary,
            "",
            "### Risk Signals",
        ]

        risk_keywords = ("risk", "block", "pending", "fail", "critical", "approval")
        risk_blocks: list[str] = []
        for block in evidence_pack.selected_blocks[:10]:
            lowered = block.text.lower()
            if any(keyword in lowered for keyword in risk_keywords):
                snippet = block.text.strip()
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                risk_blocks.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")

        if risk_blocks:
            lines.extend(risk_blocks[:5])
        else:
            lines.append("- Явные risk-signal блоки не найдены, нужна ручная проверка.")

        lines.extend(
            [
                "",
                "### Preliminary Recommendation",
                "Decision pending reviewer validation.",
            ]
        )
        return "\n".join(lines)

    def build_llm_prompt(self, *, query: str, evidence_pack: EvidencePack, research_summary: str) -> str:
        lines = [
            "Подготовь writer-черновик release readiness в markdown.",
            "",
            "Структура:",
            "1. Risk Assessment.",
            "2. Pending Approvals.",
            "3. Preliminary Recommendation.",
            "4. Evidence Sources.",
            "",
            "Важно: используй только evidence и research summary, не выдумывай факты.",
            "",
            "Запрос:",
            query.strip(),
            "",
            "Research summary:",
            research_summary,
            "",
            "Evidence blocks:",
        ]

        for block in evidence_pack.selected_blocks[:10]:
            snippet = block.text.strip()
            if len(snippet) > 500:
                snippet = snippet[:497] + "..."
            lines.append(f"- [{block.source.doc_id}/{block.source.version}/{block.source.block_id}] {snippet}")

        if not evidence_pack.selected_blocks:
            lines.append("- evidence blocks отсутствуют")

        lines.extend(["", "Evidence sources:"])
        for source in evidence_pack.selected_sources[:20]:
            lines.append(f"- {source.doc_id}/{source.version}/{source.block_id}")

        return "\n".join(lines)
