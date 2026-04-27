from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from application.artifact_service import ArtifactListPage, ArtifactRecord
from infra.fastmcp.artifact_writer_service import FastMcpArtifactWriterService


class _FakeArtifactService:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, Any]] = {}

    def write_artifact(
        self,
        *,
        payload: dict[str, Any],
        artifact_id: str | None = None,
        artifact_type: str = "generic",
    ) -> ArtifactRecord:
        resolved_id = artifact_id or "artifact-auto-1"
        merged_payload = dict(payload)
        merged_payload["artifact_id"] = resolved_id
        merged_payload["artifact_type"] = artifact_type
        self.storage[resolved_id] = merged_payload
        return ArtifactRecord(artifact_id=resolved_id, artifact_type=artifact_type, payload=merged_payload)

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        if artifact_id not in self.storage:
            raise KeyError(f"Артефакт {artifact_id} не найден")
        payload = self.storage[artifact_id]
        return ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=str(payload.get("artifact_type", "generic")),
            payload=dict(payload),
        )

    def list_artifacts(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        artifact_type: str | None = None,
    ) -> ArtifactListPage:
        ordered_ids = sorted(self.storage.keys(), reverse=True)
        if artifact_type:
            ordered_ids = [
                artifact_id
                for artifact_id in ordered_ids
                if str(self.storage[artifact_id].get("artifact_type", "generic")) == artifact_type
            ]
        window_ids = ordered_ids[offset : offset + limit]
        items = [
            ArtifactRecord(
                artifact_id=artifact_id,
                artifact_type=str(self.storage[artifact_id].get("artifact_type", "generic")),
                payload=dict(self.storage[artifact_id]),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for artifact_id in window_ids
        ]
        return ArtifactListPage(items=items, limit=limit, offset=offset, total_returned=len(items))


def test_fastmcp_artifact_writer_service_write_get_list() -> None:
    fake_service = _FakeArtifactService()
    mcp_service = FastMcpArtifactWriterService(fake_service)  # type: ignore[arg-type]
    mcp_service.register_tools()

    written = mcp_service.write_artifact(
        {
            "artifact_id": "ART-1",
            "artifact_type": "release_report",
            "title": "GO/NO-GO",
            "content": "all green",
            "format": "markdown",
            "metadata": {"project_id": "p1"},
        }
    )
    loaded = mcp_service.get_artifact({"artifact_id": "ART-1"})
    listed = mcp_service.list_artifacts({"limit": 10, "offset": 0, "artifact_type": "release_report"})

    assert written["artifact_id"] == "ART-1"
    assert loaded["content"] == "all green"
    assert listed["total_returned"] == 1
    assert listed["items"][0]["artifact_id"] == "ART-1"


def test_fastmcp_artifact_writer_service_metadata_contains_tools() -> None:
    mcp_service = FastMcpArtifactWriterService(_FakeArtifactService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    metadata = mcp_service.metadata()

    assert metadata["service_name"] == "artifact-writer-mcp"
    assert metadata["transport"] == "fastmcp"
    assert metadata["policy_version"] == "mcp-policy-v1"
    assert metadata["service_scope"] == "artifact-writer"
    assert metadata["operation_scopes"] == {"get_artifact": "read", "list_artifacts": "read", "write_artifact": "write"}
    assert "write_artifact" in metadata["tool_names"]
    assert "get_artifact" in metadata["tool_names"]
    assert "list_artifacts" in metadata["tool_names"]


def test_fastmcp_artifact_writer_service_get_not_found_raises_value_error() -> None:
    mcp_service = FastMcpArtifactWriterService(_FakeArtifactService())  # type: ignore[arg-type]
    mcp_service.register_tools()

    with pytest.raises(ValueError, match="ART-MISSING"):
        mcp_service.get_artifact({"artifact_id": "ART-MISSING"})
