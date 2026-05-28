# ADR-0014: Task Events API and stabilization demo/smoke runbook

- Status: Accepted
- Date: 2026-04-19

## Context

After implementing `task_events` into the database (`app.task_events`), auditing of status transitions was available only at the SQL level. For operational diagnostics, you need a standard API circuit with pagination and filters.

Additionally, the Linux demo script had unstable JSON parsing of the smoke run result, which prevented manual validation of the reference-case on the server.

## Solution

1. Add endpoint `GET /api/v1/tasks/events`:
- filters: `task_id`, `task_type`, `from`, `to`;
- cursor pagination: `cursor`, `next_cursor`, `has_more`;
- sorting: `created_at DESC, event_id DESC`.
2. Extend the application/registry contract:
- separate page model for task events;
- cursor encode/decode for audit events.
3. Update smoke/demo:
- smoke returns `events_returned` and `events_has_running_to_completed`;
- Linux demo uses secure JSON parsing via environment variable.
4. Update tests:
- unit/integration/e2e to the new endpoint and task event cursors.

## Consequences

Pros:

- lifecycle audit is now available via public API;
- the operator can diagnose transition flow without direct access to SQL;
- the manual demo/smoke cycle on Linux has become more stable and more informative.

Cons:

- the volume of API contracts and support tests has increased;
- for complete observability, aggregated metrics on top of raw task events are still needed.
