#ADR-0018: Advanced Task Events and Summary Read-Model Filters

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 12` the API already provided a raw audit stream of status transitions via `GET /api/v1/tasks/events`, but it was not enough for operational analysis:

- filtering by transition direction (`from_status`, `to_status`);
- compact aggregated summary without client post-aggregation.

For manual diagnostics on an Ubuntu server, it is important to quickly answer questions like:

- how many transitions `running -> completed` were there;
- how many tasks fell into this type of transition during the selected interval.

## Solution

1. Expand `GET /api/v1/tasks/events` with filters:
   - `from_status`;
   - `to_status`.
2. Add a new endpoint `GET /api/v1/tasks/events/summary`:
- supports filters `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`;
- returns `total_events`, `unique_tasks` and transition aggregates `from_status -> to_status`.
3. Add indexes for statuses in `task_events`:
- migration of `0005_task_events_status_filter_indexes.sql`.
4. Update smoke/demo scripts:
- smoke JSON includes the fields `events_summary_total`, `events_summary_unique_tasks`, `events_summary_has_running_to_completed`.

## Consequences

Pros:

- The audit layer API has become suitable for operational analytics without heavy post-processing;
- smoke/runbook covers not only raw events, but also aggregated checks.

Cons:

- summary endpoint is currently building on-the-fly aggregates (no materialized tables/dashboards);
- for large volumes, a separate read-model and periodic precompute jobs will be required.
