from __future__ import annotations

from typing import Any

from schemas.authoring.contracts import SectionArtifact
from schemas.documents.contracts import TemplateSpec


class DocumentAssembler:
    """Domain service for final authoring document assembly."""

    def assemble_document(
        self,
        *,
        query: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        section_traceability: list[dict[str, Any]],
        workflow_mode: str,
        template_spec: TemplateSpec | None = None,
        section_artifacts: list[SectionArtifact] | None = None,
    ) -> str:
        if workflow_mode == "single_pass":
            return writer_draft

        if template_spec is not None and section_artifacts:
            return self._assemble_from_template(
                query=query,
                research_summary=research_summary,
                writer_draft=writer_draft,
                review_result=review_result,
                template_spec=template_spec,
                section_artifacts=section_artifacts,
                section_traceability=section_traceability,
            )

        lines = [
            "# Release Readiness Report",
            "",
            "## Query",
            query.strip(),
            "",
            "## Research",
            research_summary,
            "",
            "## Writer",
            writer_draft,
            "",
            "## Reviewer",
            f"- status: {review_result.get('status', 'unknown')}",
            f"- recommendation: {review_result.get('recommendation', 'pending_manual_review')}",
            f"- notes: {review_result.get('notes', '-')}",
        ]

        issues = review_result.get("issues", []) or []
        lines.append("- issues:")
        if issues:
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("  - none")

        lines.extend(["", "## Section Traceability"])
        for section in section_traceability:
            lines.append(
                f"- {section['section_id']} ({section['title']}), review_status={section.get('review_status', 'not_reviewed')}"
            )
            for source in section.get("source_refs", [])[:5]:
                lines.append(f"  - {source['doc_id']}/{source['version']}/{source['block_id']}")

        return "\n".join(lines)

    def _assemble_from_template(
        self,
        *,
        query: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
    ) -> str:
        artifact_by_id = {item.section_id: item for item in section_artifacts}
        section_order = self._resolve_section_order(template_spec)
        lines = [
            f"# {self._title_from_template(template_spec)}",
            "",
            "## Query",
            query.strip(),
            "",
            "## Research",
            research_summary,
        ]

        sections_by_id = {
            str(section.get("section_id", "")).strip(): section
            for section in template_spec.sections
            if str(section.get("section_id", "")).strip()
        }

        for section_id in section_order:
            section = sections_by_id.get(section_id, {"section_id": section_id, "title": section_id.replace("_", " ").title()})
            title = str(section.get("title", section_id)).strip()
            artifact = artifact_by_id.get(section_id)
            lines.extend(["", f"## {title}"])
            if artifact is None:
                lines.append("Section artifact is missing.")
                continue
            lines.append(artifact.content)
            if artifact.digest.decisions:
                lines.append("")
                lines.append("Decisions:")
                for item in artifact.digest.decisions[:3]:
                    lines.append(f"- {item}")
            if artifact.digest.constraints:
                lines.append("")
                lines.append("Constraints:")
                for item in artifact.digest.constraints[:3]:
                    lines.append(f"- {item}")
            if artifact.digest.open_questions:
                lines.append("")
                lines.append("Open Questions:")
                for item in artifact.digest.open_questions[:3]:
                    lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Reviewer",
                f"- status: {review_result.get('status', 'unknown')}",
                f"- recommendation: {review_result.get('recommendation', 'pending_manual_review')}",
                f"- notes: {review_result.get('notes', '-')}",
                "",
                "## Writer Draft",
                writer_draft,
                "",
                "## Section Traceability",
            ]
        )
        for section in section_traceability:
            lines.append(
                f"- {section['section_id']} ({section['title']}), review_status={section.get('review_status', 'not_reviewed')}"
            )
            for source in section.get("source_refs", [])[:5]:
                lines.append(f"  - {source['doc_id']}/{source['version']}/{source['block_id']}")

        return "\n".join(lines)

    def _title_from_template(self, template_spec: TemplateSpec) -> str:
        if template_spec.template_id == "release_readiness":
            return "Release Readiness Report"
        return template_spec.template_id.replace("_", " ").title()

    def _resolve_section_order(self, template_spec: TemplateSpec) -> list[str]:
        for rule in template_spec.assembly_rules:
            if str(rule.get("mode", "")) != "section_order":
                continue
            section_order = [str(item).strip() for item in rule.get("section_order", []) if str(item).strip()]
            if section_order:
                return section_order
        return [str(section.get("section_id", "")).strip() for section in template_spec.sections if str(section.get("section_id", "")).strip()]
