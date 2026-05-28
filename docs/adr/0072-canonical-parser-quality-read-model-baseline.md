# ADR-0072: Canonical parser quality read-model baseline

- Status: Accepted
- Date: 2026-04-27

## Context

Increment 31 begins Knowledge Factory Hardening. Previously, canonical ingestion only stored a flat `quality_flags` list at the document level and an aggregated `quality_summary` list at the indexing task details level.

This is enough for MVP gate `passed|warning|failed`, but not enough for production hardening:

- it is impossible to understand parser family and extraction mode from the document;
- you cannot separate info/warning/blocking parser issues;
- it’s difficult to see which documents contain tables, need OCR or have lost their structure;
- the following slices (`OCR`, rich layout, DOCX tables/lists, `.xlsx/.pptx`) will add extraction behavior without a measurable read-model layer.

## Solution

1. Add typed parser quality contracts to `schemas.documents`:
   - `ParserQualityIssue`;
   - `ParserQualitySummary`.
2. Expand `CanonicalDocument` with the `parser_quality` field without changing the existing ingestion API contract.
3. `CanonicalDocumentParser` is now required to fill in:
   - `parser_family`;
   - `extraction_mode`;
   - counts (`blocks/headings/lists/tables/pages`);
- typed issues and mirrored `flags`.
4. Existing `quality_flags` are saved as a backward-compatible coarse signal and continue to be used by the current indexing quality gate.
5. `KnowledgeIndexingApplicationService` throws parser diagnostics into task details and aggregated `quality_summary`:
   - `parser_families`;
   - `extraction_modes`;
   - `parser_issues_total`;
   - `documents_with_tables`;
   - `documents_needing_ocr`.
6. Retrieval/reporting surfaces receive `parser_quality` only as read-model metadata, without a separate parser-specific runtime branch.

## Consequences

Pros:

- a production-compatible measurement layer for parser hardening appears;
- smoke/demo/report can now show parser diagnostics based on documents;
- future OCR/table/layout slices can be implemented on top of the existing typed quality read-model;
- existing APIs and quality gate semantics remain compatible.

Cons:

- quality gate still relies on `quality_flags`, and not on the fully configurable production policy layer;
- parser quality counters are currently limited to the current `.md/.txt/.json/.docx/.pdf` adapters;
- extracted tables/layout blocks are not yet saved as separate canonical entities.
