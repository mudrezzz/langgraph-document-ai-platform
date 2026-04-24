from __future__ import annotations

from typing import Any

from schemas.rag.contracts import EvidencePack


class SectionReviewService:
    """Domain service for reviewer heuristics and section review updates."""

    def review_draft(
        self,
        *,
        query: str,
        draft: str,
        evidence_pack: EvidencePack,
        workflow_mode: str,
    ) -> dict[str, Any]:
        _ = query, draft
        if workflow_mode == "single_pass":
            return {
                "status": "skipped",
                "notes": "Reviewer этап пропущен в single_pass режиме.",
                "recommendation": "pending_manual_review",
                "issues": [],
            }

        risk_keywords = ("pending", "block", "critical", "fail", "no-go", "risk")
        approval_keywords = ("approval", "approve", "governance", "security")

        risk_count = 0
        approval_mentions = 0
        issues: list[str] = []

        for block in evidence_pack.selected_blocks:
            lowered = block.text.lower()
            if any(word in lowered for word in risk_keywords):
                risk_count += 1
            if any(word in lowered for word in approval_keywords):
                approval_mentions += 1

        if not evidence_pack.selected_blocks:
            issues.append("Нет evidence блоков для reviewer проверки.")
        if risk_count == 0:
            issues.append("Risk-сигналы в evidence почти не выражены.")
        if approval_mentions == 0:
            issues.append("Не обнаружены явные approval-ссылки.")

        if not evidence_pack.selected_blocks:
            recommendation = "no_go"
            status = "needs_revision"
            notes = "Недостаточно evidence для релизного решения."
        elif risk_count >= 2:
            recommendation = "no_go"
            status = "needs_revision"
            notes = "Обнаружены выраженные risk-сигналы и pending ограничения."
        elif approval_mentions >= 1:
            recommendation = "conditional_go"
            status = "completed"
            notes = "Есть approval-контекст, но требуется контроль оставшихся ограничений."
        else:
            recommendation = "go"
            status = "completed"
            notes = "Критичные риск-сигналы не выявлены, evidence достаточно для GO."

        return {
            "status": status,
            "notes": notes,
            "recommendation": recommendation,
            "issues": issues,
            "risk_count": risk_count,
            "approval_mentions": approval_mentions,
        }

    def set_section_review_status(self, *, sections: list[dict[str, Any]], review_status: str) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        for section in sections:
            current = dict(section)
            if current.get("section_id") != "evidence_register":
                current["review_status"] = review_status
            updated.append(current)
        return updated
