# ADR-0028: HITL actions persistence and read-model API

- Status: Accepted
- Date: 2026-04-22

## Context

After `Increment 22` reviewer actions were saved only inside checkpoint/task details.

Limitations of this approach:

- there is no separate query API for reviewer actions;
- analytics on reviewer decisions (`approve/needs_changes/reject`) is difficult;
- reviewer actions data is strongly related to the internal state payload.

## Solution

1. Add a separate persistence layer HITL actions:
- table `app.hitl_actions` (`0008_hitl_actions.sql`);
- adapter `PostgresHitlActionStore` with fallback mode for dev/test.
2. Save reviewer actions at each key transition:
   - `queued -> processing -> completed|dispatch_failed`.
3. Add read-model endpoint:
   - `GET /api/v1/hitl/actions`;
- filters `task_id`, `decision`, `status`, `reviewer`, `from`, `to`;
- cursor pagination.
4. Leave checkpoint payload as a runtime-state layer, but make history/actions available through a separate read-model.

## Consequences

Pros:

- reviewer actions are available as a separate API/read-model;
- it’s easier to build audits and reports on reviewer decisions;
- less coupling between runtime-state and reporting reading.

Cons:

- additional table and support for consistency between state and read-model;
- complicating the write-path when updating the HITL action status.
