from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from application.errors import ConfigurationNotFoundError


class ConfigurationRecord(BaseModel):
    """Versioned configuration artifact stored in the library."""

    config_id: str
    version: str
    config_type: str = "generic"
    title: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfigurationListPage(BaseModel):
    """Read-model page for stored configurations."""

    items: list[ConfigurationRecord] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class ConfigurationValueDiff(BaseModel):
    """One changed payload path between two configuration versions."""

    key: str
    left_value: Any = None
    right_value: Any = None


class ConfigurationComparison(BaseModel):
    """Deterministic config diff summary for MCP/API callers."""

    left: ConfigurationRecord
    right: ConfigurationRecord
    shared_keys: list[str] = Field(default_factory=list)
    left_only_keys: list[str] = Field(default_factory=list)
    right_only_keys: list[str] = Field(default_factory=list)
    changed_values: list[ConfigurationValueDiff] = Field(default_factory=list)
    same_value_keys: list[str] = Field(default_factory=list)


class SimilarConfigurationMatch(BaseModel):
    """Similarity match against another stored configuration."""

    config_id: str
    version: str
    config_type: str = "generic"
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity_score: float = 0.0
    shared_key_count: int = 0
    exact_value_match_count: int = 0
    overlapping_tags: list[str] = Field(default_factory=list)


