# ADR Reading Map

Дата обновления: 2026-04-30  
Статус: Active (P2 navigation)

Цель: ускорить навигацию по ADR для внешнего разработчика.

## 1. Fast path by role

## Integrator (минимальный контекст)

Прочитать в порядке:

1. `0001-layer-boundaries.md`
2. `0005-api-boundary-and-task-lifecycle.md`
3. `0020-multifile-ingestion-and-retrieval-mcp-mvp.md`
4. `0036-canonical-release-go-no-go-demo-report.md`
5. `0090-unified-release-gate-smoke-matrix.md`
6. `0091-final-release-decision-contract.md`
7. `0092-external-developer-documentation-surface.md`

## Contributor (расширение framework/domain)

Прочитать в порядке:

1. `0001-layer-boundaries.md`
2. `0002-langgraph-runtime-boundary.md`
3. `0029-framework-hardening-and-extension-guide.md`
4. `0037-framework-tool-execution-policy.md`
5. `0038-workflow-node-specs-and-subgraph-context.md`
6. `0039-workflow-node-events-task-audit.md`
7. `0040-workflow-factory-di-builders.md`

## Maintainer (операции и release governance)

Прочитать в порядке:

1. `0008-postgres-pgvector-baseline-persistence.md`
2. `0013-runtime-profiles-task-history-cursor-and-status-audit.md`
3. `0066-task-observability-summary-and-execution-metadata.md`
4. `0067-structured-logging-and-hitl-observability-summary.md`
5. `0089-observability-sla-percentiles-and-time-buckets.md`
6. `0090-unified-release-gate-smoke-matrix.md`
7. `0091-final-release-decision-contract.md`

## 2. Topic map

Runtime / workflows:

- `0002`, `0007`, `0037`, `0038`, `0039`, `0040`

Persistence / data model:

- `0008`, `0011`, `0016`, `0017`, `0076`

Knowledge indexing / canonical ingestion:

- `0030`, `0031`, `0035`, `0072`..`0087`

Retrieval quality / provenance:

- `0032`, `0033`, `0041`, `0042`, `0043`, `0044`, `0074`, `0079`, `0080`

Authoring / HITL / templates:

- `0023`..`0028`, `0045`..`0063`, `0068`

MCP boundaries:

- `0020`, `0021`, `0022`, `0059`, `0068`, `0069`, `0070`, `0071`

Observability / release gates:

- `0066`, `0067`, `0088`, `0089`, `0090`, `0091`

## 3. How to use with docs set

1. Сначала пройти `docs/developer_guide/public_contract_surface.md`.
2. Потом выбрать role-based ADR fast path.
3. Для deep dive перейти в `docs/adr/README.md` и topic map above.

Это снижает риск читать ADR в случайном порядке и пропустить ключевые контракты.
