# ADR-0011: Persistent TaskRegistry and Task History API

- Status: Accepted
- Date: 2026-04-18

## Context

After `Increment 6` the lifecycle of tasks was stored only in `InMemoryTaskRegistry`. This did not survive the restart of the process API and did not allow getting the task history through the public API.

For observability and diagnostics, a minimum stable circuit is needed:

- store the lifecycle of tasks in PostgreSQL;
- have an endpoint for reading task history.

## Solution

1. Enter `PostgresTaskRegistry` in the infra persistence layer.
2. Add SQL migration `0002_task_registry.sql` with the `app.tasks` table.
3. Switch the API DI container from `InMemoryTaskRegistry` to `PostgresTaskRegistry`.
4. Extend `TaskApplicationService` with the `list_tasks` method.
5. Add endpoint `GET /api/v1/tasks` and typed response `TaskHistoryResponse`.
6. Add test coverage:
- unit tests registry;
- integration tests endpoint history;
- e2e history tests (including PostgreSQL loop).

## Consequences

Pros:

- the lifecycle of tasks is saved in PostgreSQL and survives the restart of the API process;
- a standard API contract for task history has appeared;
- smoke/e2e scripts now check not only task flow, but also historicity.

Cons:

- there are no filters/cursor pagination or a separate log of status transitions yet;
- fallback mode is saved in dev/test, which should be disabled in the `prod` profile.
