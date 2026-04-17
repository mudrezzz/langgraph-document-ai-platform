# ADR-0005: API boundary и task lifecycle через application services

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

После появления первого рабочего retrieval workflow требовалась сервисная граница, через которую UI и внешние клиенты смогут запускать задачи, получать статус, evidence и выполнять resume.

## Решение

1. Добавить `apps/api` на FastAPI как HTTP boundary.
2. Вынести orchestration-композицию в `application` слой:
   - `TaskApplicationService` для task registry/checkpoints;
   - `RetrievalApplicationService` для сценария retrieval.
3. Использовать typed контракты запросов/ответов (`schemas/api/contracts.py`).
4. На этапе Increment 3 использовать синхронную модель исполнения retrieval в одном процессе.

## Последствия

Плюсы:

- отделена API-граница от domain-логики;
- подтверждена работоспособность end-to-end пути `start -> status -> evidence -> resume`;
- зафиксирован шаблон для следующих application services.

Минусы:

- пока отсутствует асинхронный task runner;
- нет интеграции с реальным LangGraph runtime executor;
- persistence пока in-memory через adapter skeleton.