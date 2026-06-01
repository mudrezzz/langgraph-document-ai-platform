# ADR-0075: XLSX parser baseline for canonical ingestion

- Status: Accepted
- Date: 2026-04-27

## Context

After DOCX table extraction and table-aware retrieval provenance, the system can already work well with table evidence. The next production-relevant format for such evidence is `.xlsx`: approval trackers, risk registers, release matrices and control checklists often come in Excel.

You cannot build a separate ingestion path for spreadsheet documents. XLSX must be in the same canonical/indexing/retrieval loop as DOCX/PDF/JSON.

## Solution

1. Add `.xlsx` to supported extensions canonical parser.
2. Implement baseline parser on `openpyxl`:
- workbook sheets become structural sections;
- sheet header + rows are extracted as canonical table;
- table rows become `table_row` blocks;
- metadata includes `sheet_name`.
3. Binary demo input expand with real fixture `08_release_tracker.xlsx`.
4. Do not introduce a separate spreadsheet-specific retrieval stack: XLSX reuse the existing `CanonicalDocument`, `KnowledgeIndexingApplicationService`, vector indexing and retrieval provenance path.

## Consequences

Pros:

- ingestion covers another frequent enterprise format;
- tabular evidence from Excel is immediately available for retrieval/MCP/reporting;
- the solution naturally continues the already introduced table-aware provenance path.

Cons:

- baseline parser is currently focused on sheet-level tabular extraction, without merged-cells/formatting/formulas semantics;
- `.xls` and rich workbook semantics remain outside the current slice.
