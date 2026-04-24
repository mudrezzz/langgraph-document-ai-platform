from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from infra.tei import http as tei_http
from infra.tei.embedding_gateway import TeiEmbeddingGateway
from infra.tei.rerank_gateway import TeiRerankGateway


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_tei_embedding_gateway_calls_http_embed_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "payload": json.loads(request.data.decode("utf-8")),
                "authorization": request.headers.get("Authorization"),
            }
        )
        return _FakeResponse([[0.1, 0.2, 0.3]])

    monkeypatch.setattr(tei_http, "urlopen", fake_urlopen)

    gateway = TeiEmbeddingGateway(
        endpoint_url="http://tei.local/embed",
        api_key="secret",
        timeout_sec=7,
    )

    assert gateway.embed("security approval") == [0.1, 0.2, 0.3]
    assert calls == [
        {
            "url": "http://tei.local/embed",
            "timeout": 7,
            "payload": {"inputs": "security approval", "truncate": True},
            "authorization": "Bearer secret",
        }
    ]


def test_tei_embedding_gateway_falls_back_to_hashing_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr(tei_http, "urlopen", fake_urlopen)

    gateway = TeiEmbeddingGateway(
        vector_dim=4,
        endpoint_url="http://tei.local/embed",
        fallback_enabled=True,
    )

    vector = gateway.embed("security approval")

    assert len(vector) == 4
    assert any(value != 0.0 for value in vector)


def test_tei_rerank_gateway_calls_http_rerank_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "payload": json.loads(request.data.decode("utf-8")),
                "authorization": request.headers.get("Authorization"),
            }
        )
        return _FakeResponse(
            [
                {"index": 1, "score": 0.92},
                {"index": 0, "score": 0.14},
            ]
        )

    monkeypatch.setattr(tei_http, "urlopen", fake_urlopen)

    gateway = TeiRerankGateway(
        endpoint_url="http://tei.local/rerank",
        api_key="secret",
        timeout_sec=5,
    )

    scores = gateway.rerank("approval", ["rollback ready", "approval pending"])

    assert scores == [0.14, 0.92]
    assert calls == [
        {
            "url": "http://tei.local/rerank",
            "timeout": 5,
            "payload": {
                "query": "approval",
                "texts": ["rollback ready", "approval pending"],
                "truncate": True,
            },
            "authorization": "Bearer secret",
        }
    ]


def test_tei_rerank_gateway_falls_back_to_lexical_scores_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr(tei_http, "urlopen", fake_urlopen)

    gateway = TeiRerankGateway(
        endpoint_url="http://tei.local/rerank",
        fallback_enabled=True,
    )

    assert gateway.rerank("security approval", ["approval pending", "rollback ready"]) == [0.5, 0.0]
