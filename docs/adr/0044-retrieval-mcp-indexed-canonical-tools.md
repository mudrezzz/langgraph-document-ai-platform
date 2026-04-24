# ADR-0044: Retrieval MCP indexed canonical tools

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

Retrieval MCP начинался как MVP с одним tool `build_evidence_pack`. После ADR-0041..0043 retrieval fabric уже умеет работать с indexed canonical summary/detail layers, real TEI gateways и quality gates, но MCP boundary не давал агентам прямого доступа к production corpus search и source mapping.

Нельзя вводить отдельную MCP-specific retrieval архитектуру: canonical indexing, pgvector search и source lookup уже имеют application/infra boundaries.

## Решение

1. Расширить `FastMcpRetrievalService` tools:
   - `search_summaries`;
   - `search_blocks`;
   - `lookup_source`.
2. Оставить `build_evidence_pack` без изменения внешнего контракта.
3. `search_summaries` использует `CanonicalSummaryVectorRetriever` с injected `embedding_gateway` и `vector_store`.
4. `search_blocks` использует `CanonicalVectorRetriever` с теми же dependencies.
5. `lookup_source` читает canonical document/block metadata через `CanonicalDocumentApplicationService`.
6. Добавить typed MCP schemas в `schemas.mcp.retrieval`.
7. Runtime assembly в `apps/mcp_retrieval/main.py` берет dependencies из existing `ApiContainer`.

## Последствия

Плюсы:

- MCP consumers могут искать indexed canonical summaries/details без запуска full retrieval task;
- source mapping доступен через тот же canonical read boundary, что и ingestion/retrieval reports;
- Retrieval MCP переиспользует production adapters и не создает параллельный search stack;
- старый `build_evidence_pack` MCP contract остается совместимым.

Минусы:

- indexed search tools требуют configured `embedding_gateway` и `vector_store`;
- operational smoke для прямых MCP calls еще нужно выделить отдельным script slice;
- metadata schema vector records все еще остается свободной и должна стабилизироваться вместе с retrieval adapter contracts.
