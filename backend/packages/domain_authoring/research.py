from __future__ import annotations

from schemas.rag.contracts import EvidencePack


class ResearchSummaryBuilder:
    """Domain service for composing authoring research summaries from evidence."""

    def build_summary(self, *, query: str, evidence_pack: EvidencePack) -> str:
        lines = [
            "Запрос:",
            query.strip(),
            "",
            "Ключевые наблюдения:",
        ]

        for block in evidence_pack.selected_blocks[:6]:
            snippet = block.text.strip()
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            lines.append(f"- {snippet} ({block.source.doc_id}/{block.source.block_id})")

        if not evidence_pack.selected_blocks:
            lines.append("- Retrieval не вернул блоки evidence.")

        return "\n".join(lines)
