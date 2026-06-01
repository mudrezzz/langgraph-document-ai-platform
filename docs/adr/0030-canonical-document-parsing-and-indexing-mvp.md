# ADR-0030: Canonical document parsing and indexing MVP

- Status: Accepted
- Date: 2026-04-23

## Context

After `Increment 24` the framework layer received an extension guide and contract tests. The next major GAP to the target architecture is Knowledge Factory: canonical document model, parsing, quality flags and indexing workflow.

The complete target layer includes PDF/DOCX/OCR, separate canonical documents/knowledge blocks tables and pgvector-backed indexing. The first backend/framework slice requires a smaller vertical step, which can be tested on an existing release go/no-go demo.

## Solution

1. Extend `schemas.documents` with typed canonical contracts:
   - `CanonicalStructureNode`;
   - `CanonicalContentBlock`;
   - `CanonicalTable`;
   - `CanonicalSectionSummary`;
   - `CanonicalDocument`.
2. Add `domain_docs` as a separate domain package.
3. Implement `CanonicalDocumentParser` for text-like MVP formats:
   - `.md`;
   - `.txt`;
   - `.json`.
4. Add `KnowledgeIndexingWorkflow` on top of `BaseWorkflow`.
5. On the first slice, save the canonical payload through the existing `DocumentApplicationService` and `app.documents`, without a new migration.
6. Add smoke `smoke_knowledge_indexing.sh/.ps1`, which indexes the current release go/no-go multifile demo input.

## Consequences

Pros:

- the first reusable `domain_docs` layer appeared;
- canonical ingestion can be tested without FastAPI and without a new database schema;
- the current demo script received Knowledge Factory smoke.

Cons:

- PDF/DOCX/OCR are not yet implemented;
- canonical documents and knowledge blocks are not yet separated into separate tables;
- retrieval does not yet read the indexed canonical corpus directly.
