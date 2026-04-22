# Design Note: Increment 23 (HITL Actions Persistence + Read-Model API)

Дата: 2026-04-22

## 1. Problem statement

Reviewer actions в HITL контуре хранились внутри checkpoint/state payload.

Это усложняло:

- аудит и фильтрацию действий reviewer;
- API-доступ к истории reviewer actions;
- построение аналитики по решениям/нагрузке reviewer.

## 2. Scope / Out of scope

Scope:

- отдельная таблица `hitl_actions`;
- adapter `PostgresHitlActionStore` (+ fallback режим);
- запись HITL action на ключевых переходах;
- endpoint `GET /api/v1/hitl/actions` с фильтрами и курсорной пагинацией;
- тесты unit/integration/e2e + ручной smoke.

Out of scope:

- UI/dashboard reviewer;
- агрегированные SLA/BI-метрики по reviewer actions;
- сложная модель ролей/доступов reviewer.

## 3. Какие контракты меняются

API:

- новый endpoint `GET /api/v1/hitl/actions`.

Persistence:

- новая миграция `0008_hitl_actions.sql`.

Backward compatibility:

- существующие endpointы (`/tasks/{task_id}/hitl`, `/hitl/submit`) остаются совместимыми.

## 4. Риски и совместимость

- риск рассинхронизации state и read-model: минимизируется upsert-логикой на каждом переходе action status;
- `prod` профиль остается совместимым, миграция additive.

## 5. Test plan

- Unit:
  - `InMemoryHitlActionStore` (фильтры, курсоры, валидация cursor).
- Integration:
  - `GET /api/v1/hitl/actions` в real authoring/HITL flow.
- E2E:
  - Postgres e2e проверяет наличие записей в `app.hitl_actions`.
- Smoke:
  - `smoke_authoring_async_api` проверяет `hitl_actions_total`.

## 6. Rollout plan

1. Применить миграцию `0008_hitl_actions.sql`.
2. Развернуть API/worker с новым `HitlActionStore`.
3. Проверить smoke async authoring + HITL sequence.
4. Подтвердить API endpoint `GET /api/v1/hitl/actions`.

## 7. Definition of Done

- reviewer actions persisted отдельно от checkpoint;
- history API доступен и фильтруется по `task_id/decision/reviewer/time`;
- тесты зеленые (unit/integration/e2e/smoke);
- docs/ADR/architecture обновлены.
