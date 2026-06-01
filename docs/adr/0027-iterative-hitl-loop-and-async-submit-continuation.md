# ADR-0027: Iterative HITL loop and async continuation after submit

- Status: Accepted
- Date: 2026-04-21

## Context

In `Increment 21` HITL was one-step:

- reviewer submit brought the task to the final (completed/failed) in one transition;
- continuation could be executed synchronously in the API context;
- there was no protected idempotency mechanism for repeated submits;
- there was no explicit limit on `needs_changes` iterations.

Extending the authoring process requires a controlled iterative loop and predictable async behavior.

## Solution

1. Introduce an iterative HITL lifecycle:
- state fields: `hitl_iteration`, `hitl_max_iterations`, `hitl_deadline_at`, `hitl_pending_action_id`;
- policy: `needs_changes` is allowed only while `iteration < max_iterations`;
- `needs_changes` triggers rewrite + reviewer rerun and returns the task to `waiting_human` with `iteration + 1`.
2. Place continuation after `hitl/submit` in the async dispatcher plane:
- new dispatcher method `enqueue_hitl_action`;
- new Celery worker task `run_authoring_hitl_action`;
- rollback in `waiting_human` on enqueue error.
3. Add optimistic/idempotent submit protection:
- `idempotency_key` for dedup repeated requests;
- `expected_iteration` to protect against stale submit.
4. Extend HITL read-model:
- `GET /api/v1/tasks/{task_id}/hitl` returns iteration/max/deadline/can_submit/pending_action + extended action history.

## Consequences

Pros:

- reviewer loop has become iterative and controlled;
- The API is not blocked by finalization after submit in an async profile;
- reduced risk of double processing due to network retries.

Cons:

- state logic has become more complex (more transitions and edge-cases);
- without a separate SQL table, the HITL audit is stored inside checkpoint/details (MVP);
- policy `needs_changes` at the final iteration requires an explicit approve/reject and may return 409.
