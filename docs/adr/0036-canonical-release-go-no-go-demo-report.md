# ADR-0036: Canonical release go/no-go demo report

Date: 2026-04-23

Status: Accepted

## Context

After ADR-0035, Knowledge Indexing became a full-fledged task lifecycle operation, but the human-readable `release_readiness_report.md` in the multi-file demo was still built around the old `case_dataset_dir` retrieval path. This left the demo artifact with a weak acceptance signal for Knowledge Factory: the report did not show canonical quality flags, source path mapping and the fact that the retrieval uses a canonical source.

## Solution

1. Translate `demo_release_go_no_go_multifile_case.sh/.ps1` to canonical route:
   - `POST /api/v1/tasks/knowledge-indexing/start`;
- `POST /api/v1/tasks/retrieval/start` with `knowledge_source=canonical`;
- `canonical_doc_ids` from indexing task details.
2. Extend `build_release_readiness_report.py`:
- accept indexing status payload;
- show `Canonical Quality Summary`;
- build `Canonical Source Mapping` from evidence block metadata.
3. Keep the same output artifact path:
   - `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`.

## Consequences

- The main multi-file demo now checks the full path `documents -> canonical documents -> knowledge_blocks -> embeddings -> retrieval -> report`.
- Manual check sees which `.md/.txt/.json/.docx/.pdf` files were included in the evidence pack.
- Quality flags became part of the demo artifact, and not just JSON-smoke.
- The old `case_dataset_dir` retrieval path remains as a quick fallback in `smoke_retrieval_api.sh`, but is not the main multi-file demo.
