# ADR-0083: PDF extraction coverage and partial-failure gates

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0082, the parser already extracts table/form-like structures from PDF, but without explicitly assessing the completeness of the extraction. In production retrieval, this is a risk: partial retrieval may look like normal success, although some table-like candidates are not recognized.

## Solution

1. Add coverage metrics for PDF table extraction path:
   - `pdf_table_candidates_total`;
   - `pdf_table_candidates_extracted`;
   - `pdf_table_rows_extracted`;
   - `pdf_table_rows_failed`;
   - `pdf_table_coverage_percent`.
2. Enter the quality flag `pdf_table_extraction_partial` for partial extraction (`candidates_failed > 0`).
3. Post metrics in `parser_quality.issues` metadata:
- for `pdf_tables_extracted`;
- for `pdf_table_extraction_partial`.
4. Aggregate at the indexing quality summary level:
   - `documents_with_pdf_table_partial`;
   - `documents_with_pdf_form_like`.

## Consequences

Pros:

- partial extraction becomes observable and is explicitly signaled in the quality/read-model path;
- manual and automatic quality assessment of retrieval evidence using PDF becomes more transparent;
- the solution maintains compatibility of existing API/MCP contracts.

Cons:

- coverage baseline is still based on heuristic table-like candidates;
- does not solve deep complex layout cases (merged/rotated tables), only makes them visible.
