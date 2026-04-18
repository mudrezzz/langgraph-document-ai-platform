# ADR-0010: Локальный PostgreSQL профиль и устойчивость e2e старта API

- Статус: Accepted
- Дата: 2026-04-18

## Контекст

После `Increment 5` persistence-адаптеры и миграции уже были добавлены, но не было стандартизованного способа быстро поднять PostgreSQL локально и прогнать smoke/e2e сценарии в одном и том же профиле.

Дополнительно выяснилось, что e2e-фикстуры на реальном `uvicorn` падали слишком рано при `connection refused` во время старта сервера, без информативной диагностики.

## Решение

1. Зафиксировать стандартный локальный профиль PostgreSQL:
   - `backend/docker-compose.postgres.yml`;
   - `backend/.env.example`;
   - `backend/scripts/postgres_up.ps1`;
   - `backend/scripts/postgres_migrate.ps1`;
   - `backend/scripts/postgres_down.ps1`.
2. Добавить отдельный e2e-контур с реальным PostgreSQL:
   - `backend/tests/e2e/test_fastapi_retrieval_e2e_postgres.py`.
3. Усилить надежность e2e-старта API:
   - в ожидании `/health` обрабатывать `URLError` как временное состояние;
   - при раннем завершении `uvicorn` выбрасывать ошибку с `stdout/stderr` процесса.

## Последствия

Плюсы:

- локальный bootstrap PostgreSQL стал воспроизводимым и документированным;
- e2e покрытие проверяет не только in-memory режим, но и реальный DB runtime;
- сбои старта API теперь быстрее диагностируются по stderr, без "немых" таймаутов.

Минусы:

- e2e PostgreSQL требуют Docker и работают дольше, чем in-memory e2e;
- тестовый контур сложнее в сопровождении из-за зависимости от внешнего контейнера.
