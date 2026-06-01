# ADR-0032: Canonical knowledge retrieval source

- Status: Accepted
- Date: 2026-04-23

## Context

ADR-0031 added canonical store and `knowledge_blocks`, but retrieval continued to use only demo dataset loaders (`case_dataset_id`, `case_dataset_path`, `case_dataset_dir`). This left a gap between the Knowledge Factory output and the Retrieval Fabric.

## Solution

1. Add loader `load_canonical_knowledge_dataset(...)`, which builds:
- summary blocks from `CanonicalDocument.section_summaries`;
- detail blocks from `app.knowledge_blocks`.
2. Extend `build_retrieval_workflow(...)` with `knowledge_source="canonical"` mode.
3. Extend `RetrievalApplicationService` and `task_context` API:
   - `knowledge_source: "canonical"`;
- `canonical_doc_ids: list[str] | str` to constrain the hull.
4. Save the existing default path through demo case datasets for backward compatibility.
5. Add smoke `smoke_canonical_retrieval.sh/.ps1`, which does:
   - canonical indexing demo input;
- retrieval on top of the canonical store;
- checking evidence pack and `knowledge_source=canonical`.

## Consequences

Pros:

- Knowledge Factory output is used directly by Retrieval Fabric for the first time;
- demo corpus can go through the path `documents -> canonical documents -> knowledge_blocks -> evidence pack`;
- API contract remains backward-compatible.

Cons:

- retrieval by canonical store while lexical/in-memory after reading read-model;
- pgvector/embedding write path is not connected yet;
- canonical source smoke runs indexing and retrieval in one process for the fallback circuit.
