from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from application.template_library_service import TemplateListPage, TemplateRecord
from infra.fastmcp.template_library_service import FastMcpTemplateLibraryService
from schemas.documents.contracts import TemplateSpec


class _FakeTemplateLibraryService:
    def __init__(self) -> None:
        self.storage: dict[tuple[str, str], TemplateRecord] = {}

    def compile_template(
        self,
        *,
        template_id: str,
        version: str = "1",
        sections: list[dict[str, Any]] | None = None,
        validation_rules: list[dict[str, Any]] | None = None,
        assembly_rules: list[dict[str, Any]] | None = None,
    ) -> TemplateSpec:
        return TemplateSpec(
            template_id=template_id,
            version=version,
            sections=list(sections or []),
            validation_rules=list(validation_rules or []),
            assembly_rules=list(assembly_rules or []),
        )

    def upsert_template(self, template_spec: TemplateSpec, *, metadata: dict | None = None) -> str:
        now = datetime.now(timezone.utc)
        key = (template_spec.template_id, template_spec.version)
        existing = self.storage.get(key)
        self.storage[key] = TemplateRecord(
            template_id=template_spec.template_id,
            version=template_spec.version,
            template_spec=template_spec,
            metadata=dict(metadata or {}),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        return template_spec.template_id

    def get_template(self, template_id: str, version: str | None = None) -> TemplateRecord:
        if version is not None:
            key = (template_id, version)
            if key not in self.storage:
                raise KeyError(f"Template {template_id}:{version} не найден")
            return self.storage[key]

        matching = [record for (stored_template_id, _), record in self.storage.items() if stored_template_id == template_id]
        if not matching:
            raise KeyError(f"Template {template_id} не найден")
        return sorted(matching, key=lambda item: item.version, reverse=True)[0]

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
    ) -> TemplateListPage:
        records = list(self.storage.values())
        if template_id is not None:
            records = [item for item in records if item.template_id == template_id]
        ordered = sorted(records, key=lambda item: (item.template_id, item.version), reverse=True)
        window = ordered[offset : offset + limit]
        return TemplateListPage(items=window, limit=limit, offset=offset, total_returned=len(window))


def test_fastmcp_template_library_service_upsert_get_list() -> None:
    fake_service = _FakeTemplateLibraryService()
    mcp_service = FastMcpTemplateLibraryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    upserted = mcp_service.upsert_template(
        {
            "template_id": "board_memo",
            "version": "3",
            "sections": [
                {
                    "section_id": "decision",
                    "title": "Decision",
                    "objective": "Summarize decision.",
                    "required_keywords": ["decision"],
                }
            ],
            "assembly_rules": [
                {
                    "rule_id": "decision_first",
                    "mode": "section_order",
                    "section_order": ["decision"],
                    "include_writer_draft": False,
                    "include_traceability": True,
                }
            ],
            "metadata": {"owner": "unit-test"},
        }
    )
    loaded = mcp_service.get_template({"template_id": "board_memo", "version": "3"})
    listed = mcp_service.list_templates({"limit": 10, "offset": 0, "template_id": "board_memo"})

    assert upserted["template_id"] == "board_memo"
    assert upserted["version"] == "3"
    assert upserted["metadata"]["owner"] == "unit-test"
    assert loaded["template_spec"]["sections"][0]["section_id"] == "decision"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["template_id"] == "board_memo"


def test_fastmcp_template_library_service_metadata_contains_tools() -> None:
    mcp_service = FastMcpTemplateLibraryService(_FakeTemplateLibraryService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    metadata = mcp_service.metadata()

    assert metadata["service_name"] == "template-library-mcp"
    assert "upsert_template" in metadata["tool_names"]
    assert "get_template" in metadata["tool_names"]
    assert "list_templates" in metadata["tool_names"]


def test_fastmcp_template_library_service_get_not_found_raises_value_error() -> None:
    mcp_service = FastMcpTemplateLibraryService(_FakeTemplateLibraryService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(ValueError, match="missing-template"):
        mcp_service.get_template({"template_id": "missing-template"})

