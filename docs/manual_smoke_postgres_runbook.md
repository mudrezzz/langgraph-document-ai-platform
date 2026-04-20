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

Опционально для MCP:

```bash
pip install fastmcp
```

## 2. Создать `backend/.env`

```bash
cat > backend/.env <<'EOF'
APP_RUNTIME_PROFILE=prod
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
APP_DB_SCHEMA=app
APP_VECTOR_DIM=1536
APP_LLM_ENABLED=false
APP_LLM_PROVIDER=openrouter
APP_LLM_STRICT=false
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT_SEC=60

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
- применены миграции `0001`..`0007`.

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

## 6. Расширенный demo: single-file сценарий

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

## 7. Расширенный demo: multi-file сценарий

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

Что делает скрипт:

1. берет директорию `input/` с несколькими файлами (`.md`, `.txt`, `.json`);
2. запускает retrieval через `task_context.case_dataset_dir`;
3. формирует отчет `output/release_readiness_report.md`.

Что увидеть:

- `evidence_blocks > 0`;
- `top_sources` содержит документы из нескольких файлов;
- отчет формируется без промежуточной ручной сборки dataset JSON.

## 8. Готово / Не реализовано в demo-контуре

Готово:

- file-based вход (`markdown -> dataset -> retrieval task`);
- multi-file вход (`directory -> retrieval task`) через `case_dataset_dir`;
- аудит статусов и summary API в том же прогоне;
- осмысленный итоговый markdown-отчет для ручной проверки.

Еще не реализовано:

- универсальный ingestion для бинарных форматов (`.pdf/.docx`) и OCR;
- multi-step authoring цикл (`research -> writer -> reviewer -> assembly`) и HITL-петля;
- отдельный production dashboard по агрегатам task events за периоды.

## 9. (Опционально) Проверка Retrieval MCP

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_retrieval_mcp.sh
```

Что увидеть:

- MCP-сервис стартует без ошибки импорта;
- процесс остается запущенным и слушает MCP runtime до `Ctrl+C`.

## 10. Smoke Repository MCP (document tools)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_repository_mcp.sh
```

Что увидеть в JSON:

- `upserted_doc_ids` содержит 2 значения;
- `loaded_doc_id` и `loaded_title` заполнены;
- `list_total_returned >= 1`;
- `list_contains_doc_1=true` и `list_contains_doc_2=true`.

Как интерпретировать:

- это подтверждает, что repository-контур в PostgreSQL профиле поддерживает `upsert/get/list` через MCP service слой.

## 11. (Опционально) Проверка Repository MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_repository_mcp.sh
```

Что увидеть:

- MCP-сервис `repository-mcp` стартует без ошибки импорта;
- процесс остается запущенным и слушает MCP runtime до `Ctrl+C`.

## 12. Smoke Artifact Writer MCP (generated artifacts)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_artifact_writer_mcp.sh
```

Что увидеть в JSON:

- `written_artifact_ids` содержит 2 значения;
- `loaded_artifact_id` и `loaded_title` заполнены;
- `list_total_returned >= 1`;
- `list_contains_artifact_1=true` и `list_contains_artifact_2=true`.

Как интерпретировать:

- это подтверждает, что artifact writer-контур в PostgreSQL профиле поддерживает `write/get/list` через MCP service слой.

## 13. (Опционально) Проверка Artifact Writer MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_artifact_writer_mcp.sh
```

Что увидеть:

- MCP-сервис `artifact-writer-mcp` стартует без ошибки импорта;
- процесс остается запущенным и слушает MCP runtime до `Ctrl+C`.

## 14. Smoke Authoring API (retrieval -> artifact + traceability)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030
```

Что увидеть в JSON:

- `start_status=completed` и `task_status=completed`;
- `artifact_id` и `artifact_title` заполнены;
- `draft_generation_mode` обычно `deterministic` (если LLM не включена);
- `traceability_sources >= 1`;
- `events_summary_has_running_to_completed=true`.

Как интерпретировать:

- это подтверждает, что authoring API flow формирует итоговый артефакт и сохраняет traceability link к retrieval источникам.

Проверка с реальной LLM через OpenRouter:

```bash
set -a && source backend/.env && set +a
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --draft-strategy llm --require-llm
```

Что увидеть в JSON для LLM-режима:

- `draft_generation_mode=llm`;
- заполнены `draft_model_provider=openrouter` и `draft_model_name`.

## 15. Расширенный demo: authoring + traceability

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_authoring_traceability_case.sh --host 127.0.0.1 --port 8040
```

Что делает скрипт:

1. запускает authoring smoke flow через новый endpoint `authoring/start`;
2. получает итоговый task artifact и summary событий;
3. сохраняет итог в `output/authoring_traceability_result.json`.

## 16. Завершение и остановка сервисов

Если запускали `--keep-server`, остановить API:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

Остановить PostgreSQL и удалить volume:

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
