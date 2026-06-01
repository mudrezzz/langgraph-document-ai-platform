# ADR-0079: PDF page provenance baseline for canonical retrieval

- Status: Accepted
- Date: 2026-04-28

## Context

After table-aware provenance (ADR-0074), retrieval fabric already explains table rows, but for PDF evidence there was a gap: in indexed retrieval and `lookup_source` it was impossible to consistently see the source page and layout hint (`bbox`/layout source). This reduces the verifiability of evidence in manual smoke/demo and in production traceability.

Also in the PDF parser path, a risk of `block_id` collisions on multi-page documents (local numbering within the page) was detected.

## Solution

1. Fix the page-level provenance baseline for PDF blocks in the existing canonical metadata path:
   - `source_kind=page_block`;
   - `page_number`;
   - `layout_source`;
- `bbox` (when available).
2. Correct the PDF parser to use global numbering `block_id` for the document to eliminate collisions on multi-page PDF.
3. Upload page provenance without a new storage layer:
- in canonical dataset loader;
- in pgvector retrieval metadata mapping;
- in `FastMcpRetrievalService.lookup_source` typed provenance payload.
4. Update release readiness report source mapping so that it shows page refs/layout source for PDF evidence.

## Consequences

Pros:

- evidence from PDF becomes verifiable against the page in report and MCP lookup;
- multi-page PDF ingestion does not lose the uniqueness of the block identity;
- the solution reuses existing canonical/vector/read-model contracts without breaking API changes.

Cons:

- this is baseline only for page-level provenance; fully rich layout semantics (table/image/form/reading order) remain a separate future slice;
- `bbox` remains the best-effort field and depends on the quality of the layout extraction of a particular PDF.
