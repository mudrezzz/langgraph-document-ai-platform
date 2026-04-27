from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from application.document_service import DocumentListPage, DocumentRecord
from infra.fastmcp.repository_service import FastMcpRepositoryService


class _FakeDocumentService:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, Any]] = {}

    def upsert_document(self, *, doc_id: str, payload: dict[str, Any]) -> DocumentRecord:
        self.storage[doc_id] = dict(payload)
        return DocumentRecord(doc_id=doc_id, payload=dict(payload))

    def get_document(self, doc_id: str) -> DocumentRecord:
        if doc_id not in self.storage:
            raise KeyError(f"Документ {doc_id} не найден")
        return DocumentRecord(doc_id=doc_id, payload=dict(self.storage[doc_id]))

    def list_documents(self, *, limit: int = 50, offset: int = 0) -> DocumentListPage:
        ordered_ids = sorted(self.storage.keys(), reverse=True)
        window_ids = ordered_ids[offset : offset + limit]
        items = [
            DocumentRecord(
                doc_id=doc_id,
                payload=dict(self.storage[doc_id]),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for doc_id in window_ids
        ]
        return DocumentListPage(items=items, limit=limit, offset=offset, total_returned=len(items))


def test_fastmcp_repository_service_upsert_get_list() -> None:
    fake_service = _FakeDocumentService()
    mcp_service = FastMcpRepositoryService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    upserted = mcp_service.upsert_document({"doc_id": "DOC-1", "payload": {"title": "Release Plan", "v": 1}})
    loaded = mcp_service.get_document({"doc_id": "DOC-1"})
    listed = mcp_service.list_documents({"limit": 10, "offset": 0})

    assert upserted["doc_id"] == "DOC-1"
    assert loaded["payload"]["title"] == "Release Plan"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["doc_id"] == "DOC-1"


def test_fastmcp_repository_service_metadata_contains_tools() -> None:
    mcp_service = FastMcpRepositoryService(_FakeDocumentService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    metadata = mcp_service.metadata()

    assert metadata["service_name"] == "repository-mcp"
    assert metadata["transport"] == "fastmcp"
    assert metadata["policy_version"] == "mcp-policy-v1"
    assert metadata["service_scope"] == "repository"
    assert metadata["operation_scopes"] == {"get_document": "read", "list_documents": "read", "upsert_document": "write"}
    assert metadata["tool_required_roles"] == {
        "get_document": [],
        "list_documents": [],
        "upsert_document": ["repository_writer"],
    }
    assert "upsert_document" in metadata["tool_names"]
    assert "get_document" in metadata["tool_names"]
    assert "list_documents" in metadata["tool_names"]


def test_fastmcp_repository_service_get_not_found_raises_value_error() -> None:
    mcp_service = FastMcpRepositoryService(_FakeDocumentService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(ValueError, match="DOC-MISSING"):
        mcp_service.get_document({"doc_id": "DOC-MISSING"})


def test_fastmcp_repository_service_upsert_requires_role_when_auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    mcp_service = FastMcpRepositoryService(_FakeDocumentService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(ValueError, match="Authentication required"):
        mcp_service.upsert_document({"doc_id": "DOC-1", "payload": {"title": "Release Plan"}})

    saved = mcp_service.upsert_document(
        {
            "doc_id": "DOC-1",
            "payload": {"title": "Release Plan"},
            "actor": "alice",
            "roles": ["repository_writer"],
        }
    )

    assert saved["doc_id"] == "DOC-1"
