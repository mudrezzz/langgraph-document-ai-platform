# Ручной Прогон: PostgreSQL + Миграции + Smoke

Краткий чеклист для самостоятельной проверки проекта на Linux-сервере.

## 1. Подготовка (один раз)

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi pydantic langgraph "psycopg[binary]" uvicorn pytest
chmod +x backend/scripts/*.sh
```

Ожидаемо: команды завершаются без ошибок.

## 2. Подготовить `backend/.env`

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

## 3. Поднять PostgreSQL в Docker

```bash
bash backend/scripts/postgres_up.sh
docker compose -f backend/docker-compose.postgres.yml --project-name langgraph ps
```

Ожидаемо: контейнер `langgraph-db` в статусе `Up ... (healthy)`.

## 4. Применить миграции

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/postgres_migrate.sh
```

Ожидаемо:

- `applied: 0001_baseline.sql`
- `applied: 0002_task_registry.sql`
- `applied: 0003_task_events.sql`

## 5. Прогнать smoke-сценарий

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

Ожидаемо в JSON-результате:

- `start_status = "completed"`
- `task_status = "completed"`
- `evidence_blocks >= 1`
- `history_contains_task = true`
- `events_returned >= 2`
- `events_has_running_to_completed = true`

Дополнительно полезно: в `top_sources` обычно есть `METH-001`, `OPS-002`, `INT-015`.

## 6. Проверить `task_id` вручную через API событий

Если нужно сразу после smoke вручную дергать API по `task_id`, оставьте сервер поднятым:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010 --keep-server
```

В stderr будет подсказка с PID-файлом, например:

- `backend/.smoke_uvicorn_8010.pid`

Проверка событий по задаче:

```bash
TASK_ID="<task_id_из_smoke_json>"
curl -sS --get "http://127.0.0.1:8010/api/v1/tasks/events" \
  --data-urlencode "limit=20" \
  --data-urlencode "task_id=$TASK_ID" \
  --data-urlencode "task_type=retrieval_pack"
```

## 7. Быстрая интерпретация результата

- `evidence_blocks = 0`: проблема в retrieval/dataset wiring.
- `history_contains_task = false`: проблема в persistence/task history.
- `events_has_running_to_completed = false`: проблема в lifecycle transitions или аудите task events.
- ошибка про `psycopg`: не активирован venv или не установлены зависимости.
- `API сервер завершился до /health`: смотреть лог smoke-скрипта и проверить env.

## 8. (Опционально) Проверить записи в БД

```bash
docker compose -f backend/docker-compose.postgres.yml --project-name langgraph exec -T postgres \
  psql -U app -d langgraph -c "SELECT task_id,status,updated_at FROM app.tasks ORDER BY updated_at DESC LIMIT 5;"

docker compose -f backend/docker-compose.postgres.yml --project-name langgraph exec -T postgres \
  psql -U app -d langgraph -c "SELECT task_id,from_status,to_status,created_at FROM app.task_events ORDER BY created_at DESC LIMIT 10;"

docker compose -f backend/docker-compose.postgres.yml --project-name langgraph exec -T postgres \
  psql -U app -d langgraph -c "SELECT run_id,updated_at FROM app.checkpoints WHERE run_id LIKE 'lg_thread:%' ORDER BY updated_at DESC LIMIT 5;"
```

Ожидаемо: свежая задача в `app.tasks`, события переходов статусов в `app.task_events` и как минимум одна запись `lg_thread:*` в `app.checkpoints` (это LangGraph runtime checkpoint namespace).

## 9. Завершение

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```

Ожидаемо: контейнер/сеть/volume удалены.

Если запускали smoke с `--keep-server`, сначала остановите API:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

Если PID-файл устарел, найдите процесс по порту и завершите его:

```bash
ss -ltnp '( sport = :8010 )'
# затем kill <pid>
```

## Примечания

- Для основной проверки использовать `smoke_retrieval_api.sh`.
- Demo-скрипт `demo_saa_release_readiness_case.sh` использует тот же smoke-контур и должен стабильно отрабатывать.
