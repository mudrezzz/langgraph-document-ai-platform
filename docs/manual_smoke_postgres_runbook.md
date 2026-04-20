# Ручной Прогон: PostgreSQL + Smoke + Расширенный Demo

Краткая актуальная инструкция для Linux-сервера.

## 1. Подготовка окружения

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi pydantic langgraph "psycopg[binary]" uvicorn pytest
chmod +x backend/scripts/*.sh
```

Что увидеть:

- команды завершаются без ошибок;
- в проекте есть `./.venv` (smoke/demo теперь автоматически предпочитает этот python).

## 2. Создать `backend/.env`

```bash
cat > backend/.env <<'EOF'
APP_RUNTIME_PROFILE=prod
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
APP_DB_SCHEMA=app
APP_VECTOR_DIM=1536

POSTGRES_DB=langgraph
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_PORT=55432
EOF
```

Что это значит:

- `prod` профиль запрещает in-memory fallback persistence;
- проверяется именно реальный PostgreSQL-контур.

## 3. Поднять PostgreSQL и применить миграции

```bash
bash backend/scripts/postgres_up.sh
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/postgres_migrate.sh
```

Что увидеть:

- контейнер `langgraph-db` в состоянии `healthy`;
- применены миграции `0001`..`0005`.

## 4. Базовый smoke retrieval

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

Что увидеть в JSON:

- `start_status=completed`, `task_status=completed`;
- `evidence_blocks >= 1`;
- `history_contains_task=true`;
- `events_has_running_to_completed=true`;
- `events_summary_has_running_to_completed=true`.

Как интерпретировать:

- это минимальное подтверждение, что retrieval + task history + task events + events summary работают в PostgreSQL-контуре.

## 5. Ручной аудит событий по `task_id`

Если хотите вручную пройти API после smoke:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010 --keep-server
```

Дальше:

```bash
TASK_ID="<task_id_из_smoke_json>"
curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/events" \
  --data-urlencode "limit=20" \
  --data-urlencode "task_id=$TASK_ID" \
  --data-urlencode "task_type=retrieval_pack"

curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/events/summary" \
  --data-urlencode "task_id=$TASK_ID" \
  --data-urlencode "task_type=retrieval_pack"
```

Что увидеть:

- в `events` есть переходы `null -> running` и `running -> completed`;
- в `summary.transitions` есть `running -> completed`.

## 6. Расширенный demo (реалистичный file-based сценарий)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_case.sh --host 127.0.0.1 --port 8020
```

Что делает скрипт:

1. берёт `input/release_packet.md`;
2. строит dataset JSON;
3. запускает retrieval через `task_context.case_dataset_path`;
4. формирует отчет `output/release_readiness_report.md`.

Что увидеть:

- `evidence_blocks > 0`;
- в конце выведены пути к `dataset` и `report`;
- в отчете есть GO/NO-GO, blockers, pending approvals, evidence sources, task events summary.

## 7. Готово / Не реализовано в demo-контуре

Готово:

- file-based вход (`markdown -> dataset -> retrieval task`);
- аудит статусов и summary API в том же прогоне;
- осмысленный итоговый markdown-отчет для ручной проверки.

Еще не реализовано:

- универсальный ingestion произвольных форматов (пока фокус на структуре release packet);
- LLM-авторинг итогового решения (сейчас используются rule-based эвристики);
- отдельный production dashboard по агрегатам task events за периоды.

## 8. Завершение и остановка сервисов

Если запускали `--keep-server`, остановить API:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

Остановить PostgreSQL и удалить volume:

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
