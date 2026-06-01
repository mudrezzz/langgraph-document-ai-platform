# ADR-0085: PDF multi-line form and rotated-layout hardening

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0084, the quality gate takes into account form-confidence, but extraction baseline for PDF is still vulnerable to two common production cases:

1. form-like fields with multi-line values;
2. rotated text blocks (90/270°), which can participate in table/form evidence.

Without this, the parser either loses part of the field value or does not give an explicit signal that the extraction was performed using a rotated layout.

## Solution

1. Extend form-like parser:
- support keys with spaces and hyphens;
- support multi-line continuation values;
- save normalized key/value pairs in the existing `form_like` tabular path.
2. Add rotated layout hint to PDF block metadata:
- `rotated_text=true|false` on page blocks and table_row blocks;
- detection via `Page.get_text("dict")` line direction (`dir`).
3. Add parser quality flag `pdf_rotated_layout_detected` and diagnostics metadata:
   - `rotated_table_candidates_total`;
   - `rotated_table_candidates_extracted`.
4. Update demo fixture `06_audit_summary.pdf`:
   - multi-line form value;
- rotated form-like line for manual smoke/demo checking.

## Consequences

Pros:

- better coverage of real form-like PDF cases without changing public APIs;
- rotated-layout path becomes observable in parser diagnostics;
- demo/smoke confirm hardening in manual mode.

Cons:

- rotated hint is a lightweight heuristic, not a full-fledged layout/OCR pipeline;
- merged/complex rotated tables remain the next stage of hardening.
