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

## 3. Профиль A: local dev (быстрая локальная проверка)

Когда использовать: локальная разработка и быстрый feedback loop без async worker.

```bash
APP_RUNTIME_PROFILE=dev \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=inline \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

Ожидаемый результат: `task_status=completed`, `selected_blocks` не пустой, `events_summary_total > 0`.

## 4. Профиль B: stage-like (canonical + indexed retrieval)

Когда использовать: проверка canonical indexing/retrieval, близкая к acceptance пути.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=inline \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

Ожидаемый результат: `retrieval_backend=pgvector`, `stored_blocks_total > 0`, `embeddings_indexed > 0`.

## 5. Профиль C: prod-like (release gate baseline)

Когда использовать: pre-release проверка execution/observability/HITL matrix.

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=inline \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

Ожидаемый результат: `gate_status=pass` и пустой `failed_checks`.

Если нужен async/celery rehearsal и полный релизный цикл, используйте:

- `docs/developer_guide/operations_and_release.md`
- `docs/production_runbook.md`

## 6. Завершение

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
