# ADR-0080: PDF reading-order and layout-kind baseline

- Status: Accepted
- Date: 2026-04-28

## Context

After ADR-0079, page-level provenance for PDF appeared in retrieval, but evidence still remained too rough: there was not enough baseline signal about the order of reading blocks and a sign of the table structure inside the page.

For manual checking in demo/report and for downstream retrieval/rerank, you need at least two additional fields:

- `reading_order_index` (block order on the page);
- `layout_kind` (`paragraph|table_like`).

## Solution

1. Add reading-order normalization to the PDF parser path:
- sorting layout blocks by `y/x`;
- record `reading_order_index` in metadata.
2. Add lightweight layout heuristics:
- `layout_kind=table_like`, if the block is similar to a table one (`|`-separators, key-value row pattern, multi-column spacing);
- otherwise `layout_kind=paragraph`.
3. Add `pdf_table_like_blocks_detected` to parser quality flags if there is at least one `table_like` block.
4. Add new fields without changing public APIs:
   - canonical retrieval dataset;
   - pgvector metadata mapping;
   - MCP `lookup_source` typed provenance;
   - release report canonical source mapping.

## Consequences

Pros:

- evidence from PDF becomes better explainable: the page, order and type of block layout are visible;
- in report/MCP you can clearly separate paragraph vs table-like evidence;
- the solution remains compatible with current contracts.

Cons:

- `table_like` is a heuristic and does not replace full-fledged table extraction;
- reading order best-effort and depends on the quality of block coordinates of a particular PDF.
