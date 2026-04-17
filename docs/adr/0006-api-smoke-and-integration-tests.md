# ADR-0006: Smoke script и интеграционные тесты API endpoint-ов

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

После появления API boundary требуется быстрый и воспроизводимый способ проверки runtime-пути endpoint-ов в локальном окружении, а также регрессионное покрытие каждого endpoint-а на тестовом уровне.

## Решение

1. Добавить smoke script `backend/scripts/smoke_retrieval_api.ps1`.
2. В script запускать uvicorn, ждать `health`, затем прогонять путь:
   - start;
   - status;
   - evidence;
   - resume.
3. Добавить `backend/tests/integration/test_api_endpoints.py` с тестами на каждый endpoint (успешные и 404 ветки).

## Последствия

Плюсы:

- ускорена ручная проверка API без ручного копирования команд;
- каждый endpoint имеет интеграционное покрытие;
- легче контролировать регрессии task lifecycle.

Минусы:

- smoke script пока рассчитан на локальный single-process запуск;
- не покрывает распределенную конфигурацию и внешние сервисы production-контура.