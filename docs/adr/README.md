# ADR Index

## Правило ведения

При каждом инкременте:

1. Обновляется статус существующих ADR при изменении решения.
2. Добавляется новый ADR, если принято новое архитектурное решение.
3. В `System_Architecture_Overview.md` указывается связь с новыми ADR.

## Список ADR

- `0001-layer-boundaries.md`
- `0002-langgraph-runtime-boundary.md`
- `0003-typed-contracts-and-state-policy.md`
- `0004-adapter-wiring-and-vertical-slice.md`
- `0005-api-boundary-and-task-lifecycle.md`
- `0006-api-smoke-and-integration-tests.md`
- `0007-langgraph-runtime-in-base-workflow.md`
- `0008-postgres-pgvector-baseline-persistence.md`
- `0009-reference-case-and-fastapi-e2e-policy.md`
- `0010-postgres-local-profile-and-e2e-startup-resilience.md`
- `0011-persistent-task-registry-and-task-history-api.md`
- `0012-linux-server-migration-and-bash-operations-profile.md`
- `0013-runtime-profiles-task-history-cursor-and-status-audit.md`
- `0014-task-events-api-and-demo-runbook-hardening.md`
- `0015-smoke-keep-server-mode-for-post-smoke-api-validation.md`
- `0016-langgraph-postgres-checkpointer-runtime-integration.md`
- `0017-dedicated-langgraph-checkpoint-storage.md`
- `0018-task-events-status-filters-and-summary-read-model.md`
- `0019-file-based-demo-release-go-no-go-pipeline.md`
- `0020-multifile-ingestion-and-retrieval-mcp-mvp.md`
- `0021-repository-mcp-mvp-and-document-tools.md`
- `0022-artifact-writer-mcp-mvp-and-postgres-artifact-store.md`
- `0023-authoring-api-flow-and-task-artifact-traceability-link.md`
- `0024-openrouter-llm-authoring-draft-gateway.md`
- `0025-multistep-authoring-workflow-and-section-traceability.md`
- `0026-celery-redis-async-authoring-and-hitl-mvp.md`
- `0027-iterative-hitl-loop-and-async-submit-continuation.md`
- `0028-hitl-actions-persistence-and-read-model-api.md`
- `0029-framework-hardening-and-extension-guide.md`
- `0030-canonical-document-parsing-and-indexing-mvp.md`
