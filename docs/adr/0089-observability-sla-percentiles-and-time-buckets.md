# ADR-0089: Observability SLA percentiles and time buckets

- Status: Accepted
- Date: 2026-04-29

## Context

After ADR-0088, we had quality/token execution metrics and day/week `task_events` aggregates, but there was not enough for SLA control:

- percentiles (`p50/p95`) by duration and queue wait;
- breach counters relative to SLA thresholds;
- periodic day/week slices for the SLA state of the execution plane.

We need to close this gap without a new telemetry database and without breaking API contracts.

## Solution

1. Expand `TaskObservabilitySummary` and API `GET /api/v1/tasks/observability/summary`:
   - overall:
     - `p50_duration_ms`, `p95_duration_ms`;
     - `p50_queue_wait_ms`, `p95_queue_wait_ms`;
     - `duration_sla_threshold_ms`, `queue_wait_sla_threshold_ms`;
     - `duration_sla_breaches_total`, `queue_wait_sla_breaches_total`;
   - per task type:
- the same percentile/breach fields.
2. Add periodic observability slices:
- `daily[]` and `weekly[]`:
     - `bucket_start`;
     - `total_tasks`, `completed_tasks`, `failed_tasks`, `waiting_human_tasks`;
     - `duration_sla_breaches_total`, `queue_wait_sla_breaches_total`.
3. SLA thresholds taken from env:
   - `APP_SLA_TASK_DURATION_MS`;
   - `APP_SLA_QUEUE_WAIT_MS`;
- values ​​`<=0` or invalid values ​​are treated as `disabled`.
4. Leave the calculations at the current task read-model level (`app.tasks`/fallback), without new storage.

## Consequences

Pros:

- basic SLA visibility of the execution plane for ops/release gate appears;
- day/week dynamics and percentile metrics are available through an existing API;
- the solution is additive, backward compatibility is preserved.

Cons:

- metrics are calculated according to the current task read-model, and not according to raw queue/runtime telemetry;
- for a large volume of tasks in the future, a pre-aggregated materialized layer may be needed.
