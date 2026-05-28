# ADR-0076: Canonical document version read-model policy

- Status: Accepted
- Date: 2026-04-27

## Context

By Increment 31, canonical ingestion already retains production-relevant document formats and indexed retrieval corpus. But the persistence policy was still effectively single-version per `doc_id`: repeated indexing overwrote the document row and latest knowledge blocks, and there was no historical version lookup.

This is not enough for production retrieval fabric. Needed:

1. stable canonical identity by `doc_id`;
2. latest-by-default reading without breaking existing APIs and retrieval path;
3. explicit version lookup for source tracing and controlled re-index semantics.

## Solution

1. Save existing latest-read contract:
- `app.canonical_documents` and `app.knowledge_blocks` remain the latest snapshot by `doc_id`.
2. Add separate history read-model:
   - `app.canonical_document_versions`;
   - `app.knowledge_block_versions`.
3. `CanonicalDocumentApplicationService` works according to policy:
   - `get_document(doc_id)` -> latest version;
   - `get_document(doc_id, version=...)` -> explicit historical version;
   - `list_documents(...)` -> latest only;
   - `list_versions(doc_id, ...)` -> history list.
4. Knowledge indexing request receives explicit `document_version`.
5. Re-index semantics:
- latest snapshot and latest vectors replace are identified by `doc_id`;
- historical canonical versions are saved and available for explicit lookup;
- vector index remains latest-oriented, without a separate historical vector plane.
6. Retrieval MCP `lookup_source` accepts optional `version` and can also resolve historical `block_ref` in `doc_id:version:block_id` format.

## Consequences

Pros:

- backward compatibility is maintained for existing canonical retrieval and MCP flows;
- audit/source-trace path to historical canonical versions appears;
- re-index semantics become explicit and predictable.

Cons:

- historical retrieval search via pgvector is not yet supported as a separate search plane;
- vector index reflects only the latest snapshot, so historical lookup is available for source resolution, and not for general semantic search.
