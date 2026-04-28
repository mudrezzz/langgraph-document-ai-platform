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
- `0031-canonical-document-store-and-binary-parser-adapters.md`
- `0032-canonical-knowledge-retrieval-source.md`
- `0033-knowledge-block-embedding-index-and-vector-retrieval.md`
- `0034-binary-demo-documents-for-knowledge-factory-acceptance.md`
- `0035-knowledge-indexing-task-lifecycle-api.md`
- `0036-canonical-release-go-no-go-demo-report.md`
- `0037-framework-tool-execution-policy.md`
- `0038-workflow-node-specs-and-subgraph-context.md`
- `0039-workflow-node-events-task-audit.md`
- `0040-workflow-factory-di-builders.md`
- `0041-indexed-canonical-summary-retrieval.md`
- `0042-real-tei-embedding-and-rerank-gateways.md`
- `0043-retrieval-quality-gates.md`
- `0044-retrieval-mcp-indexed-canonical-tools.md`
- `0045-domain-authoring-minimal-service-extraction.md`
- `0046-domain-authoring-research-writer-composition.md`
- `0047-domain-authoring-traceability-and-hitl-feedback-helpers.md`
- `0048-domain-authoring-section-contracts-and-packets.md`
- `0049-domain-authoring-section-authoring-service-baseline.md`
- `0050-template-compiler-and-template-aware-section-contracts.md`
- `0051-template-aware-deterministic-assembly.md`
- `0052-template-catalog-and-assembly-rules-baseline.md`
- `0053-artifact-exporter-baseline-for-template-aware-authoring.md`
- `0054-outline-approval-hitl-point.md`
- `0055-section-authoring-workflow-baseline.md`
- `0056-document-assembly-workflow-baseline.md`
- `0057-persisted-template-library-baseline.md`
- `0058-template-management-api-boundary.md`
- `0059-template-library-mcp-boundary.md`
- `0060-template-library-governance-status-baseline.md`
- `0061-rich-template-assembly-policy-baseline.md`
- `0062-exclusive-published-template-version-policy.md`
- `0063-template-governance-lifecycle-closure.md`

- `0064-async-knowledge-indexing-execution-plane-first-slice.md`
- `0065-async-retrieval-execution-plane-second-slice.md`
- `0066-task-observability-summary-and-execution-metadata.md`
- `0067-structured-logging-and-hitl-observability-summary.md`
- `0068-review-approval-mcp-boundary.md`
- `0069-configuration-library-mcp-skeleton.md`
- `0070-unified-fastmcp-service-policies.md`
- `0071-rbac-boundaries-for-sensitive-api-and-mcp-operations.md`
- `0072-canonical-parser-quality-read-model-baseline.md`
- `0073-scanned-pdf-ocr-fallback-path.md`
- `0074-table-aware-canonical-retrieval-provenance.md`
- `0075-xlsx-parser-baseline-for-canonical-ingestion.md`
- `0076-canonical-document-version-read-model-policy.md`
- `0077-production-indexing-quality-policy-layer.md`
- `0078-pptx-parser-baseline-for-canonical-ingestion.md`
- `0079-pdf-page-provenance-baseline-for-canonical-retrieval.md`
- `0080-pdf-reading-order-and-layout-kind-baseline.md`
- `0081-pdf-table-extraction-baseline-for-canonical-ingestion.md`
- `0082-pdf-form-like-extraction-and-demo-fixture-hardening.md`
- `0083-pdf-extraction-coverage-and-partial-failure-gates.md`
