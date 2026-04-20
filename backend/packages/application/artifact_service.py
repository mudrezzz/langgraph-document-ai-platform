from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from application.errors import ArtifactNotFoundError
from infra.postgres.artifact_store import PostgresArtifactStore


class ArtifactRecord(BaseModel):
    """Внутренняя запись артефакта для application-слоя."""

    artifact_id: str
    artifact_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArtifactListPage(BaseModel):
    """Страница артефактов для list-операции."""

    items: list[ArtifactRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class ArtifactApplicationService:
    """Application service для операций artifact store."""

    def __init__(self, artifact_store: PostgresArtifactStore) -> None:
        self._artifact_store = artifact_store

    def write_artifact(
        self,
        *,
        payload: dict[str, Any],
        artifact_id: str | None = None,
        artifact_type: str = "generic",
    ) -> ArtifactRecord:
        resolved_id = artifact_id or str(uuid4())
        normalized_payload = dict(payload)
        normalized_payload["artifact_id"] = resolved_id
        normalized_payload["artifact_type"] = artifact_type
        self._artifact_store.save_artifact(resolved_id, normalized_payload)
        loaded_payload = self._artifact_store.read_artifact(resolved_id)
        return ArtifactRecord(
            artifact_id=resolved_id,
            artifact_type=str(loaded_payload.get("artifact_type", artifact_type)),
            payload=loaded_payload,
        )

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        try:
            payload = self._artifact_store.read_artifact(artifact_id)
        except KeyError as exc:
            raise ArtifactNotFoundError(f"Артефакт {artifact_id} не найден") from exc
        return ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=str(payload.get("artifact_type", "generic")),
            payload=payload,
        )

    def list_artifacts(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        artifact_type: str | None = None,
    ) -> ArtifactListPage:
        rows = self._artifact_store.list_artifacts(limit=limit, offset=offset, artifact_type=artifact_type)
        items = [
            ArtifactRecord(
                artifact_id=str(row.get("artifact_id", "")),
                artifact_type=str(row.get("artifact_type", "generic")),
                payload=dict(row.get("payload") or {}),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
            for row in rows
        ]
        return ArtifactListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=len(items),
        )