class SimilarConfigurationPage(BaseModel):
    """Page of similar configuration matches."""

    items: list[SimilarConfigurationMatch] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class ConfigurationLibraryStore(Protocol):
    """Persistence port for versioned configuration library."""

    def upsert_config(
        self,
        *,
        config_id: str,
        version: str,
        config_type: str,
        title: str | None,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Persist one configuration artifact."""

    def get_config(self, config_id: str, version: str | None = None) -> ConfigurationRecord:
        """Load one configuration by id/version."""

    def list_configs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> list[ConfigurationRecord]:
        """List stored configurations with basic filters."""

    def count_configs(
        self,
        *,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        """Count stored configurations for paged responses."""


class ConfigurationLibraryApplicationService:
    """Application boundary for reusable configuration bundles."""

    def __init__(self, store: ConfigurationLibraryStore, *, similarity_pool_limit: int = 250) -> None:
        self._store = store
        self._similarity_pool_limit = max(similarity_pool_limit, 50)

    def upsert_config(
        self,
        *,
        config_id: str,
        version: str = "1",
        config_type: str = "generic",
        title: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> ConfigurationRecord:
        self._store.upsert_config(
            config_id=config_id,
            version=version,
            config_type=config_type,
            title=title,
            payload=dict(payload or {}),
            metadata=dict(metadata or {}),
            tags=_normalize_tags(tags),
        )
        return self.get_config(config_id, version)

    def get_config(self, config_id: str, version: str | None = None) -> ConfigurationRecord:
        try:
            return self._store.get_config(config_id, version)
        except KeyError as exc:
            requested = f"{config_id}:{version}" if version is not None else config_id
            raise ConfigurationNotFoundError(f"Configuration {requested} не найдена") from exc

    def list_configs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        config_id: str | None = None,
        config_type: str | None = None,
        tag: str | None = None,
    ) -> ConfigurationListPage:
        items = self._store.list_configs(
            limit=limit,
            offset=offset,
            config_id=config_id,
            config_type=config_type,
            tag=tag,
        )
        return ConfigurationListPage(
            items=items,
            limit=limit,
            offset=offset,
            total_returned=self._store.count_configs(
                config_id=config_id,
                config_type=config_type,
                tag=tag,
            ),
        )

    def compare_configs(
        self,
        *,
        left_config_id: str,
        right_config_id: str,
        left_version: str | None = None,
        right_version: str | None = None,
    ) -> ConfigurationComparison:
        left = self.get_config(left_config_id, left_version)
        right = self.get_config(right_config_id, right_version)

        left_flat = _flatten_payload(left.payload)
        right_flat = _flatten_payload(right.payload)

        shared_keys = sorted(set(left_flat) & set(right_flat))
        left_only_keys = sorted(set(left_flat) - set(right_flat))
        right_only_keys = sorted(set(right_flat) - set(left_flat))
        same_value_keys: list[str] = []
        changed_values: list[ConfigurationValueDiff] = []

        for key in shared_keys:
            if _stable_value(left_flat[key]) == _stable_value(right_flat[key]):
                same_value_keys.append(key)
                continue
            changed_values.append(
                ConfigurationValueDiff(
                    key=key,
                    left_value=left_flat[key],
                    right_value=right_flat[key],
                )
            )

        return ConfigurationComparison(
            left=left,
            right=right,
            shared_keys=shared_keys,
            left_only_keys=left_only_keys,
            right_only_keys=right_only_keys,
            changed_values=changed_values,
            same_value_keys=same_value_keys,
        )

    def find_similar_configs(
        self,
        *,
        reference_config_id: str | None = None,
        reference_version: str | None = None,
        candidate_payload: dict[str, Any] | None = None,
        config_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SimilarConfigurationPage:
        if reference_config_id is not None:
            reference = self.get_config(reference_config_id, reference_version)
            query_payload = reference.payload
            resolved_type = config_type or reference.config_type
            resolved_tags = _normalize_tags(tags) or reference.tags
            excluded_config_id = reference.config_id
        else:
            if candidate_payload is None:
                raise ValueError("candidate_payload обязателен, если reference_config_id не задан")
            query_payload = dict(candidate_payload)
            resolved_type = config_type
            resolved_tags = _normalize_tags(tags)
            excluded_config_id = None

        candidates = self._store.list_configs(
            limit=self._similarity_pool_limit,
            offset=0,
            config_type=resolved_type,
            tag=None,
        )
        query_flat = _flatten_payload(query_payload)
        query_tags = set(resolved_tags)

        matches: list[SimilarConfigurationMatch] = []
        for candidate in candidates:
            if excluded_config_id is not None and candidate.config_id == excluded_config_id:
                continue

            candidate_flat = _flatten_payload(candidate.payload)
            shared_keys = sorted(set(query_flat) & set(candidate_flat))
            if not shared_keys and not query_tags.intersection(candidate.tags):
                continue

            exact_value_match_count = sum(
                1 for key in shared_keys if _stable_value(query_flat[key]) == _stable_value(candidate_flat[key])
            )
            overlapping_tags = sorted(query_tags.intersection(candidate.tags))
            score = _calculate_similarity_score(
                query_flat=query_flat,
                candidate_flat=candidate_flat,
                exact_value_match_count=exact_value_match_count,
                overlapping_tags=overlapping_tags,
                query_type=resolved_type,
                candidate_type=candidate.config_type,
                query_tag_total=len(query_tags),
                candidate_tag_total=len(candidate.tags),
            )
            if score <= 0:
                continue

            matches.append(
                SimilarConfigurationMatch(
                    config_id=candidate.config_id,
                    version=candidate.version,
                    config_type=candidate.config_type,
                    title=candidate.title,
                    tags=candidate.tags,
                    metadata=candidate.metadata,
                    similarity_score=score,
                    shared_key_count=len(shared_keys),
                    exact_value_match_count=exact_value_match_count,
                    overlapping_tags=overlapping_tags,
                )
            )

        ordered = sorted(
            matches,
            key=lambda item: (
                item.similarity_score,
                item.exact_value_match_count,
                item.shared_key_count,
                item.config_id,
                item.version,
            ),
            reverse=True,
        )
        page_items = ordered[offset : offset + limit]
        return SimilarConfigurationPage(
            items=page_items,
            limit=limit,
            offset=offset,
            total_returned=len(ordered),
        )


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in tags:
        item = raw.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _flatten_payload(payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_payload(value, path))
            continue
        flattened[path] = value
    return flattened


def _stable_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _calculate_similarity_score(
    *,
    query_flat: dict[str, Any],
    candidate_flat: dict[str, Any],
    exact_value_match_count: int,
    overlapping_tags: list[str],
    query_type: str | None,
    candidate_type: str,
    query_tag_total: int,
    candidate_tag_total: int,
) -> float:
    query_keys = set(query_flat)
    candidate_keys = set(candidate_flat)
    shared_keys = query_keys & candidate_keys
    all_keys = query_keys | candidate_keys
    key_overlap = len(shared_keys) / len(all_keys) if all_keys else 0.0
    exact_value_ratio = exact_value_match_count / len(shared_keys) if shared_keys else 0.0

    tag_denominator = len(set(overlapping_tags))
    total_unique_tags = len(set(overlapping_tags))
    if query_tag_total or candidate_tag_total:
        total_unique_tags = len(set(overlapping_tags)) + (query_tag_total - len(set(overlapping_tags))) + (
            candidate_tag_total - len(set(overlapping_tags))
        )
    tag_score = (tag_denominator / total_unique_tags) if total_unique_tags else 0.0

    type_bonus = 0.15 if query_type is not None and query_type == candidate_type else 0.0
    raw_score = (key_overlap * 0.45) + (exact_value_ratio * 0.35) + (tag_score * 0.2) + type_bonus
    return round(min(raw_score, 1.0), 4)
