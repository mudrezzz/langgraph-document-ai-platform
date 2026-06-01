# Design Note: Increment 23 (HITL Actions Persistence + Read-Model API)

Date: 2026-04-22

## 1. Problem statement

Reviewer actions in the HITL circuit were stored inside the checkpoint/state payload.

This made it difficult:

- audit and filtering of reviewer actions;
- API access to reviewer actions history;
- building analytics on reviewer decisions/load.

## 2. Scope / Out of scope

Scope:

- separate table `hitl_actions`;
- adapter `PostgresHitlActionStore` (+ fallback mode);
- recording HITL action at key transitions;
- endpoint `GET /api/v1/hitl/actions` with filters and cursor pagination;
- unit/integration/e2e tests + manual smoke.

Out of scope:

- UI/dashboard reviewer;
- aggregated SLA/BI metrics based on reviewer actions;
- complex model of reviewer roles/accesses.

## 3. Which contracts are changing

API:

- new endpoint `GET /api/v1/hitl/actions`.

Persistence:

- new migration `0008_hitl_actions.sql`.

Backward compatibility:

- existing endpoints (`/tasks/{task_id}/hitl`, `/hitl/submit`) remain compatible.

## 4. Risks and compatibility

- the risk of state and read-model desynchronization: minimized by upsert logic at each action status transition;
- `prod` profile remains compatible, migration is additive.

## 5. Test plan

- Unit:
- `InMemoryHitlActionStore` (filters, cursors, cursor validation).
- Integration:
- `GET /api/v1/hitl/actions` in real authoring/HITL flow.
- E2E:
- Postgres e2e checks for entries in `app.hitl_actions`.
- Smoke:
- `smoke_authoring_async_api` checks `hitl_actions_total`.

## 6. Rollout plan

1. Apply migration `0008_hitl_actions.sql`.
2. Deploy the API/worker with the new `HitlActionStore`.
3. Check smoke async authoring + HITL sequence.
4. Confirm API endpoint `GET /api/v1/hitl/actions`.

## 7. Definition of Done

- reviewer actions persisted separately from checkpoint;
- history API is available and filtered by `task_id/decision/reviewer/time`;
- green tests (unit/integration/e2e/smoke);
- docs/ADR/architecture updated.
