# ADR-0009: Reference-case и обязательные e2e тесты FastAPI

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

По мере роста framework нужно иметь стабильный и понятный для бизнеса индикатор прогресса: не только unit/integration тесты, но и постоянный реалистичный сценарий, который усложняется от итерации к итерации.

## Решение

1. Ввести постоянный reference-case:
   - `saa_release_readiness_case` с тестовыми knowledge layers.
2. Привязать retrieval workflow к case dataset через `task_context` (`case_dataset_id` / `case_dataset_path`).
3. Добавить обязательные e2e FastAPI тесты на реальном `uvicorn`:
   - `backend/tests/e2e/test_fastapi_retrieval_e2e.py`.
4. Добавить demo-run script для наглядного прогона кейса:
   - `backend/scripts/demo_saa_release_readiness_case.ps1`.

## Последствия

Плюсы:

- появляется сквозной, приближенный к реальности индикатор развития платформы;
- прогресс виден через стабильный бизнес-сценарий;
- e2e слой ловит проблемы, которые не видны в TestClient-only тестах.

Минусы:

- тестовый контур становится тяжелее и требует поддержки fixture-данных;
- при изменениях контрактов нужно синхронно обновлять reference-case.