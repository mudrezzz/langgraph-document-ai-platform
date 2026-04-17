from __future__ import annotations

from typing import Any

from framework.models.interfaces import IChatModelGateway


class VllmChatModelGateway(IChatModelGateway):
    """Скелет gateway для self-hosted vLLM."""

    def __init__(self, model_name: str = "mock-vllm-model") -> None:
        self._model_name = model_name

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> str:
        # На текущем этапе возвращаем предсказуемый ответ-заглушку.
        return f"[{self._model_name}] {prompt}"