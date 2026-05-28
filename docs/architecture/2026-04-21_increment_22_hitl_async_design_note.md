# Design Note: Increment 22 (Iterative HITL + Async Continuation)

Date: 2026-04-21

## 1. Problem statement

After `Increment 21` HITL was one-step:

- `waiting_human -> submit -> completed|failed`;
- there was no iterative loop `needs_changes -> rewrite -> re-review -> waiting_human`;
- `hitl/submit` could synchronously complete the pipeline in the API context;
- there was no explicit idempotency protection for repeated submission of the same solution.

For a production-like circuit, you need a managed async lifecycle and a predictable policy for iterations.

## 2. Scope / Out of scope

Scope:

- add an iterative HITL loop with a limit on the number of iterations;
- convert continuation after `hitl/submit` to async dispatcher plane (inline/celery);
- enter idempotency and optimistic guard (`expected_iteration`) for `hitl/submit`;
- expand read-model HITL status (`iteration`, `max_iterations`, `deadline`, `pending_action`);
- update smoke/demo/tests/docs for the new lifecycle.

Out of scope:

- separate reviewer UI;
- complex role model (RBAC/SSO);
- external event broker (Kafka/NATS) and distributed workflow orchestration beyond Celery.

## 3. Which contracts are changing

API:

- `POST /api/v1/tasks/{task_id}/hitl/submit`:
- added `idempotency_key`, `expected_iteration`;
- submit can now return not only `completed`, but also `queued/running/waiting_human`.
- `GET /api/v1/tasks/{task_id}/hitl`:
- added `current_iteration`, `max_iterations`, `deadline_at`, `can_submit`, `pending_action_id`;
- reviewer actions now contain `action_id`, `iteration`, `status`, `idempotency_key`.

Internal async contract:

- `AuthoringAsyncDispatcher` extended with enqueue HITL-action continuation method;
- Celery worker received a separate task for continuation after submit.

Schemes/migrations:

- SQL migrations were not added in this increment (MVP stores HITL history in checkpoint/task details).

## 4. Risks and compatibility

Compatibility:

- existing endpoints are saved;
- `idempotency_key` and `expected_iteration` are optional;
- `start`/`start_async` contracts do not break.

Risks:

- repeated submits without idempotency key can create new action events;
- if there is an error queuing a continuation, a rollback is needed in `waiting_human` (implemented);
- policy on `needs_changes` at the final iteration can cause 409 (expected behavior, requires explicit approve/reject).

## 5. Test plan

Unit:

- async submit + continuation via inline dispatcher;
- `needs_changes -> iteration+1`;
- idempotency replay on `idempotency_key`;
- blocking `needs_changes` when max iterations is reached.

Integration:

- API flow `start_async -> waiting_human -> submit -> poll -> completed`;
- iterative flow with two iterations and replay submit.

E2E:

- FastAPI e2e (in-process uvicorn);
- Postgres-backed e2e;
- Docker e2e for real `PostgreSQL + Redis + Celery`.

Smoke/manual:

- async smoke updated for decision sequence (`--hitl-decision-sequence needs_changes,approve`).

## 6. Rollout plan

1. Expand API/state and dispatcher contract schemes.
2. Add worker-task for HITL continuation.
3. Change submit to async continuation with rollback when enqueue-error.
4. Add iterative loop policy and idempotency.
5. Update tests (unit/integration/e2e/docker-e2e).
6. Update runbook/docs/ADR.

## 7. Definition of Done

- iterative HITL lifecycle works: at least 2 iterations (`needs_changes -> waiting_human(iteration+1) -> approve`);
- continuation after submit is executed via async dispatcher (inline/celery);
- submit supports idempotency and expected_iteration guard;
- green tests: unit + integration + e2e + docker async e2e;
- documentation updated (`README`, `Architecture Overview`, `ADR`, manual smoke/runbook).
