# ADR-0066: Task Observability Summary and Execution Metadata on Unified Plane third slice

- Status: Accepted
- Date: 2026-04-26

## Context

After ADR-0064 and ADR-0065, the unified async execution plane already covers authoring, knowledge indexing and retrieval, but it is still inconvenient for the operator to parse the runtime state of the system:

- `GET /api/v1/tasks` shows only individual task rows;
- `GET /api/v1/tasks/events` and `/summary` show transitions, but do not give dashboard-friendly current-state aggregates;
- manual smoke/demo confirmed only the fact of completion, and not the execution trace (`queue`, `dispatch`, `correlation`, queue wait).

Increment 29 requires a minimal observability slice on top of the existing read-model layer, without a new telemetry subsystem.

## Solution

1. Expand task lifecycle details execution metadata with fields:
   - `correlation_id`;
   - `async_provider`;
   - `queue_name`;
   - `queued_at`;
   - `started_at`;
   - `completed_at`/`failed_at`;
   - `queue_wait_ms`.
2. Leave these fields in the existing `details` payload of the task, without introducing a separate table.
3. Add a new read-model endpoint `GET /api/v1/tasks/observability/summary`.
4. Count aggregates on top of the existing task registry, and not on top of the raw queue backend:
   - `total_tasks`;
- counts by current statuses (`queued`, `running`, `waiting_human`, `completed`, `failed`);
   - `async_tasks`;
   - `avg_duration_ms`, `max_duration_ms`, `avg_queue_wait_ms`;
- breakdown by `task_type`.
5. Manual smoke/demo scripts should output execution metadata and observability summary so that the operator can check the unified execution plane manually.

## Consequences

Pros:

- the execution plane becomes observable without the new metrics/logging infrastructure;
- the operator sees not only transitions, but also the current summary of tasks and queue wait behavior;
- The API remains backward-compatible: new fields are added as an extension of the existing details/read-model payloads.

Cons:

- aggregates are built according to the state of the task registry, and not according to the real internal metrics of the queue broker;
- structured JSON logging and cross-service log correlation are not yet closed;
- for production dashboards, as the load increases, a separate pre-aggregated read model may be needed.
