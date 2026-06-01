# ADR-0077: Production indexing quality policy layer

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0072/0073/0075/0076, canonical ingestion already covers parser diagnostics, OCR fallback, table-aware provenance and version-aware read-model. At the same time, the quality gate for indexing remained a local function in `KnowledgeIndexingApplicationService` with hardcoded blocking flags.

This approach limited production hardening:

- policy could not be configured via runtime env without code edits;
- no typed per-document solution (`accepted/rejected`) for partial indexing;
- quality summary was loosely coupled with parser diagnostics and policy metadata.

## Solution

1. Introduce a separate domain-level policy layer `KnowledgeIndexingQualityPolicy` (`domain_docs.indexing.quality_policy`).
2. Policy returns typed aggregated decision `IndexingQualityPolicyDecision` and per-document decisions `IndexingDocumentQualityDecision`:
   - `gate_status`;
- `accepted/rejected` according to documents;
   - `blocking_flags` / `warning_flags`;
   - `accepted_doc_ids` / `rejected_doc_ids`.
3. `KnowledgeIndexingApplicationService` applies policy before persistence workflow:
- rejected documents are not sent to `KnowledgeIndexingWorkflow`;
- embeddings are indexed only for accepted documents;
- parser diagnostics remain available for all parsed documents in task details/reporting.
4. `ApiContainer` collects policy from env:
   - `APP_INDEXING_QUALITY_POLICY_NAME`;
   - `APP_INDEXING_QUALITY_BLOCKING_FLAGS` (CSV);
   - `APP_INDEXING_QUALITY_WARNING_ONLY_FLAGS` (CSV);
   - `APP_INDEXING_ALLOW_RECOVERED_OCR`;
   - `APP_INDEXING_OCR_RECOVERY_BLOCKING_FLAG`;
   - `APP_INDEXING_OCR_RECOVERY_SUCCESS_FLAG`.
5. Public API endpoints do not change; quality fields are expanded additively within `quality_summary`.

## Consequences

Pros:

- quality gate for canonical indexing has become a configurable production policy layer;
- partial-blocking behavior is formalized and is being tested;
- runtime can soften/tighten gates without changing workflow contracts.

Cons:

- policy is currently env-driven and not placed in a separate persisted configuration domain;
- with `gate_status=failed` the task can still end `completed` if there are accepted documents (the operational fail-fast policy can be added as a separate section).
