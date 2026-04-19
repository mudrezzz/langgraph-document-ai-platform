# Handoff: Ubuntu 24 Server Migration

- Дата: 2026-04-19
- Последний commit: `d4e4613`
- Репозиторий: `https://github.com/mudrezzz/langgraph-document-ai-platform`
- Основная ветка: `main`

## 1. Текущее состояние проекта

Система уже поддерживает:

- typed FastAPI API для retrieval lifecycle:
  - `POST /api/v1/tasks/retrieval/start`
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/evidence`
  - `POST /api/v1/tasks/{task_id}/resume`
  - `GET /api/v1/tasks` (история задач)
- LangGraph execution внутри `BaseWorkflow` (`invoke/resume`);
- persistence baseline через PostgreSQL + pgvector;
- персистентный `TaskRegistry` (`app.tasks`, миграция `0002_task_registry.sql`);
- покрытие тестами:
  - unit / integration / e2e (включая postgres e2e);
- reference-case:
  - `saa_release_readiness_case`;
  - smoke/demo сценарии.

## 2. Что нужно сделать в новом чате (следующая итерация)

Цель серверной итерации:

1. Развернуть и проверить проект на Ubuntu 24 (не на Windows).
2. Ввести runtime профили (`dev/stage/prod`) и запретить fallback persistence в `prod`.
3. Расширить API истории задач:
   - фильтры (`status`, `task_type`, временной диапазон);
   - курсорная пагинация.
4. Добавить аудит переходов статусов задач (`task_events`).

## 3. Минимальное окружение Ubuntu 24

Установить пакеты:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl ca-certificates gnupg
```

Установить Docker + Compose plugin (официальный Docker repo) и добавить пользователя в группу `docker`.

Требования к Python-зависимостям проекта:

- `fastapi`
- `uvicorn`
- `pydantic`
- `psycopg[binary]`
- `pytest`
- остальные зависимости из `requirements`/poetry/uv-файла проекта (если будут добавлены в следующих итерациях)

## 4. Базовый запуск на сервере

```bash
git clone https://github.com/mudrezzz/langgraph-document-ai-platform.git
cd langgraph-document-ai-platform

cp backend/.env.example backend/.env
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh

APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010

python -m pytest backend/tests -q

bash backend/scripts/postgres_down.sh --remove-volumes
```

## 5. Стартовый текст для нового чата

```text
Работаем с репозиторием https://github.com/mudrezzz/langgraph-document-ai-platform, ветка main.
Контекст: реализованы retrieval API, LangGraph runtime, PostgreSQL+pgvector persistence, persistent task registry и endpoint истории задач.
Нужно продолжить серверную итерацию на Ubuntu 24:
1) ввести runtime profiles dev/stage/prod и отключить fallback в prod;
2) расширить GET /api/v1/tasks фильтрами и курсорной пагинацией;
3) добавить task_events для аудита переходов статусов;
4) обновить README, ADR и System Architecture Overview;
5) покрыть новые изменения unit/integration/e2e тестами и прогнать smoke.
Комментарии в коде — на русском.
```

## 6. Быстрый bootstrap checklist

См. отдельный документ:

- `docs/handoff/2026-04-19_ubuntu24_first_bootstrap_checklist.md`
