# ADR-0026: Celery + Redis async authoring and HITL MVP

- Status: Accepted
- Date: 2026-04-21

## Context

After `Increment 20` the authoring flow was multi-step, but executed synchronously in the API request.

This created restrictions:

- long-running authoring blocked HTTP request;
- there was no queue or retry policy for background launching;
- HITL required manual orchestration outside of the API.

## Solution

1. Enter async authoring launch via Celery/Redis:
   - endpoint `POST /api/v1/tasks/authoring/start_async`;
   - worker task `apps.worker.tasks.run_authoring_task`;
- dispatcher policy via `APP_ASYNC_PROVIDER=inline|celery`.
2. Accept stack for queue:
- Celery as task runner;
- Redis as broker/result backend;
- Docker compose for runtime: `backend/docker-compose.async.yml`.
3. Add HITL MVP to the API boundary:
- task status `waiting_human`;
   - `GET /api/v1/tasks/{task_id}/hitl`;
   - `POST /api/v1/tasks/{task_id}/hitl/submit` (`approve|needs_changes|reject`).
4. Maintain backward compatibility:
- synchronous `POST /api/v1/tasks/authoring/start` remains working;
- `inline` dispatcher is used by default in local test/runtime.

## Consequences

Pros:

- long-running authoring can be launched via a queue without blocking the API;
- a basic HITL lifecycle has appeared within the framework of existing API contracts;
- dockerized Redis/Celery circuit can be reproduced on the server similarly to PostgreSQL.

Cons:

- HITL is still one-step (without a full iterative re-review loop);
- retry policy is limited to the worker task level and requires further hardening;
- async plane currently only covers the authoring contour.
