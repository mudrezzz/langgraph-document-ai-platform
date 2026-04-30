# Quickstart

## 1. Bootstrap окружение

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
PATH="$(pwd)/.venv/bin:$PATH"
pip install -e ./backend
```

## 2. Поднять PostgreSQL + pgvector и применить миграции

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

## 3. Проверить базовый retrieval API smoke

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

Ожидаемый результат: JSON с `task_status=completed`, `events_summary_total > 0` и непустым `selected_blocks`.

## 4. Проверить canonical indexing + retrieval слой

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

Ожидаемый результат: в JSON присутствуют `retrieval_backend=pgvector`, `stored_blocks_total > 0`, `embeddings_indexed > 0`.

## 5. Завершение

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```

Если нужен полный manual flow с async/MCP/HITL и release gate, используйте `docs/developer_guide/operations_and_release.md`.
