"""DeviceSearchAgent configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeviceSearchConfig:
    requester: str = "agent-examples-device-search"
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "")
    )
    openrouter_model: str = field(
        default_factory=lambda: os.environ.get(
            "OPENROUTER_MODEL", "openai/gpt-4o-mini"
        )
    )
    openrouter_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
    )
