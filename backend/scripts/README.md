# Scripts Guide

Документ описывает скрипты запуска и проверки проекта.

## Linux (Ubuntu 24.04)

### Требования

- `python` 3.12+
- установленный пакет `psycopg[binary]` в Python окружении проекта
- `docker` + `docker compose` plugin
- `curl`

### Скрипты

- `postgres_up.sh` — поднять PostgreSQL + pgvector через docker compose.
- `postgres_migrate.sh` — загрузить `.env` и применить SQL-миграции.
- `postgres_down.sh` — остановить PostgreSQL контейнер (опционально удалить volume).
- `apply_migrations.sh` — применить миграции при уже заданной `APP_DB_DSN`.
- `smoke_retrieval_api.sh` — поднять `uvicorn`, дернуть API-цепочку `start -> status -> evidence -> resume -> history`.
- `demo_saa_release_readiness_case.sh` — человекочитаемый demo-ран reference-кейса.

### Пример полного цикла

```bash
cp backend/.env.example backend/.env
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010
bash backend/scripts/postgres_down.sh --remove-volumes
```

## Windows (PowerShell)

- `postgres_up.ps1`
- `postgres_migrate.ps1`
- `postgres_down.ps1`
- `apply_migrations.ps1`
- `smoke_retrieval_api.ps1`
- `demo_saa_release_readiness_case.ps1`
