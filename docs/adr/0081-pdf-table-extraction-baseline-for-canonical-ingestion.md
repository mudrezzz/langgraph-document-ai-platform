# ADR-0081: PDF table extraction baseline for canonical ingestion

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0080, the PDF path already gave `reading_order_index` and `layout_kind`, but this remained a heuristic hint layer. Production retrieval/traceability requires the same level of source precision that already exists for DOCX/XLSX: tables in `extracted_tables` and rows as canonical `table_row` blocks.

## Solution

1. Add baseline table extraction to PDF parser:
- for `layout_kind=table_like` try to assemble a table specification;
- support lightweight patterns: `|`-separators, key-value rows, multi-column spacing;
- if successful, create `CanonicalTable` (`PDF-T-*`) and `table_row` blocks.
2. Check provenance for PDF table rows:
   - `source_kind=table_row`;
   - `table_id`, `row_index`;
   - `page_number`, `reading_order_index`, `layout_kind`, `layout_source`, `bbox`.
3. Add parser quality flag `pdf_tables_extracted`.
4. Do not introduce a separate PDF-table store: reuse the existing canonical store + retrieval metadata path.

## Consequences

Pros:

- retrieval/source mapping for PDF can now refer to a specific table row, and not just to the page block;
- unification with DOCX/XLSX table-aware path;
- without breaking changes in API/MCP contracts.

Cons:

- extraction remains the best-effort heuristic baseline and does not cover complex merged/rotated tables;
- for complex PDFs you will need a separate hardening slice (specialized table detector/parser).
