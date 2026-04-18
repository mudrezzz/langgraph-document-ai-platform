# ADR-0011: Персистентный TaskRegistry и API истории задач

- Статус: Accepted
- Дата: 2026-04-18

## Контекст

После `Increment 6` lifecycle задач хранился только в `InMemoryTaskRegistry`. Это не переживало рестарт API процесса и не позволяло получить историю задач через публичный API.

Для наблюдаемости и диагностики нужен минимальный устойчивый контур:

- хранить lifecycle задач в PostgreSQL;
- иметь endpoint для чтения истории задач.

## Решение

1. Ввести `PostgresTaskRegistry` в infra persistence слое.
2. Добавить SQL миграцию `0002_task_registry.sql` с таблицей `app.tasks`.
3. Переключить DI-контейнер API с `InMemoryTaskRegistry` на `PostgresTaskRegistry`.
4. Расширить `TaskApplicationService` методом `list_tasks`.
5. Добавить endpoint `GET /api/v1/tasks` и typed response `TaskHistoryResponse`.
6. Добавить test coverage:
   - unit тесты registry;
   - integration тесты endpoint истории;
   - e2e тесты истории (включая PostgreSQL-контур).

## Последствия

Плюсы:

- lifecycle задач сохраняется в PostgreSQL и переживает рестарт API процесса;
- появился стандартный API-контракт для истории задач;
- smoke/e2e сценарии теперь проверяют не только task flow, но и историчность.

Минусы:

- пока нет фильтров/курсорной пагинации и отдельного журнала переходов статусов;
- в dev/test сохраняется fallback-режим, который должен быть отключен в `prod` профиле.
