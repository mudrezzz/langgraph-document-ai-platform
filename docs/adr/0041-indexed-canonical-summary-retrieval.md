# ADR-0041: Indexed canonical summary retrieval

- Status: Accepted
- Date: 2026-04-24

## Context

Canonical retrieval could already use pgvector for detail blocks through `CanonicalVectorRetriever`, but the summary layer remained in-memory: `load_canonical_knowledge_dataset(...)` built `RetrievedBlock` from `section_summaries`, and `HierarchicalRAGPipeline` looked for them through `InMemoryRetriever`.

For production retrieval fabric this is incomplete: the summary/detail hierarchy must work from the indexed corpus, otherwise the large corpus will require canonical documents to be loaded into memory before each retrieval task.

## Solution

1. Knowledge Indexing writes embeddings for two types of canonical artifacts:
- `knowledge_block_embedding` for `content_blocks`;
- `knowledge_summary_embedding` for `section_summaries`.
2. Add `CanonicalSummaryVectorRetriever` on top of the same `PgVectorStoreAdapter`.
3. Save `CanonicalVectorRetriever` for detail layer.
4. In `build_retrieval_workflow(... knowledge_source="canonical" ...)` use pgvector summary/detail retrievers if `embedding_gateway` and `vector_store` are available.
5. Leave in-memory fallback for demo/bootstrap mode and tests without vector store.
6. Separate summary/detail records via `metadata.kind`, and return the usual `RetrievedBlock` with `metadata.block_kind` to the outside.

## Consequences

Pros:

- hierarchical retrieval no longer requires an in-memory summary layer when indexed canonical corpus;
- summary/detail records live in one vector store and are filtered through metadata;
- current APIs and workflow state contracts do not change;
- demo fallback remains compatible.

Cons:

- summary embeddings increase the volume of `app.embeddings`;
- metadata schema for vector records is still free and requires further stabilization in retrieval adapter contracts.
