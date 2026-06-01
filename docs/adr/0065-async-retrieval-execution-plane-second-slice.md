# ADR-0065: Async Retrieval on Unified Execution Plane second slice

- Status: Accepted
- Date: 2026-04-26

## Context

After ADR-0064, the unified execution plane already covers authoring/HITL and knowledge indexing, but the retrieval task lifecycle remained synchronous with the special-case path. This created an architectural gap:

- retrieval is a mandatory step in almost all production scenarios;
- task/events/checkpoint contracts are already uniform, but queue-based execution for retrieval was missing;
- manual demo and Docker/Celery e2e could not verify that the execution plane actually covers the main retrieval workload.

For Increment 29, the following minimum slice is needed: transfer retrieval to the same async plane without introducing a new runtime layer and without breaking changes sync API.

## Solution

1. Extend the existing async dispatcher plane with a new port `RetrievalAsyncDispatcher`.
2. Add runtime implementations:
- `InlineRetrievalAsyncDispatcher` for dev/test;
- `CeleryRetrievalAsyncDispatcher` for production-like queue execution.
3. Extend `RetrievalApplicationService` methods:
   - `start_async(request, dispatcher=...)`;
   - `run_existing_task(task_id, request)`.
4. Leave the sync endpoint `POST /api/v1/tasks/retrieval/start` without changing the external contract.
5. Add a compatible API extension: `POST /api/v1/tasks/retrieval/start_async`.
6. Perform queued execution through an existing worker app:
   - Celery task `apps.worker.tasks.run_retrieval_task`;
- separate queue `retrieval` via env `APP_CELERY_RETRIEVAL_QUEUE`.
7. Extend docker-compose async worker so that one worker listens to the `authoring`, `knowledge-indexing`, `retrieval` queues.
8. Add operational smoke/demo scripts so that async retrieval can be checked manually in the PostgreSQL/Celery loop.

## Consequences

Pros:

- unified execution plane now covers all three main long-running workflows: retrieval, knowledge indexing, authoring;
- sync API is preserved, and async retrieval is added as a backward-compatible extension;
- task lifecycle, checkpoint and task events remain the same for sync/async retrieval paths;
- manual smoke and Docker/Celery e2e now confirm queue-backed retrieval path, and not just authoring/indexing.

Cons:

- authoring still calls retrieval synchronously within its pipeline, that is, nested async orchestration has not yet been introduced;
- the observability layer is currently limited to existing task events/status details and does not add separate queue metrics;
- worker topology remains pragmatic single-worker/multi-queue layout for docker-compose acceptance contour.
