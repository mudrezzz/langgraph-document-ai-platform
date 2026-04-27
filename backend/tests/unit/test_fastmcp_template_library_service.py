from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from application.errors import InvalidTemplateStatusTransitionError
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

    def upsert_template(
        self,
        template_spec: TemplateSpec,
        *,
        metadata: dict | None = None,
        status: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        key = (template_spec.template_id, template_spec.version)
        existing = self.storage.get(key)
        self.storage[key] = TemplateRecord(
            template_id=template_spec.template_id,
            version=template_spec.version,
            status=status or (existing.status if existing is not None else "draft"),
            template_spec=template_spec,
            metadata=dict(metadata or {}),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        return template_spec.template_id

    def get_template(self, template_id: str, version: str | None = None, *, published_only: bool = False) -> TemplateRecord:
        if version is not None:
            key = (template_id, version)
            if key not in self.storage:
                raise KeyError(f"Template {template_id}:{version} не найден")
            return self.storage[key]

        matching = [record for (stored_template_id, _), record in self.storage.items() if stored_template_id == template_id]
        if published_only:
            matching = [record for record in matching if record.status == "published"]
        if not matching:
            raise KeyError(f"Template {template_id} не найден")
        return sorted(matching, key=lambda item: item.version, reverse=True)[0]

    def publish_template(self, template_id: str, version: str) -> TemplateRecord:
        return self.set_template_status(template_id, version, "published")

    def set_template_status(
        self,
        template_id: str,
        version: str,
        status: str,
        *,
        reason: str | None = None,
        actor: str | None = None,
        metadata: dict | None = None,
    ) -> TemplateRecord:
        key = (template_id, version)
        current = self.storage.get(key)
        if current is None:
            raise KeyError(f"Template {template_id}:{version} не найден")
        if current.status == "archived" and status != "archived":
            raise InvalidTemplateStatusTransitionError("Переход статуса template archived -> active не разрешен")

        now = datetime.now(timezone.utc)
        if status == "published":
            for existing_key, existing_record in list(self.storage.items()):
                if existing_key[0] != template_id or existing_key == key:
                    continue
                if existing_record.status != "published":
                    continue
                self.storage[existing_key] = existing_record.model_copy(update={"status": "draft", "updated_at": now})

        merged_metadata = dict(current.metadata)
        if metadata:
            merged_metadata.update(metadata)
        governance = dict(merged_metadata.get("governance") or {})
        history = list(governance.get("status_history") or [])
        history.append({"status": status, "reason": reason, "actor": actor})
        governance.update({"current_status": status, "reason": reason, "updated_by": actor, "status_history": history})
        merged_metadata["governance"] = governance

        updated = current.model_copy(update={"status": status, "metadata": merged_metadata, "updated_at": now})
        self.storage[key] = updated
        return updated

    def list_templates(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        template_id: str | None = None,
        status: str | None = None,
    ) -> TemplateListPage:
        records = list(self.storage.values())
        if template_id is not None:
            records = [item for item in records if item.template_id == template_id]
        if status is not None:
            records = [item for item in records if item.status == status]
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
    assert upserted["status"] == "draft"
    assert upserted["metadata"]["owner"] == "unit-test"
    assert loaded["template_spec"]["sections"][0]["section_id"] == "decision"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["template_id"] == "board_memo"


def test_fastmcp_template_library_service_metadata_contains_tools() -> None:
    mcp_service = FastMcpTemplateLibraryService(_FakeTemplateLibraryService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    metadata = mcp_service.metadata()

    assert metadata["service_name"] == "template-library-mcp"
    assert metadata["transport"] == "fastmcp"
    assert metadata["policy_version"] == "mcp-policy-v1"
    assert metadata["service_scope"] == "template-library"
    assert metadata["operation_scopes"] == {"get_template": "read", "list_templates": "read", "publish_template": "write", "set_template_status": "write", "upsert_template": "write"}
    assert "upsert_template" in metadata["tool_names"]
    assert "publish_template" in metadata["tool_names"]
    assert "set_template_status" in metadata["tool_names"]
    assert "get_template" in metadata["tool_names"]
    assert "list_templates" in metadata["tool_names"]


def test_fastmcp_template_library_service_get_not_found_raises_value_error() -> None:
    mcp_service = FastMcpTemplateLibraryService(_FakeTemplateLibraryService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(ValueError, match="missing-template"):
        mcp_service.get_template({"template_id": "missing-template"})


def test_fastmcp_template_library_service_publish_and_filter_by_status() -> None:
    fake_service = _FakeTemplateLibraryService()
    mcp_service = FastMcpTemplateLibraryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    mcp_service.upsert_template(
        {
            "template_id": "status_report",
            "version": "1",
            "status": "draft",
            "sections": [{"section_id": "overview", "title": "Overview"}],
        }
    )
    published = mcp_service.publish_template({"template_id": "status_report", "version": "1"})
    listed = mcp_service.list_templates({"limit": 10, "offset": 0, "status": "published"})

    assert published["status"] == "published"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["template_id"] == "status_report"


def test_fastmcp_template_library_service_publish_demotes_previous_published_version() -> None:
    fake_service = _FakeTemplateLibraryService()
    mcp_service = FastMcpTemplateLibraryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    mcp_service.upsert_template(
        {
            "template_id": "status_report",
            "version": "1",
            "sections": [{"section_id": "overview_v1", "title": "Overview V1"}],
        }
    )
    mcp_service.upsert_template(
        {
            "template_id": "status_report",
            "version": "2",
            "sections": [{"section_id": "overview_v2", "title": "Overview V2"}],
        }
    )

    mcp_service.publish_template({"template_id": "status_report", "version": "1"})
    mcp_service.publish_template({"template_id": "status_report", "version": "2"})

    first = mcp_service.get_template({"template_id": "status_report", "version": "1"})
    second = mcp_service.get_template({"template_id": "status_report", "version": "2"})
    listed = mcp_service.list_templates({"limit": 10, "offset": 0, "template_id": "status_report", "status": "published"})

    assert first["status"] == "draft"
    assert second["status"] == "published"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["version"] == "2"


def test_fastmcp_template_library_service_set_template_status_supports_deprecate_and_archive() -> None:
    fake_service = _FakeTemplateLibraryService()
    mcp_service = FastMcpTemplateLibraryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    mcp_service.upsert_template(
        {
            "template_id": "status_report",
            "version": "3",
            "sections": [{"section_id": "overview", "title": "Overview"}],
        }
    )

    deprecated = mcp_service.set_template_status(
        {
            "template_id": "status_report",
            "version": "3",
            "status": "deprecated",
            "reason": "legacy layout",
            "actor": "qa",
        }
    )
    archived = mcp_service.set_template_status(
        {
            "template_id": "status_report",
            "version": "3",
            "status": "archived",
            "reason": "retired",
            "actor": "qa",
        }
    )

    assert deprecated["status"] == "deprecated"
    assert deprecated["metadata"]["governance"]["current_status"] == "deprecated"
    assert archived["status"] == "archived"
    assert archived["metadata"]["governance"]["status_history"][-1]["status"] == "archived"


def test_fastmcp_template_library_service_invalid_status_transition_raises_value_error() -> None:
    fake_service = _FakeTemplateLibraryService()
    mcp_service = FastMcpTemplateLibraryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    mcp_service.upsert_template(
        {
            "template_id": "status_report",
            "version": "4",
            "sections": [{"section_id": "overview", "title": "Overview"}],
        }
    )
    mcp_service.set_template_status(
        {
            "template_id": "status_report",
            "version": "4",
            "status": "archived",
        }
    )

    with pytest.raises(ValueError, match="archived"):
        mcp_service.set_template_status(
            {
                "template_id": "status_report",
                "version": "4",
                "status": "draft",
            }
        )
