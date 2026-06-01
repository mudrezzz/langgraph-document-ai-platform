# ADR-0031: Canonical document store and binary parser adapters

- Status: Accepted
- Date: 2026-04-23

## Context

ADR-0030 added the first Knowledge Factory MVP: canonical contracts, `domain_docs`, parser `.md/.txt/.json` and `KnowledgeIndexingWorkflow`. But the canonical payload was saved through a common document repository boundary, and not through a separate read-model layer. Also, the target specification requires support for PDF/DOCX parsing by standard libraries.

## Solution

1. Add a separate persistence/read-model layer:
   - `app.canonical_documents`;
   - `app.knowledge_blocks`;
- migration `backend/migrations/0009_canonical_knowledge_store.sql`.
2. Add `CanonicalDocumentApplicationService`.
3. Add `PostgresCanonicalDocumentStore` with in-memory fallback for dev/test.
4. Switch `KnowledgeIndexingApplicationService` to canonical store boundary.
5. Expand parser boundary with `.docx` and `.pdf` formats.
6. Use lazy imports:
- `python-docx` for DOCX;
- `PyMuPDF` for PDF.
7. Fix the dependencies in `backend/pyproject.toml`, but leave adapter-level errors explicit if the runtime environment has not yet installed the optional package.

## Consequences

Pros:

- canonical documents and derived knowledge blocks are no longer mixed with the generic document repository;
- retrieval fabric will be able to read `app.knowledge_blocks` as the next step;
- binary parser boundary is implemented without forcing PDF/DOCX tests to be executed in an environment without dependencies.

Cons:

- new migration `0009` required;
- PDF/DOCX parsing is still basic and does not include OCR, tables or rich layout extraction;
- retrieval has not yet been switched to canonical knowledge blocks.
