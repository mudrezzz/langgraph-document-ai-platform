# ADR-0064: Async Knowledge Indexing on Unified Execution Plane first slice

- Status: Accepted
- Date: 2026-04-26

## Context

After Increment 28, the async execution plane already existed, but was actually tied only to the authoring/HITL path via Celery + Redis. Increment 29 requires making the execution plane common to all long-running workflows, without introducing a new parallel architecture.

Knowledge Indexing was the next logical candidate:

- this is a long workflow with file parsing, canonical persistence and embedding indexing;
- it already has a task lifecycle API (`POST /api/v1/tasks/knowledge-indexing/start`);
- he already writes task events and workflow node events;
- in the release demo, it is indexing that is the input to the production retrieval fabric.

Leaving indexing only synchronous would mean preserving the special-case execution behavior and preventing the queue/Celery from covering the ingestion path.

## Solution

1. Extend the existing async dispatcher contract with a new port `KnowledgeIndexingAsyncDispatcher`.
2. Add two runtime implementations without new architecture branch:
- `InlineKnowledgeIndexingAsyncDispatcher` for dev/test;
- `CeleryKnowledgeIndexingAsyncDispatcher` for production-like async execution.
3. Extend `KnowledgeIndexingApplicationService` methods:
   - `start_task_async(request, dispatcher=...)`;
   - `run_existing_task(task_id, request)`.
4. Add API endpoint `POST /api/v1/tasks/knowledge-indexing/start_async`.
5. Perform queued execution through an existing worker app:
   - Celery task `apps.worker.tasks.run_knowledge_indexing_task`;
- queue `knowledge-indexing` via env `APP_CELERY_INDEXING_QUEUE`.
6. Leave sync endpoint `POST /api/v1/tasks/knowledge-indexing/start` without breaking changes.
7. For Docker/Celery runtime, normalize `source_paths` from host-path to worker-visible `/workspace/...` path, since the worker runs in a container with a bind mount volume.
8. Extend worker image parser dependencies (`python-docx`, `PyMuPDF`) so that async knowledge indexing supports the same `.docx/.pdf` fixtures as sync path.

## Consequences

Pros:

- execution plane ceases to be authoring-only and begins to cover the ingestion path;
- release/demo loop can now run canonical indexing through the same queue/Celery runtime as other long-running workflows;
- task lifecycle and workflow node audit remain the same for the sync/async path;
- the public sync contract has been preserved, and async path has been added as a compatible extension.

Cons:

- unified execution plane has not yet been generalized to retrieval and quality evaluation;
- worker path normalization is currently implemented as a pragmatic mapping for the docker-compose volume layout `/workspace`, and not as a general storage abstraction;
- Docker worker image is now required to contain parser dependencies Knowledge Factory.
