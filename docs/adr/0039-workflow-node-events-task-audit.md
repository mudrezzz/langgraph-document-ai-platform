# ADR-0039: Workflow node events in task audit

- Status: Accepted
- Date: 2026-04-24

## Context

ADR-0038 added `WorkflowNodeSpec` and `WorkflowExecutionContext`, but observability was still only at the task status transition level. For production troubleshooting, this is not enough: the task can remain in the `running` status, and the operator needs to see which graph node started, ended or crashed.

A new database schema is not required: `app.task_events` already contains `from_current_node`, `to_current_node` and JSONB `event_payload`.

## Solution

1. Add framework event contract:
   - `WorkflowNodeEventRecord`;
   - `WorkflowNodeEventSink`.
2. `BaseWorkflow` emits events around each node:
   - `started`;
   - `completed`;
   - `failed`.
3. Add application adapter `TaskWorkflowNodeEventSink`.
4. Map node events to the existing table `app.task_events`:
- `from_status` and `to_status` are equal to the current task status;
- `from_current_node` is equal to the current `task.current_node`;
- `to_current_node` is equal to the name of the workflow node;
   - `event_payload.event_kind = "workflow_node"`;
- payload contains `workflow_name`, `node_name`, `node_status`, `is_resume`, `correlation_id`, `metadata`, `error`.
5. Connect node event sink to retrieval and knowledge-indexing workflows.
6. Do not change the external API:
- `GET /api/v1/tasks/events` already returns `event_payload`;
- filters `from_status/to_status/task_id/task_type` continue to work.

## Consequences

Pros:

- node-level audit appears without a new migration and without changing API schemas;
- status transition events and node events live in the same cursor/read-model API;
- demo/smoke can check graph-node activity through existing task events endpoint;
- the next observability slice can build aggregates on top of `event_payload.event_kind`.

Cons:

- summary endpoint currently groups all events by `from_status/to_status`, so node events like `running -> running` can increase `total_events`;
- there is no separate `event_kind` filter in the API yet, so as not to change the external contract in this slice.
