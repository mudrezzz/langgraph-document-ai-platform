# ADR-0088: Execution Metrics MVP (day/week events + token/quality observability)

- Status: Accepted
- Date: 2026-04-29

## Context

By the end of Increment 31, we already had `task_events` and endpoint `GET /api/v1/tasks/observability/summary`, but there were still spaces for runtime operations:

- in the summary of events there were no periodic buckets (day/week) for fast trends;
- task observability did not include quality/token metrics retrieval/authoring path;
- there was no unified `duration_ms` in task lifecycle details.

For Increment 32, you need a minimal metrics slice without a separate telemetry database and without breaking API changes.

## Solution

1. Expand `GET /api/v1/tasks/events/summary` with aggregates:
- `daily[]` and `weekly[]` with structure:
     - `bucket_start`;
     - `total_events`;
     - `unique_tasks`.
2. Expand `GET /api/v1/tasks/observability/summary` and per-task-type breakdown:
   - quality metrics:
     - `avg_selected_block_count`;
     - `avg_confidence`;
     - `tasks_with_unresolved_gaps`;
     - `unresolved_gaps_total`;
   - token metrics:
     - `llm_tokens_prompt_total`;
     - `llm_tokens_completion_total`;
     - `llm_tokens_total`.
3. In `TaskApplicationService`, automatically calculate `duration_ms` if `started_at` and `completed_at|failed_at` are present.
4. In the authoring LLM path, add `llm_tokens_*` to draft metadata and task details:
- use provider usage if available;
- in the absence of usage, use lightweight fallback estimate.

## Consequences

Pros:

- the operational layer receives day/week trends and basic quality/token metrics without new infrastructure;
- API extended additively and backward-compatible;
- runtime details become more suitable for SLA/quality dashboards of the next slice.

Cons:

- token usage for some gateways may be evaluative;
- aggregates are still considered on top of the task registry/state payload, and not on top of the dedicated metrics warehouse.
