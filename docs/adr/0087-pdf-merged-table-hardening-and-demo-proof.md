# ADR-0087: PDF merged-table hardening and demo proof contract

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0085, the parser already extracted form-like and rotated PDF structures, but complex pipe-like tables with wrapped/merged rows remained partially lost. Also, for manual acceptance, the demo lacked an explicit machine-verified proof that the extraction worked on the real `06_audit_summary.pdf`.

## Solution

1. Strengthen pipe-table extraction:
- save empty cells (do not collapse them prematurely);
- recognize markdown separator rows (`| --- | --- |`);
- merge continuation rows into the previous row (merged/wrapped cell values).
2. Add demo proof payload to smoke path:
- direct smoke (`smoke_knowledge_indexing.py`) returns `pdf_demo_proof` for `06_audit_summary.pdf`;
- API smoke (`smoke_knowledge_indexing_api.py`) also returns `pdf_demo_proof` via task details.
3. In `pdf_demo_proof` record the basic acceptance signs:
   - `found`;
   - `doc_id`;
- `tables_total` / `table_rows_total` (or `blocks_total` in API path);
   - `has_pdf_tables_extracted`;
   - `has_pdf_form_like_blocks_detected`;
   - `has_pdf_rotated_layout_detected`.

## Consequences

Pros:

- increased stability of extraction for real PDF tables with wrapped rows;
- manual demo smoke receives explicit proof of functionality for a specific PDF fixture;
- the solution is additive and does not break API/MCP contracts.

Cons:

- merged-table heuristics are still baseline and require further tuning on a real body;
- `pdf_demo_proof` is aimed at a demo fixture and does not replace a full-fledged production quality dashboard.
