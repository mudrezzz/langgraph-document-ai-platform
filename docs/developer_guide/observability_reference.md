# Observability Reference

Update date: 2026-04-30
Status: Active (P1 handbook)

Source of truth: `backend/apps/api/main.py`, `backend/packages/schemas/api/contracts.py`, `backend/packages/application/task_service.py`, `backend/packages/application/authoring_service.py`.

## 1. Endpoint map

Task observability:

- `GET /api/v1/tasks/events`
- `GET /api/v1/tasks/events/summary`
- `GET /api/v1/tasks/observability/summary`

HITL observability:

- `GET /api/v1/hitl/actions`
- `GET /api/v1/hitl/observability/summary`

## 2. Task events model

`TaskEventItem` key fields:

- `task_id`, `task_type`
- `from_status`, `to_status`
- `from_current_node`, `to_current_node`
- `event_payload`
- `created_at`

Events include both status transitions and workflow-node audit payload.

## 3. Task events summary

`TaskEventsSummaryResponse`:

- `total_events`
- `unique_tasks`
- `transitions[]`: units `from_status -> to_status`
- `daily[]`, `weekly[]`:
  - `bucket_start`
  - `total_events`
  - `unique_tasks`

Purpose:

- lifecycle stability check;
- confirmation of the presence of expected transition paths;
- input for release-gate checks (RG-series).

## 4. Task observability summary

`TaskObservabilityResponse` includes:

- current counters:
  - `total_tasks`, `queued_tasks`, `running_tasks`, `waiting_human_tasks`, `completed_tasks`, `failed_tasks`, `async_tasks`
- latency:
  - `avg_duration_ms`, `p50_duration_ms`, `p95_duration_ms`, `max_duration_ms`
  - `avg_queue_wait_ms`, `p50_queue_wait_ms`, `p95_queue_wait_ms`
- SLA:
  - `duration_sla_threshold_ms`, `duration_sla_breaches_total`
  - `queue_wait_sla_threshold_ms`, `queue_wait_sla_breaches_total`
- quality/token aggregates:
  - `avg_selected_block_count`, `avg_confidence`
  - `tasks_with_unresolved_gaps`, `unresolved_gaps_total`
  - `llm_tokens_prompt_total`, `llm_tokens_completion_total`, `llm_tokens_total`
- slices:
  - `daily[]`, `weekly[]`
  - `statuses[]`
  - `task_types[]`

## 5. HITL observability summary

`HitlObservabilityResponse`:

- volume:
  - `total_actions`, `unique_tasks`
- state counters:
  - `pending_actions`, `queued_actions`, `processing_actions`, `completed_actions`
- decision mix:
  - `approve_total`, `needs_changes_total`, `reject_total`
- loop metrics:
  - `avg_iteration`, `max_iteration`
- actor load:
  - `reviewers[]` (`reviewer`, `total`, decision breakdown)

## 6. SLA interpretation rules

SLA thresholds are read from env:

- `APP_SLA_TASK_DURATION_MS`
- `APP_SLA_QUEUE_WAIT_MS`

Interpretation:

- if env is empty/invalid/`<=0`, threshold is considered `None` and breach-check is disabled;
- breach counters are counted only when the threshold is active;
- `p50/p95` — nearest-rank percentile semantics for stable dashboard interpretation.

## 7. Practical query patterns

Diagnosis of a problematic queue:

1. `GET /api/v1/tasks/observability/summary?task_type=authoring_pack`
2. Check `queue_wait` metrics and SLA breaches.
3. Check `GET /api/v1/tasks/events?task_type=authoring_pack&to_status=failed`.

HITL bottleneck diagnostics:

1. `GET /api/v1/hitl/observability/summary?status=pending`
2. Check `reviewers[]` and `max_iteration`.
3. Check `GET /api/v1/hitl/actions?decision=needs_changes`.

## 8. Related documents

- `docs/developer_guide/api_reference.md`
- `docs/developer_guide/release_reproducible_flow.md`
- `docs/developer_guide/env_config_reference.md`
