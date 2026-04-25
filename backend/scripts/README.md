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
- `async_up.sh` — поднять Redis + Celery worker через docker compose.
- `async_down.sh` — остановить Redis + Celery worker (опционально удалить volume).
- `apply_migrations.sh` — применить миграции при уже заданной `APP_DB_DSN`.
- `build_binary_demo_documents.sh` — сгенерировать `.docx/.pdf` входы для release go/no-go multifile demo.
- `smoke_retrieval_api.sh` — поднять `uvicorn`, дернуть API-цепочку `start -> status -> evidence -> resume -> history -> task_events`.
  - поддерживает `--keep-server` (не выключать API после smoke);
  - поддерживает `--server-pid-file <path>` (куда записать PID запущенного API).
- `demo_saa_release_readiness_case.sh` — человекочитаемый demo-ран reference-кейса.
- `demo_release_go_no_go_multifile_case.sh` — canonical release go/no-go demo.
  - запускает `knowledge-indexing/start`, затем canonical retrieval по `canonical_doc_ids`;
  - обновляет markdown report с quality summary и source mapping.
- `run_retrieval_mcp.sh` — запуск Retrieval MCP runtime (`build_evidence_pack/search_summaries/search_blocks/lookup_source`).
- `smoke_retrieval_mcp.sh` — ручной smoke Retrieval MCP indexed tools через `smoke_retrieval_mcp.py`.
- `run_repository_mcp.sh` — запуск Repository MCP runtime (`upsert_document/get_document/list_documents`).
- `smoke_repository_mcp.sh` — ручной smoke Repository MCP service через `smoke_repository_mcp.py`.
- `smoke_knowledge_indexing.sh` — ручной smoke canonical indexing для release go/no-go multifile input.
  - проверяет запись canonical documents и derived knowledge blocks в canonical store.
  - поддерживает `--build-binary-demo-docs` для генерации `.docx/.pdf` входов перед индексированием.
- `smoke_knowledge_indexing_api.sh` — smoke API flow `knowledge-indexing/start -> status -> events/summary`.
  - проверяет task registry/checkpoint/task events для canonical indexing.
  - поддерживает `--build-binary-demo-docs` для генерации `.docx/.pdf` входов перед индексированием.
- `smoke_canonical_retrieval.sh` — ручной smoke canonical indexing + retrieval поверх `knowledge_blocks`.
  - проверяет embedding indexing и vector-backed detail retrieval (`retrieval_backend=pgvector`).
  - поддерживает `--build-binary-demo-docs` для генерации `.docx/.pdf` входов перед индексированием.
- `run_artifact_writer_mcp.sh` — запуск Artifact Writer MCP runtime (`write_artifact/get_artifact/list_artifacts`).
- `smoke_artifact_writer_mcp.sh` — ручной smoke Artifact Writer MCP service через `smoke_artifact_writer_mcp.py`.
- `run_template_library_mcp.sh` — запуск Template Library MCP runtime (`upsert_template/publish_template/get_template/list_templates`).
- `smoke_template_library_mcp.sh` — ручной smoke Template Library MCP service через `smoke_template_library_mcp.py`.
- `smoke_authoring_api.sh` — smoke API flow `authoring/start -> status -> artifact -> events/summary`.
  - поддерживает `--draft-strategy auto|deterministic|llm`;
  - поддерживает `--workflow-mode single_pass|multi_step`;
  - поддерживает `--require-llm` для проверки, что ответ действительно сгенерирован LLM.
- `demo_release_authoring_traceability_case.sh` — demo authoring + traceability с сохранением результата в JSON.
- `smoke_authoring_async_api.sh` — smoke API flow `authoring/start_async -> waiting_human -> hitl/submit -> artifact`.
  - поддерживает `--hitl-decision-sequence` (например `needs_changes,approve`) для проверки итеративного HITL loop.
  - проверяет read-model endpoint `GET /api/v1/hitl/actions` для текущего task.
- `demo_release_authoring_async_hitl_case.sh` — demo async authoring + HITL с сохранением результата в JSON.

### Пример полного цикла

```bash
# Создайте backend/.env вручную (пример полей см. docs/manual_smoke_postgres_runbook.md)
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
APP_RUNTIME_PROFILE=stage APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010

# Для ручных curl-проверок после smoke:
APP_RUNTIME_PROFILE=stage APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010 --keep-server

# Остановка API после --keep-server:
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid

# Repository MCP smoke (работает в текущем runtime profile и DSN из окружения/.env):
bash backend/scripts/smoke_repository_mcp.sh

# Retrieval MCP indexed-tools smoke:
bash backend/scripts/smoke_retrieval_mcp.sh --build-binary-demo-docs

# Knowledge Factory canonical indexing smoke:
bash backend/scripts/smoke_knowledge_indexing.sh --build-binary-demo-docs

# Knowledge Factory API task lifecycle smoke:
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs

# Canonical retrieval smoke:
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs

# Запуск MCP runtime (до Ctrl+C), выполняйте по одному:
bash backend/scripts/run_repository_mcp.sh
# либо:
bash backend/scripts/run_artifact_writer_mcp.sh
# либо:
bash backend/scripts/run_template_library_mcp.sh

# Artifact Writer MCP smoke:
bash backend/scripts/smoke_artifact_writer_mcp.sh

# Template Library MCP smoke:
bash backend/scripts/smoke_template_library_mcp.sh

# Smoke проверяет draft -> publish -> list(status=published) path.

# Authoring API smoke:
bash backend/scripts/smoke_authoring_api.sh --port 8030 --workflow-mode multi_step

# Authoring API smoke c реальной LLM (при заданном OPENROUTER_API_KEY):
set -a && source backend/.env && set +a
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
  bash backend/scripts/smoke_authoring_api.sh --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm

# Authoring demo:
bash backend/scripts/demo_release_authoring_traceability_case.sh --port 8040

# Async authoring + HITL smoke:
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 APP_HITL_MAX_ITERATIONS=2 \
  bash backend/scripts/smoke_authoring_async_api.sh --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve

# Async authoring + HITL demo:
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 APP_HITL_MAX_ITERATIONS=2 \
  bash backend/scripts/demo_release_authoring_async_hitl_case.sh --port 8060 --hitl-decision-sequence needs_changes,approve
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```

Если PostgreSQL поднят на нестандартном host-порту, задайте `APP_WORKER_DB_DSN=postgresql://...@host.docker.internal:<port>/langgraph` перед `async_up.sh`.

## Windows (PowerShell)

- `postgres_up.ps1`
- `postgres_migrate.ps1`
- `postgres_down.ps1`
- `async_up.ps1`
- `async_down.ps1`
- `apply_migrations.ps1`
- `build_binary_demo_documents.ps1`
- `smoke_retrieval_api.ps1`
- `demo_saa_release_readiness_case.ps1`
- `run_retrieval_mcp.ps1`
- `smoke_retrieval_mcp.ps1`
- `run_repository_mcp.ps1`
- `smoke_repository_mcp.ps1`
- `smoke_knowledge_indexing.ps1`
- `smoke_knowledge_indexing_api.ps1`
- `smoke_canonical_retrieval.ps1`
- `run_artifact_writer_mcp.ps1`
- `smoke_artifact_writer_mcp.ps1`
- `run_template_library_mcp.ps1`
- `smoke_template_library_mcp.ps1`
- `smoke_authoring_api.ps1`
- `demo_release_authoring_traceability_case.ps1`
- `smoke_authoring_async_api.ps1`
- `demo_release_authoring_async_hitl_case.ps1`
