from __future__ import annotations

from typing import Any

from schemas.documents.contracts import TemplateSpec


class TemplateCompiler:
    """Compiles loose template inputs into a normalized TemplateSpec."""

    def compile(self, *, template_id: str, template_payload: dict[str, Any] | None = None) -> TemplateSpec:
        payload = dict(template_payload or {})
        version = str(payload.get("version", "1"))
        sections = self._normalize_sections(payload.get("sections"), template_id=template_id)
        validation_rules = self._normalize_validation_rules(payload.get("validation_rules"))
        assembly_rules = self._normalize_assembly_rules(payload.get("assembly_rules"))

        if not sections:
            sections = self._default_sections(template_id=template_id)
        if not assembly_rules:
            assembly_rules = self._default_assembly_rules(template_id=template_id, sections=sections)

        return TemplateSpec(
            template_id=template_id,
            version=version,
            sections=sections,
            validation_rules=validation_rules,
            assembly_rules=assembly_rules,
        )

    def _normalize_sections(self, raw_sections: Any, *, template_id: str) -> list[dict[str, Any]]:
        if not isinstance(raw_sections, list):
            return []

        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(raw_sections, start=1):
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("section_id") or item.get("id") or f"section_{index}").strip() or f"section_{index}"
            if section_id in seen:
                section_id = f"{section_id}_{index}"
            seen.add(section_id)

            title = str(item.get("title") or section_id.replace("_", " ").title()).strip()
            objective = str(item.get("objective") or f"Produce section {title} for template {template_id}.").strip()
            required_keywords = [str(value).strip() for value in item.get("required_keywords", []) if str(value).strip()]
            source_hints = [str(value).strip() for value in item.get("source_hints", []) if str(value).strip()]

            normalized.append(
                {
                    "section_id": section_id,
                    "title": title,
                    "objective": objective,
                    "required_keywords": required_keywords,
                    "source_hints": source_hints,
                    "required": self._coerce_bool(item.get("required"), default=True),
                    "include_if_has_evidence": self._coerce_bool(item.get("include_if_has_evidence"), default=False),
                    "include_if_review_status": self._normalize_status_list(item.get("include_if_review_status")),
                    "section_group": str(item.get("section_group") or "").strip() or None,
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
        return normalized

    def _normalize_validation_rules(self, raw_rules: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_rules, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in raw_rules:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("rule_id") or item.get("id") or "").strip()
            description = str(item.get("description") or item.get("rule") or "").strip()
            if not rule_id and not description:
                continue
            normalized.append(
                {
                    "rule_id": rule_id or f"rule_{len(normalized) + 1}",
                    "description": description or rule_id,
                    "severity": str(item.get("severity") or "warning"),
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
        return normalized

    def _normalize_assembly_rules(self, raw_rules: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_rules, list):
            return []

        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(raw_rules, start=1):
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("rule_id") or item.get("id") or f"assembly_rule_{index}").strip() or f"assembly_rule_{index}"
            section_order = [str(value).strip() for value in item.get("section_order", []) if str(value).strip()]
            normalized.append(
                {
                    "rule_id": rule_id,
                    "mode": str(item.get("mode") or "section_order"),
                    "section_order": section_order,
                    "include_sections": [
                        str(value).strip() for value in item.get("include_sections", []) if str(value).strip()
                    ],
                    "exclude_sections": [
                        str(value).strip() for value in item.get("exclude_sections", []) if str(value).strip()
                    ],
                    "allowed_section_groups": [
                        str(value).strip() for value in item.get("allowed_section_groups", []) if str(value).strip()
                    ],
                    "include_writer_draft": bool(item.get("include_writer_draft", True)),
                    "include_traceability": bool(item.get("include_traceability", True)),
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
        return normalized

    def _default_sections(self, *, template_id: str) -> list[dict[str, Any]]:
        if template_id == "release_readiness":
            return [
                {
                    "section_id": "risk_assessment",
                    "title": "Risk Assessment",
                    "objective": "Summarize blocking risks, pending items, and critical constraints for release readiness.",
                    "required_keywords": ["risk", "block", "critical", "pending", "no-go"],
                    "source_hints": ["risk", "pending", "constraint"],
                    "metadata": {},
                },
                {
                    "section_id": "pending_approvals",
                    "title": "Pending Approvals",
                    "objective": "List approvals, governance gates, and remaining sign-offs required before release.",
                    "required_keywords": ["approval", "approve", "governance", "security", "policy"],
                    "source_hints": ["approval", "governance", "security"],
                    "metadata": {},
                },
                {
                    "section_id": "final_recommendation",
                    "title": "Final Recommendation",
                    "objective": "State the current go/no-go recommendation and explain its basis from the evidence.",
                    "required_keywords": ["recommendation", "go", "no-go", "decision"],
                    "source_hints": ["decision", "recommendation"],
                    "metadata": {},
                },
                {
                    "section_id": "evidence_register",
                    "title": "Evidence Register",
                    "objective": "Provide a compact register of source references used by the report.",
                    "required_keywords": [],
                    "source_hints": [],
                    "required": False,
                    "include_if_has_evidence": True,
                    "include_if_review_status": [],
                    "section_group": "appendix",
                    "metadata": {"informational": True},
                },
            ]

        return [
            {
                "section_id": "overview",
                "title": "Overview",
                "objective": f"Provide a concise overview for template {template_id}.",
                "required_keywords": [],
                "source_hints": [],
                "required": True,
                "include_if_has_evidence": False,
                "include_if_review_status": [],
                "section_group": None,
                "metadata": {},
            }
        ]

    def _default_assembly_rules(self, *, template_id: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "rule_id": f"{template_id}_default_assembly",
                "mode": "section_order",
                "section_order": [str(item.get("section_id", "")).strip() for item in sections if str(item.get("section_id", "")).strip()],
                "include_sections": [],
                "exclude_sections": [],
                "allowed_section_groups": [],
                "include_writer_draft": True,
                "include_traceability": True,
                "metadata": {},
            }
        ]

    def _normalize_status_list(self, raw_value: Any) -> list[str]:
        if not isinstance(raw_value, list):
            return []
        normalized = []
        for value in raw_value:
            item = str(value).strip().lower()
            if item:
                normalized.append(item)
        return normalized

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
