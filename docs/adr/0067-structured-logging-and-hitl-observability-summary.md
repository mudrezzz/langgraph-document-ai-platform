# ADR-0067: Structured Runtime Logging and HITL Observability Summary

- Status: Accepted
- Date: 2026-04-26

## Context

After ADR-0066, the execution plane already became observable through the task registry and `/api/v1/tasks/observability/summary`, but two spaces remained:

- the operator lacked structured runtime log lines for API, Celery worker and HITL continuation path;
- reviewer/HITL activity was available only as a list of actions via `GET /api/v1/hitl/actions`, without an aggregated summary for dashboard/manual smoke.

Increment 29 requires a small production-compatible slice that does not introduce a separate telemetry stack and uses already existing read-model/persistence adapters.

## Solution

1. Add a general helper `infra.logging.runtime` for one-line JSON logging on stdlib `logging`.
2. Log key execution events at three runtime points:
   - FastAPI start/submit endpoints;
   - Celery worker task start/completion/failure;
   - authoring/HITL orchestration events (`queued`, `waiting_human`, `processing`, `completed`, `rejected`).
3. Leave the correlation through the existing `task.details.correlation_id`, `dispatch_id`, `queue_name`, rather than introducing a separate trace context store.
4. Extend `HitlActionStore` with the `summarize_actions(...)` method and add the `GET /api/v1/hitl/observability/summary` endpoint.
5. Build reviewer/HITL aggregates on top of the existing `app.hitl_actions` read-model:
   - `total_actions`, `unique_tasks`;
   - pending/queued/processing/completed counts;
   - decision mix (`approve`, `needs_changes`, `reject`);
   - `avg_iteration`, `max_iteration`;
   - reviewer load breakdown.

## Consequences

Pros:

- the operator receives machine-readable JSON logs without an external logging platform;
- troubleshooting async/HITL paths is simplified due to single fields `task_id`, `correlation_id`, `dispatch_id`, `queue_name`;
- reviewer activity becomes visible through the aggregated API without a new table/materialized view.

Cons:

- logging is currently limited to API/worker/authoring paths and does not cover all MCP runtime entrypoints;
- HITL summary is built based on the current read-model layer and does not yet contain periodic SLA buckets;
- for full-fledged production dashboards, a separate metrics/log pipeline may be needed later.
