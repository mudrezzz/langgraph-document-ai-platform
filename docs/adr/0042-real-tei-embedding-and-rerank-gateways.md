# ADR-0042: Real TEI embedding and rerank gateways

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

ADR-0033 ввел локальный deterministic `TeiEmbeddingGateway`, а retrieval pipeline уже использовал `TeiRerankGateway`. Это сохраняло testability, но не закрывало production boundary: embeddings и rerank должны уметь ходить в self-hosted Hugging Face Text Embeddings Inference service.

TEI exposes HTTP endpoints for embeddings and ranking. Для проекта важно подключить эти endpoints без изменения workflow contracts и без обязательной внешней зависимости в unit/e2e тестах.

## Решение

1. `TeiEmbeddingGateway` поддерживает HTTP POST в `/embed`:
   - payload: `{"inputs": text, "truncate": true}`;
   - поддерживаются common response shapes: raw vector, list-of-vectors, `{"embedding": ...}`, OpenAI-like `{"data": [{"embedding": ...}]}`.
2. `TeiRerankGateway` поддерживает HTTP POST в `/rerank`:
   - payload: `{"query": query, "texts": candidates, "truncate": true}`;
   - поддерживаются response shapes со scores и indexed ranking records.
3. Env contract:
   - `TEI_BASE_URL` строит `TEI_BASE_URL/embed` и `TEI_BASE_URL/rerank`;
   - `TEI_EMBEDDING_URL` и `TEI_RERANK_URL` переопределяют endpoints явно;
   - `TEI_API_KEY` передается как Bearer token;
   - `TEI_TIMEOUT_SEC` задает timeout;
   - `TEI_FALLBACK_ENABLED=true` разрешает deterministic fallback при transport/API ошибке.
4. Если endpoint не задан, gateway работает в deterministic local mode.
5. Если endpoint задан и fallback выключен, ошибки TEI пробрасываются наружу.
6. `ApiContainer` собирает embedding и rerank gateways из env.
7. `RetrievalApplicationService` принимает injected `rerank_gateway`, поэтому authoring path использует тот же rerank adapter через retrieval service.

## Последствия

Плюсы:

- production retrieval fabric может использовать self-hosted TEI без изменения application/workflow contracts;
- локальные тесты остаются deterministic и не требуют TEI контейнера;
- strict production behavior возможен через выключенный fallback;
- authoring получает rerank через существующий retrieval service path.

Минусы:

- пока нет external TEI integration test, потому что CI/runtime не поднимает TEI service;
- response parsing намеренно tolerant, но schema должна быть закреплена в отдельном adapter contract после выбора конкретных моделей.
