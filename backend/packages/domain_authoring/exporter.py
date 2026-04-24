from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from schemas.authoring.contracts import SectionArtifact
from schemas.documents.contracts import TemplateSpec


class ArtifactExportResult(BaseModel):
    """Rendered artifact payload for persistence/API delivery."""

    content: str
    format: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactExporter:
    """Exports deterministic authoring results into the requested artifact format."""

    def export(
        self,
        *,
        artifact_type: str,
        artifact_title: str | None,
        artifact_format: str,
        assembled_content: str,
        query: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
    ) -> ArtifactExportResult:
        requested_format = str(artifact_format or "markdown").strip().lower() or "markdown"
        if requested_format == "application/json":
            requested_format = "json"
        if requested_format == "json":
            return ArtifactExportResult(
                content=self._render_json(
                    artifact_type=artifact_type,
                    artifact_title=artifact_title,
                    query=query,
                    research_summary=research_summary,
                    writer_draft=writer_draft,
                    review_result=review_result,
                    template_spec=template_spec,
                    section_artifacts=section_artifacts,
                    section_traceability=section_traceability,
                ),
                format="json",
                metadata={
                    "export_format_requested": artifact_format,
                    "export_format_resolved": "json",
                },
            )

        return ArtifactExportResult(
            content=assembled_content,
            format="markdown",
            metadata={
                "export_format_requested": artifact_format,
                "export_format_resolved": "markdown",
            },
        )

    def _render_json(
        self,
        *,
        artifact_type: str,
        artifact_title: str | None,
        query: str,
        research_summary: str,
        writer_draft: str,
        review_result: dict[str, Any],
        template_spec: TemplateSpec,
        section_artifacts: list[SectionArtifact],
        section_traceability: list[dict[str, Any]],
    ) -> str:
        payload: dict[str, Any] = {
            "title": artifact_title,
            "artifact_type": artifact_type,
            "template_id": template_spec.template_id,
            "template_version": template_spec.version,
            "query": query,
            "research_summary": research_summary,
            "review": {
                "status": review_result.get("status"),
                "recommendation": review_result.get("recommendation"),
                "notes": review_result.get("notes"),
                "issues": list(review_result.get("issues", []) or []),
            },
            "sections": [item.model_dump(mode="json") for item in section_artifacts],
        }
        if self._include_writer_draft(template_spec):
            payload["writer_draft"] = writer_draft
        if self._include_traceability(template_spec):
            payload["traceability"] = {"sections": section_traceability}
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _include_writer_draft(self, template_spec: TemplateSpec) -> bool:
        rule = self._resolve_assembly_rule(template_spec)
        return self._coerce_bool(rule.get("include_writer_draft"), default=True)

    def _include_traceability(self, template_spec: TemplateSpec) -> bool:
        rule = self._resolve_assembly_rule(template_spec)
        return self._coerce_bool(rule.get("include_traceability"), default=True)

    def _resolve_assembly_rule(self, template_spec: TemplateSpec) -> dict[str, Any]:
        for rule in template_spec.assembly_rules:
            if str(rule.get("mode", "")) != "section_order":
                continue
            return dict(rule)
        return {
            "include_writer_draft": True,
            "include_traceability": True,
        }

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
