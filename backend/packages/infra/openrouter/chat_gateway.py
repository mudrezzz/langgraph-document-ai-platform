from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from framework.models.interfaces import IChatModelGateway


class OpenRouterChatModelGateway(IChatModelGateway):
    """Gateway для OpenRouter (OpenAI-compatible chat/completions API)."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_sec: int = 60,
        app_name: str = "langgraph-document-ai-platform",
        app_url: str = "http://localhost",
    ) -> None:
        key = api_key.strip()
        if not key:
            raise ValueError("OPENROUTER_API_KEY обязателен для OpenRouter gateway")

        self._api_key = key
        self._model_name = model_name.strip() or "openai/gpt-4o-mini"
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec
        self._app_name = app_name.strip() or "langgraph-document-ai-platform"
        self._app_url = app_url.strip() or "http://localhost"
        self._last_usage: dict[str, int] = {}

    @property
    def model_name(self) -> str:
        """Возвращает имя модели, используемой gateway."""

        return self._model_name

    @property
    def last_usage(self) -> dict[str, int]:
        """Возвращает usage последнего запроса (если API его отдал)."""

        return dict(self._last_usage)

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> str:
        """Выполняет генерацию текста через OpenRouter chat/completions."""

        metadata_payload = metadata or {}
        payload = {
            "model": self._model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты AI-ассистент для подготовки черновиков release readiness. "
                        "Пиши структурированно и коротко, только на основании evidence контекста."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": float(metadata_payload.get("temperature", 0.2)),
        }

        max_tokens = metadata_payload.get("max_tokens")
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        request = Request(
            url=f"{self._base_url}/chat/completions",
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "HTTP-Referer": self._app_url,
                "X-Title": self._app_name,
            },
            data=json.dumps(payload).encode("utf-8"),
        )

        try:
            with urlopen(request, timeout=self._timeout_sec) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenRouter transport error: {exc}") from exc

        try:
            response_payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenRouter вернул невалидный JSON") from exc

        content = _extract_content(response_payload)
        if not content.strip():
            raise RuntimeError("OpenRouter вернул пустой ответ")
        self._last_usage = _extract_usage(response_payload)

        return content.strip()


def _extract_content(response_payload: dict[str, Any]) -> str:
    """Извлекает итоговый текст из ответа OpenRouter/OpenAI-compatible API."""

    choices = response_payload.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    return ""


def _extract_usage(response_payload: dict[str, Any]) -> dict[str, int]:
    usage = response_payload.get("usage")
    if not isinstance(usage, dict):
        return {}

    prompt_tokens = _as_non_negative_int(usage.get("prompt_tokens"))
    completion_tokens = _as_non_negative_int(usage.get("completion_tokens"))
    total_tokens = _as_non_negative_int(usage.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _as_non_negative_int(raw: Any) -> int:
    if isinstance(raw, int):
        return max(0, raw)
    if isinstance(raw, float):
        return max(0, int(raw))
    return 0
