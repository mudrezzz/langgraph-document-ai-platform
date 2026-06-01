# ADR-0033: Knowledge block embedding index and vector retrieval

- Status: Accepted
- Date: 2026-04-23

## Context

ADR-0032 connected the Retrieval Fabric to the canonical `knowledge_blocks`, but the detail retrieval remained read-model + lexical/in-memory path. The target retrieval fabric must use indexed corpus, embeddings and pgvector.

## Solution

1. Extend `KnowledgeIndexingApplicationService` optional embedding indexing:
- embedding gateway builds a vector for each canonical content block;
- vector store writes embedding in `app.embeddings`;
- metadata associates vector with `block_ref`, `doc_id`, `block_id`, source path, document type, tags and block text.
2. Make a local `TeiEmbeddingGateway` 1536-dimensional deterministic hashing-vector compatible with the baseline `VECTOR(1536)`.
3. Extend `PgVectorStoreAdapter` with the `query_similar(...)` method:
- fallback cosine similarity for unit/smoke;
- PostgreSQL path via pgvector cosine distance.
4. Add `CanonicalVectorRetriever` for canonical detail retrieval.
5. Leave summary retrieval through section summaries and lexical scorer; vector path is applied to detail blocks.

## Consequences

Pros:

- canonical path now goes `documents -> knowledge_blocks -> embeddings -> vector detail retrieval -> evidence`;
- smoke shows `embeddings_indexed` and `retrieval_backend=pgvector`;
- PostgreSQL path uses the existing `app.embeddings` table.

Cons:

- the local embedding gateway remains a deterministic stub, and not a real TEI HTTP client;
- summary layer is not yet vectorized separately;
- metadata stores the text of the block to restore the retrieval result, which needs to be reviewed for large corpora.
