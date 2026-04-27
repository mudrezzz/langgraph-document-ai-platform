from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ConfigurationLibraryMcpConfigItem(BaseModel):
    """Versioned configuration artifact exposed through MCP."""

    config_id: str
    version: str
    config_type: str = "generic"
    title: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfigurationLibraryMcpUpsertConfigInput(BaseModel):
    """Input contract for creating/updating one config artifact."""

    config_id: str
    version: str = "1"
    config_type: str = "generic"
    title: str | None = None
    actor: str | None = None
    roles: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ConfigurationLibraryMcpUpsertConfigOutput(ConfigurationLibraryMcpConfigItem):
    """Response after config upsert."""


class ConfigurationLibraryMcpGetConfigInput(BaseModel):
    """Input contract for loading one config by id/version."""

    config_id: str
    version: str | None = None


class ConfigurationLibraryMcpGetConfigOutput(ConfigurationLibraryMcpConfigItem):
    """Response after loading one config."""


class ConfigurationLibraryMcpListConfigsInput(BaseModel):
    """Input contract for listing stored configs."""

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    config_id: str | None = None
    config_type: str | None = None
    tag: str | None = None


class ConfigurationLibraryMcpListConfigsOutput(BaseModel):
    """Paged list of configuration records."""

    items: list[ConfigurationLibraryMcpConfigItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int


class ConfigurationLibraryMcpCompareConfigsInput(BaseModel):
    """Input contract for deterministic config diff."""

    left_config_id: str
    right_config_id: str
    left_version: str | None = None
    right_version: str | None = None


class ConfigurationLibraryMcpChangedValueItem(BaseModel):
    """One changed payload value between compared configs."""

    key: str
    left_value: Any = None
    right_value: Any = None


class ConfigurationLibraryMcpCompareConfigsOutput(BaseModel):
    """Comparison result between two config records."""

    left: ConfigurationLibraryMcpConfigItem
    right: ConfigurationLibraryMcpConfigItem
    shared_keys: list[str] = Field(default_factory=list)
    left_only_keys: list[str] = Field(default_factory=list)
    right_only_keys: list[str] = Field(default_factory=list)
    changed_values: list[ConfigurationLibraryMcpChangedValueItem] = Field(default_factory=list)
    same_value_keys: list[str] = Field(default_factory=list)


class ConfigurationLibraryMcpFindSimilarConfigsInput(BaseModel):
    """Input contract for deterministic similar-config search."""

    reference_config_id: str | None = None
    reference_version: str | None = None
    candidate_payload: dict[str, Any] | None = None
    config_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_reference_or_payload(self) -> "ConfigurationLibraryMcpFindSimilarConfigsInput":
        if self.reference_config_id is None and self.candidate_payload is None:
            raise ValueError("Нужно передать reference_config_id или candidate_payload")
        return self


class ConfigurationLibraryMcpSimilarConfigItem(BaseModel):
    """Similarity match in MCP output."""

    config_id: str
    version: str
    config_type: str = "generic"
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity_score: float
    shared_key_count: int
    exact_value_match_count: int
    overlapping_tags: list[str] = Field(default_factory=list)


class ConfigurationLibraryMcpFindSimilarConfigsOutput(BaseModel):
    """Paged similar-config search result."""

    items: list[ConfigurationLibraryMcpSimilarConfigItem] = Field(default_factory=list)
    limit: int
    offset: int
    total_returned: int
