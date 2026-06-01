# ADR-0042: Real TEI embedding and rerank gateways

- Status: Accepted
- Date: 2026-04-24

## Context

ADR-0033 introduced a local deterministic `TeiEmbeddingGateway`, and the retrieval pipeline was already using `TeiRerankGateway`. This preserved testability, but did not close the production boundary: embeddings and rerank should be able to go to the self-hosted Hugging Face Text Embeddings Inference service.

TEI exposes HTTP endpoints for embeddings and ranking. It is important for the project to connect these endpoints without changing workflow contracts and without mandatory external dependencies in unit/e2e tests.

## Solution

1. `TeiEmbeddingGateway` supports HTTP POST to `/embed`:
   - payload: `{"inputs": text, "truncate": true}`;
- common response shapes are supported: raw vector, list-of-vectors, `{"embedding": ...}`, OpenAI-like `{"data": [{"embedding": ...}]}`.
2. `TeiRerankGateway` supports HTTP POST to `/rerank`:
   - payload: `{"query": query, "texts": candidates, "truncate": true}`;
- response shapes with scores and indexed ranking records are supported.
3. Env contract:
- `TEI_BASE_URL` builds `TEI_BASE_URL/embed` and `TEI_BASE_URL/rerank`;
- `TEI_EMBEDDING_URL` and `TEI_RERANK_URL` override endpoints explicitly;
- `TEI_API_KEY` is passed as Bearer token;
- `TEI_TIMEOUT_SEC` sets timeout;
- `TEI_FALLBACK_ENABLED=true` allows deterministic fallback in case of transport/API error.
4. If endpoint is not specified, gateway operates in deterministic local mode.
5. If endpoint is specified and fallback is disabled, TEI errors are forwarded out.
6. `ApiContainer` collects embedding and rerank gateways from env.
7. `RetrievalApplicationService` accepts injected `rerank_gateway`, so the authoring path uses the same rerank adapter via the retrieval service.

## Consequences

Pros:

- production retrieval fabric can use self-hosted TEI without changing application/workflow contracts;
- local tests remain deterministic and do not require a TEI container;
- strict production behavior is possible with fallback disabled;
- authoring receives rerank through an existing retrieval service path.

Cons:

- there is no external TEI integration test yet, because CI/runtime does not support TEI service;
- response parsing is intentionally tolerant, but schema must be enshrined in a separate adapter contract after selecting specific models.
