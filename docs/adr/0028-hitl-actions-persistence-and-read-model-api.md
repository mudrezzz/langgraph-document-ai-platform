# ADR-0028: HITL actions persistence и read-model API

- Статус: Accepted
- Дата: 2026-04-22

## Контекст

После `Increment 22` reviewer actions сохранялись только внутри checkpoint/task details.

Ограничения такого подхода:

- нет отдельного query API по reviewer actions;
- аналитика по решениям reviewer (`approve/needs_changes/reject`) затруднена;
- данные reviewer actions сильно связаны с внутренним state payload.

## Решение

1. Добавить отдельный persistence слой HITL actions:
   - таблица `app.hitl_actions` (`0008_hitl_actions.sql`);
   - adapter `PostgresHitlActionStore` с fallback режимом для dev/test.
2. Сохранять действия reviewer при каждом ключевом переходе:
   - `queued -> processing -> completed|dispatch_failed`.
3. Добавить read-model endpoint:
   - `GET /api/v1/hitl/actions`;
   - фильтры `task_id`, `decision`, `status`, `reviewer`, `from`, `to`;
   - курсорная пагинация.
4. Оставить checkpoint payload как runtime-state слой, но сделать history/actions доступными через отдельный read-model.

## Последствия

Плюсы:

- reviewer actions доступны как отдельный API/read-model;
- проще строить аудит и отчеты по reviewer decisions;
- меньше связности между runtime-state и отчетным чтением.

Минусы:

- дополнительная таблица и поддержка согласованности между state и read-model;
- усложнение write-path при обновлении статуса HITL action.
