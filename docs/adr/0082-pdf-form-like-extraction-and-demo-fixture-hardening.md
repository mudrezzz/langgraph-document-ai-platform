# ADR-0082: PDF form-like extraction and demo fixture hardening

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0081, PDF parser already extracts table-like blocks into `extracted_tables`, but release/governance documents often contain form-like key/value sections (approval forms, gate checklists), where the data is not presented as a classic table.

Without explicit support for form-like layouts, some important fields degrade into ordinary paragraph blocks and lose table-row provenance in the retrieval/report path.

## Solution

1. Expand PDF table extraction baseline:
- form-like key/value blocks are also sent to the tabular extraction path;
- table metadata and row metadata get `pdf_table_kind` (`form_like|pipe_table|spaced_table`).
2. Add parser quality flag `pdf_form_like_blocks_detected`.
3. Update the demo fixture `06_audit_summary.pdf` so that it contains:
   - complex table-like release controls;
   - form-like release gate block.
4. Record in tests what the demo PDF gives:
   - `pdf_tables_extracted`;
   - `pdf_form_like_blocks_detected`;
- canonical `table_row` blocks with `pdf_table_kind=form_like`.

## Consequences

Pros:

- retrieval/source mapping gets more accurate provenance for form-like PDF sections;
- demo smoke now checks not only table-like, but also form-like extraction in a real case;
- compatibility of public API/MCP contracts is maintained.

Cons:

- form-like extraction is still heuristic and requires future hardening for non-standard templates;
- partial extractions are possible in complex multi-line forms.
