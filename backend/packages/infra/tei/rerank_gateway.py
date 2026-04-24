from __future__ import annotations

import os
from typing import Any

from framework.models.interfaces import IRerankGateway
from infra.tei.http import post_json


class TeiRerankGateway(IRerankGateway):
    """Gateway rerank для TEI `/rerank` с deterministic fallback для локального контура."""

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: int = 30,
        fallback_enabled: bool = False,
    ) -> None:
        self._endpoint_url = endpoint_url.strip() if endpoint_url else None
        self._api_key = api_key.strip() if api_key else None
        self._timeout_sec = timeout_sec
        self._fallback_enabled = fallback_enabled

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        if not candidates:
            return []
        if not self._endpoint_url:
            return self._lexical_scores(query, candidates)

        try:
            payload = post_json(
                url=self._endpoint_url,
                payload={"query": query, "texts": candidates, "truncate": True},
                timeout_sec=self._timeout_sec,
                api_key=self._api_key,
            )
            return _extract_rerank_scores(payload, candidates_count=len(candidates))
        except Exception:
            if self._fallback_enabled:
                return self._lexical_scores(query, candidates)
            raise

    @classmethod
    def from_env(cls) -> "TeiRerankGateway":
        base_url = os.getenv("TEI_BASE_URL", "").strip().rstrip("/")
        endpoint_url = os.getenv("TEI_RERANK_URL", "").strip()
        if not endpoint_url and base_url:
            endpoint_url = f"{base_url}/rerank"
        return cls(
            endpoint_url=endpoint_url or None,
            api_key=os.getenv("TEI_API_KEY", "").strip() or None,
            timeout_sec=_env_int("TEI_TIMEOUT_SEC", 30),
            fallback_enabled=_env_flag("TEI_FALLBACK_ENABLED", default=False),
        )

    def _lexical_scores(self, query: str, candidates: list[str]) -> list[float]:
        query_tokens = set(query.lower().split())
        scores: list[float] = []
        for candidate in candidates:
            candidate_tokens = set(candidate.lower().split())
            overlap = len(query_tokens.intersection(candidate_tokens))
            denom = max(len(query_tokens), 1)
            scores.append(float(overlap) / float(denom))
        return scores


def _extract_rerank_scores(payload: Any, *, candidates_count: int) -> list[float]:
    if isinstance(payload, dict):
        for key in ("results", "data", "rankings"):
            if key in payload:
                return _extract_rerank_scores(payload[key], candidates_count=candidates_count)
        if "scores" in payload:
            return _scores_from_sequence(payload["scores"], candidates_count=candidates_count)

    if isinstance(payload, list):
        if all(isinstance(item, int | float) for item in payload):
            return _scores_from_sequence(payload, candidates_count=candidates_count)
        if all(isinstance(item, dict) for item in payload):
            scores = [0.0] * candidates_count
            used_indexed_scores = False
            ordered_scores: list[float] = []
            for position, item in enumerate(payload):
                score = _score_from_item(item)
                if score is None:
                    continue
                index = item.get("index")
                if isinstance(index, int) and 0 <= index < candidates_count:
                    scores[index] = score
                    used_indexed_scores = True
                elif position < candidates_count:
                    ordered_scores.append(score)
            if used_indexed_scores:
                return scores
            return _scores_from_sequence(ordered_scores, candidates_count=candidates_count)

    raise RuntimeError("TEI rerank response не содержит scores")


def _score_from_item(item: dict[str, Any]) -> float | None:
    for key in ("score", "relevance_score"):
        if key in item:
            return float(item[key])
    return None


def _scores_from_sequence(value: Any, *, candidates_count: int) -> list[float]:
    if not isinstance(value, list):
        raise RuntimeError("TEI rerank scores должны быть list[float]")
    scores = [float(item) for item in value]
    if len(scores) != candidates_count:
        raise RuntimeError(
            f"TEI rerank вернул {len(scores)} scores для {candidates_count} candidates"
        )
    return scores


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
