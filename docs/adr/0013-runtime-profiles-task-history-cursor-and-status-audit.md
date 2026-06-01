# ADR-0013: Runtime Profiles, Cursor Task History and audit of status transitions

- Status: Accepted
- Date: 2026-04-19

## Context

After `Increment 8` the task history was already stored in PostgreSQL (`app.tasks`), but architectural gaps remained:

- fallback persistence could be used even in the production circuit;
- `GET /api/v1/tasks` supported only `limit/offset` without filters and cursors;
- there was no separate audit trail of task status transitions.

To operate on an Ubuntu server, you need a more strict runtime outline and convenient page-by-page navigation through the history without `offset` drift.

## Solution

1. Enter runtime profiles via `APP_RUNTIME_PROFILE`:
- valid values: `dev`, `stage`, `prod`;
- fallback persistence is allowed only in `dev/stage`;
- in `prod` the absence of `APP_DB_DSN` leads to an error and blocks in-memory fallback.
2. Update the contract `GET /api/v1/tasks`:
- filters `status`, `task_type`, `from`, `to`;
- cursor pagination `cursor -> next_cursor` + flag `has_more`;
- sorting: `updated_at DESC, task_id DESC`.
3. Add an audit of status transitions:
- SQL migration `0003_task_events.sql`;
- table `app.task_events`;
- events are written when a task is created and every time `status` changes.
4. Update smoke/tests:
- unit/integration/e2e coverage of a new contract;
- smoke scripts have been transferred to a filtered history query.

## Consequences

Pros:

- the production circuit has become stricter: critical persistence cannot be launched without a database;
- task history is scaled through cursor pagination and is less susceptible to `offset` problems;
- an audit trail of the task life cycle at the status level has appeared.

Cons:

- the `/api/v1/tasks` contract has changed (offset pagination is no longer the main path);
- audit events are saved for now, but a separate public endpoint for reading events is still needed in the next increment.
