# ADR-0074: Table-aware canonical retrieval provenance

- Status: Accepted
- Date: 2026-04-27

## Context

After DOCX hardening, table rows are already included in the canonical corpus as `table_row` blocks. Retrieval and MCP search are able to find such blocks, but the source mapping remained too flat: the consumer saw only `doc_id/block_id`, without an explicit answer that the evidence came from the table, from which table and which row.

This reduces the production value of retrieval fabric: the found approval status is difficult to quickly check manually and difficult to explain in the report/traceability path.

## Solution

1. Do not introduce a separate provenance store or a new retrieval architecture.
2. Save table-aware provenance in the existing canonical/vector metadata path for `table_row` blocks:
   - `source_kind=table_row`;
   - `table_id`, `table_title`, `table_columns`;
   - `row_index`, `row_values`;
   - `section_title`.
3. `CanonicalVectorRetriever` and dataset loader should pass these fields to `RetrievedBlock.metadata`.
4. `FastMcpRetrievalService.lookup_source` must return typed provenance payload and table payload for table-backed evidence.
5. Release readiness report should be able to show table-aware source mapping for tabular evidence blocks.

## Consequences

Pros:

- the evidence found can be explained and verified as a specific line of the approval matrix;
- MCP lookup/source mapping becomes more suitable for downstream authoring/traceability;
- the solution reuses existing canonical documents, knowledge blocks and vector metadata.

Cons:

- metadata schema vector records are becoming richer and require careful compatibility;
- the report layer currently shows the aggregated table provenance, and not the full cell-level trace.
