from __future__ import annotations

import hashlib
import math
import os
from typing import Any

from framework.models.interfaces import IEmbeddingGateway
from infra.tei.http import post_json


class TeiEmbeddingGateway(IEmbeddingGateway):
    """Gateway embeddings для TEI `/embed` с deterministic fallback для локального контура."""

    def __init__(
        self,
        vector_dim: int = 1536,
        *,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: int = 30,
        fallback_enabled: bool = False,
    ) -> None:
        self._vector_dim = vector_dim
        self._endpoint_url = endpoint_url.strip() if endpoint_url else None
        self._api_key = api_key.strip() if api_key else None
        self._timeout_sec = timeout_sec
        self._fallback_enabled = fallback_enabled

    def embed(self, text: str) -> list[float]:
        if not self._endpoint_url:
            return self._hashing_vector(text)

        try:
            payload = post_json(
                url=self._endpoint_url,
                payload={"inputs": text, "truncate": True},
                timeout_sec=self._timeout_sec,
                api_key=self._api_key,
            )
            return _extract_embedding(payload)
        except Exception:
            if self._fallback_enabled:
                return self._hashing_vector(text)
            raise

    @classmethod
    def from_env(cls, *, vector_dim: int = 1536) -> "TeiEmbeddingGateway":
        base_url = os.getenv("TEI_BASE_URL", "").strip().rstrip("/")
        endpoint_url = os.getenv("TEI_EMBEDDING_URL", "").strip()
        if not endpoint_url and base_url:
            endpoint_url = f"{base_url}/embed"
        return cls(
            vector_dim=vector_dim,
            endpoint_url=endpoint_url or None,
            api_key=os.getenv("TEI_API_KEY", "").strip() or None,
            timeout_sec=_env_int("TEI_TIMEOUT_SEC", 30),
            fallback_enabled=_env_flag("TEI_FALLBACK_ENABLED", default=False),
        )

    def _hashing_vector(self, text: str) -> list[float]:
        tokens = text.lower().split()
        vector = [0.0] * self._vector_dim
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._vector_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        if not tokens:
            return vector

        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 0:
            return vector
        return [value / norm for value in vector]


def _extract_embedding(payload: Any) -> list[float]:
    if isinstance(payload, dict):
        if "embedding" in payload:
            return _as_float_vector(payload["embedding"])
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and "embedding" in first:
                return _as_float_vector(first["embedding"])
        if "embeddings" in payload:
            return _extract_embedding(payload["embeddings"])

    if isinstance(payload, list):
        if not payload:
            return []
        if all(isinstance(item, int | float) for item in payload):
            return [float(item) for item in payload]
        first = payload[0]
        if isinstance(first, list):
            return _as_float_vector(first)
        if isinstance(first, dict) and "embedding" in first:
            return _as_float_vector(first["embedding"])

    raise RuntimeError("TEI embedding response не содержит embedding vector")


def _as_float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        raise RuntimeError("TEI embedding vector должен быть list[float]")
    return [float(item) for item in value]


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default
