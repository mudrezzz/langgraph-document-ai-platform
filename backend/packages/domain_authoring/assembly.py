from __future__ import annotations

from typing import Any

from schemas.authoring.contracts import SectionArtifact
from schemas.documents.contracts import TemplateSpec


class DocumentAssembler:
    """Domain service for final authoring document assembly."""

    def resolve_selected_section_ids(
        self,
        *,
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
    ) -> list[str]:
        artifact_by_id = {item.section_id: item for item in section_artifacts}
        assembly_rule = self._resolve_assembly_rule(template_spec)
        sections_by_id = {
            str(section.get("section_id", "")).strip(): section
            for section in template_spec.sections
            if str(section.get("section_id", "")).strip()
        }
        section_order = self._resolve_section_order(template_spec, assembly_rule=assembly_rule)
        return self._select_section_ids(
            section_order=section_order,
            sections_by_id=sections_by_id,
            assembly_rule=assembly_rule,
            artifact_by_id=artifact_by_id,
        )

    def filter_section_traceability(
        self,
        *,
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        selected_section_ids = self.resolve_selected_section_ids(
            template_spec=template_spec,
            section_artifacts=section_artifacts,
        )
        traceability_by_id = {
            str(section.get("section_id", "")).strip(): section
            for section in section_traceability
            if str(section.get("section_id", "")).strip()
        }
        return [traceability_by_id[section_id] for section_id in selected_section_ids if section_id in traceability_by_id]

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
        sections_by_id = {
            str(section.get("section_id", "")).strip(): section
            for section in template_spec.sections
            if str(section.get("section_id", "")).strip()
        }
        artifact_by_id = {item.section_id: item for item in section_artifacts}
        assembly_rule = self._resolve_assembly_rule(template_spec)
        selected_section_ids = self.resolve_selected_section_ids(
            template_spec=template_spec,
            section_artifacts=section_artifacts,
        )
        selected_traceability = self.filter_section_traceability(
            template_spec=template_spec,
            section_artifacts=section_artifacts,
            section_traceability=section_traceability,
        )
        lines = [
            f"# {self._title_from_template(template_spec)}",
            "",
            "## Query",
            query.strip(),
            "",
            "## Research",
            research_summary,
        ]

        for section_id in selected_section_ids:
            section = sections_by_id.get(
                section_id,
                {"section_id": section_id, "title": section_id.replace("_", " ").title()},
            )
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
            ]
        )
        if self._include_writer_draft(assembly_rule):
            lines.extend(
                [
                    "",
                    "## Writer Draft",
                    writer_draft,
                ]
            )
        if self._include_traceability(assembly_rule):
            lines.extend(["", "## Section Traceability"])
            for section in selected_traceability:
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

    def _resolve_assembly_rule(self, template_spec: TemplateSpec) -> dict[str, Any]:
        default_section_order = [
            str(section.get("section_id", "")).strip()
            for section in template_spec.sections
            if str(section.get("section_id", "")).strip()
        ]
        for rule in template_spec.assembly_rules:
            if str(rule.get("mode", "")) != "section_order":
                continue
            return {
                "mode": "section_order",
                "section_order": [str(item).strip() for item in rule.get("section_order", []) if str(item).strip()],
                "include_sections": [str(item).strip() for item in rule.get("include_sections", []) if str(item).strip()],
                "exclude_sections": [str(item).strip() for item in rule.get("exclude_sections", []) if str(item).strip()],
                "allowed_section_groups": [
                    str(item).strip() for item in rule.get("allowed_section_groups", []) if str(item).strip()
                ],
                "include_writer_draft": self._coerce_bool(rule.get("include_writer_draft"), default=True),
                "include_traceability": self._coerce_bool(rule.get("include_traceability"), default=True),
            }
        return {
            "mode": "section_order",
            "section_order": default_section_order,
            "include_sections": [],
            "exclude_sections": [],
            "allowed_section_groups": [],
            "include_writer_draft": True,
            "include_traceability": True,
        }

    def _resolve_section_order(
        self,
        template_spec: TemplateSpec,
        *,
        assembly_rule: dict[str, Any] | None = None,
    ) -> list[str]:
        resolved_rule = assembly_rule or self._resolve_assembly_rule(template_spec)
        section_order = [str(item).strip() for item in resolved_rule.get("section_order", []) if str(item).strip()]
        if section_order:
            return section_order
        return [
            str(section.get("section_id", "")).strip()
            for section in template_spec.sections
            if str(section.get("section_id", "")).strip()
        ]

    def _select_section_ids(
        self,
        *,
        section_order: list[str],
        sections_by_id: dict[str, dict[str, Any]],
        assembly_rule: dict[str, Any],
        artifact_by_id: dict[str, SectionArtifact],
    ) -> list[str]:
        include_sections = set(str(item).strip() for item in assembly_rule.get("include_sections", []) if str(item).strip())
        exclude_sections = set(str(item).strip() for item in assembly_rule.get("exclude_sections", []) if str(item).strip())
        allowed_groups = set(
            str(item).strip() for item in assembly_rule.get("allowed_section_groups", []) if str(item).strip()
        )

        selected: list[str] = []
        for section_id in section_order:
            if section_id in exclude_sections:
                continue
            section = sections_by_id.get(section_id, {})
            artifact = artifact_by_id.get(section_id)
            if include_sections and section_id not in include_sections:
                continue
            if not self._section_group_allowed(section, allowed_groups=allowed_groups):
                continue
            if not self._should_include_section(section=section, artifact=artifact):
                continue
            selected.append(section_id)
        return selected

    def _section_group_allowed(self, section: dict[str, Any], *, allowed_groups: set[str]) -> bool:
        if not allowed_groups:
            return True
        group = str(section.get("section_group") or "").strip()
        return bool(group) and group in allowed_groups

    def _should_include_section(self, *, section: dict[str, Any], artifact: SectionArtifact | None) -> bool:
        required = self._coerce_bool(section.get("required"), default=True)
        if required:
            return True

        include_if_has_evidence = self._coerce_bool(section.get("include_if_has_evidence"), default=False)
        if include_if_has_evidence and artifact is not None and bool(artifact.source_refs):
            return True

        allowed_statuses = [
            str(item).strip().lower() for item in section.get("include_if_review_status", []) if str(item).strip()
        ]
        if allowed_statuses and artifact is not None:
            review_status = str(artifact.review_status or "").strip().lower()
            if review_status in allowed_statuses:
                return True

        return False

    def _include_writer_draft(self, assembly_rule: dict[str, Any]) -> bool:
        return self._coerce_bool(assembly_rule.get("include_writer_draft"), default=True)

    def _include_traceability(self, assembly_rule: dict[str, Any]) -> bool:
        return self._coerce_bool(assembly_rule.get("include_traceability"), default=True)

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"", "0", "false", "no", "off"}:
                return False
            if normalized in {"1", "true", "yes", "on"}:
                return True
        return bool(value)
