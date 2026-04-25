# Ручной Прогон: PostgreSQL + Smoke + Расширенный Demo

Краткая актуальная инструкция для Linux-сервера.

## 1. Подготовка окружения

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./backend
pip install uvicorn pytest
chmod +x backend/scripts/*.sh
```

Что увидеть:

- команды завершаются без ошибок;
- в проекте есть `./.venv` (smoke/demo теперь автоматически предпочитает этот python).
- backend editable install подтягивает зависимости parser boundary, включая `python-docx` и `PyMuPDF`.

Если editable install все же падает на package discovery, используйте fallback без editable mode:

```bash
pip install -r <(python - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path('backend/pyproject.toml').read_text())
for item in data['project']['dependencies']:
    print(item)
PY
)
pip install uvicorn pytest
export PYTHONPATH="$(pwd)/backend:$(pwd)/backend/packages"
```

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
TEI_BASE_URL=
TEI_EMBEDDING_URL=
TEI_RERANK_URL=
TEI_API_KEY=
TEI_TIMEOUT_SEC=30
TEI_FALLBACK_ENABLED=false
APP_ASYNC_PROVIDER=inline
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0
APP_CELERY_QUEUE=authoring
APP_HITL_MAX_ITERATIONS=2
APP_HITL_WAIT_TIMEOUT_SEC=1800
REDIS_PORT=56379

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
- применены миграции `0001`..`0009`.

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

1. гарантирует наличие `.docx/.pdf` demo input files;
2. запускает Knowledge Indexing API для директории `input/` (`.md`, `.txt`, `.json`, `.docx`, `.pdf`);
3. берет `indexed_doc_ids` из indexing task details;
4. запускает retrieval через `task_context.knowledge_source=canonical` и `canonical_doc_ids`;
5. формирует отчет `output/release_readiness_report.md`.

Что увидеть:

- `indexing_status=completed`;
- `quality_gate_status=warning` для текущего PDF fixture;
- `knowledge_source=canonical`;
- `retrieval_backend=pgvector`;
- `quality_gate_status=passed|warning`;
- `evidence_blocks > 0`;
- `top_sources` содержит документы из нескольких файлов, включая `.docx`/`.pdf` при релевантном запросе;
- отчет содержит `Canonical Quality Summary`, `Retrieval Quality` и `Canonical Source Mapping`.

## 8. Готово / Не реализовано в demo-контуре

Готово:

- file-based вход (`markdown -> dataset -> retrieval task`);
- multi-file canonical вход (`directory -> canonical indexing -> retrieval task`) через `canonical_doc_ids`;
- аудит статусов и summary API в том же прогоне;
- multi-step authoring цикл (`research -> writer -> reviewer -> assembly`);
- HITL-петля с итерациями (`needs_changes -> rewrite -> re-review -> waiting_human(iteration+1)`);
- осмысленный итоговый markdown-отчет для ручной проверки.

Еще не реализовано:

- OCR/rich layout extraction для scanned PDF;
- отдельный reviewer UI/dashboard для мониторинга очереди HITL решений;
- отдельный production dashboard по агрегатам task events за периоды.

## 9. (Опционально) Проверка Retrieval MCP

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_retrieval_mcp.sh
```

Что увидеть:

- MCP-сервис стартует без ошибки импорта;
- доступны tools `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source`;
- процесс остается запущенным и слушает MCP runtime до `Ctrl+C`.

Как интерпретировать:

- `build_evidence_pack` сохраняет прежний end-to-end retrieval task contract;
- `search_summaries` ищет indexed canonical section summaries через pgvector;
- `search_blocks` ищет indexed canonical content blocks через pgvector;
- `lookup_source` возвращает source/canonical mapping по `doc_id`/`block_id` или `block_ref`;
- для indexed tools нужен PostgreSQL/pgvector контур с ранее выполненным Knowledge Indexing.

## 9.1. Smoke Retrieval MCP indexed tools

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_mcp.sh --build-binary-demo-docs
```

Что увидеть в JSON:

- `tool_names` содержит `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source`;
- `summary_candidates >= 1`;
- `block_candidates >= 1`;
- `lookup_found=true`;
- `summary_backend=pgvector` и `block_backend=pgvector`;
- `build_status=completed`;
- `evidence_blocks >= 1`.

Как интерпретировать:

- это подтверждает прямой MCP path поверх indexed canonical corpus без ручного запуска retrieval API;
- smoke использует тот же production-compatible assembly: canonical indexing, vector store, retrieval service и source lookup.

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

## 13.1. Smoke Template Library MCP (reusable templates)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_template_library_mcp.sh
```

Что увидеть в JSON:

- `upserted_template_id` и `loaded_template_id` заполнены;
- `published_status=published` и `loaded_status=published`;
- `loaded_section_id=overview`;
- `list_total_returned >= 1`;
- `list_contains_template=true`.

Как интерпретировать:

- это подтверждает, что persisted template library доступна через MCP service boundary, а не только через HTTP API или внутренний authoring wiring;
- `upsert_template` прогоняет payload через existing `TemplateCompiler`, затем сохраняет compiled `TemplateSpec` как `draft`;
- `publish_template` переводит нужную version в `published`;
- `get_template` и `list_templates(status=published)` читают те же persisted template records, что использует authoring path.

## 13.2. (Опционально) Проверка Template Library MCP runtime

```bash
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/run_template_library_mcp.sh
```

Что увидеть:

- MCP-сервис `template-library-mcp` стартует без ошибки импорта;
- доступны tools `upsert_template`, `publish_template`, `get_template`, `list_templates`;
- процесс остается запущенным и слушает MCP runtime до `Ctrl+C`.

## 13.3. Smoke Knowledge Indexing

Этот smoke проверяет реальный вход demo-кейса:

- `backend/examples/cases/release_go_no_go_multifile_case/input/01_scope_and_decision.md`
- `backend/examples/cases/release_go_no_go_multifile_case/input/02_security_findings.md`
- `backend/examples/cases/release_go_no_go_multifile_case/input/03_ops_readiness.txt`
- `backend/examples/cases/release_go_no_go_multifile_case/input/04_approvals.json`
- `backend/examples/cases/release_go_no_go_multifile_case/input/05_release_notes.docx`
- `backend/examples/cases/release_go_no_go_multifile_case/input/06_audit_summary.pdf`

Если нужно явно пересобрать `.docx/.pdf` входы:

```bash
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/build_binary_demo_documents.sh --overwrite
```

Обычный smoke можно запускать с флагом `--build-binary-demo-docs`: тогда `.docx/.pdf` будут созданы перед индексированием, если их нет.

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing.sh --build-binary-demo-docs
```

Что увидеть в JSON:

- `documents_total=6`;
- `indexed_doc_ids` содержит `01SCOPEA-*`, `02SECURI-*`, `03OPSREA-*`, `04APPROV-*`, `05RELEAS-*`, `06AUDITS-*`;
- `content_blocks_total` около `37` или больше при изменении fixture;
- `stored_blocks_for_indexed_docs_total` около `37` или больше;
- `stored_blocks_total` может быть больше, если в той же БД уже были прошлые indexing smoke;
- `embeddings_indexed` около `37` или больше;
- `file_types` содержит `docx`, `json`, `md`, `pdf`, `txt`;
- `quality_flags` может содержать `06AUDITS-*:low_text_density` для текущего PDF fixture.

Как интерпретировать:

- это подтверждает, что Knowledge Factory строит canonical documents из text, markdown, JSON, DOCX и PDF;
- canonical documents сохраняются в `app.canonical_documents`;
- derived content blocks сохраняются в `app.knowledge_blocks`;
- embedding vectors для content blocks пишутся в `app.embeddings`.

## 13.4. Smoke Knowledge Indexing API Task Lifecycle

Этот smoke проверяет тот же indexing путь через FastAPI task endpoint:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```

Что увидеть в JSON:

- `start_status=completed`;
- `task_status=completed`;
- `documents_total=6`;
- `file_types` содержит `docx`, `json`, `md`, `pdf`, `txt`;
- `stored_blocks_total` около `37` или больше;
- `embeddings_indexed` около `37` или больше;
- `quality_gate_status=passed|warning`;
- `events_summary_has_running_to_completed=true`.

Как интерпретировать:

- это подтверждает, что Knowledge Indexing работает как полноценная task lifecycle операция;
- `app.tasks` содержит задачу `task_type=knowledge_indexing`;
- `app.task_events` содержит переход `running -> completed`;
- checkpoint payload содержит canonical documents, indexed ids и quality summary.

## 13.3. Smoke Canonical Retrieval

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh \
  --build-binary-demo-docs \
  --query "release notes audit summary security sign-off customer notification"
```

Что увидеть в JSON:

- `indexed_doc_ids` содержит те же 6 canonical documents;
- `stored_blocks_for_indexed_docs_total` около `37` или больше;
- `stored_blocks_total` может быть больше из-за прошлых indexing-прогонов в той же БД;
- `embeddings_indexed` около `37` или больше;
- `knowledge_source=canonical`;
- `retrieval_backend=pgvector`;
- `quality_gate_status=passed|warning`;
- `evidence_blocks > 0` (на текущем fixture обычно десятки blocks);
- `top_sources` содержит `05RELEAS-*` и `06AUDITS-*` для этого binary-focused запроса;
- `task_status=completed`.

Как интерпретировать:

- это подтверждает путь `canonical documents -> knowledge_blocks -> retrieval evidence pack`.
- summary/detail retrieval идет через pgvector-backed canonical retrievers, а не через старый demo dataset loader;
- retrieval quality gates видны в task details и `EvidencePack.unresolved_gaps`.

## 13.4. Ручной API-прогон canonical retrieval после indexing

Если хочется проверить не только smoke script, а руками дернуть API, сначала выполните indexing smoke из раздела 13.1 и возьмите из его JSON массив `indexed_doc_ids`. Затем поднимите API:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
uvicorn apps.api.main:app --app-dir backend --host 127.0.0.1 --port 8070
```

В другом терминале отправьте retrieval task поверх canonical source:

```bash
curl -sS -X POST "http://127.0.0.1:8070/api/v1/tasks/retrieval/start" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "что блокирует релиз payments v2 и какие approvals pending",
    "filters": {
      "project_id": "p1",
      "document_types": ["requirements", "methodology", "security", "operations", "governance"]
    },
    "task_context": {
      "requester": "manual-canonical-demo",
      "knowledge_source": "canonical",
      "canonical_doc_ids": [
        "01SCOPEA-9912",
        "02SECURI-8031",
        "03OPSREA-1824",
        "04APPROV-5796",
        "05RELEAS-3554",
        "06AUDITS-1436"
      ]
    }
  }'
```

Замените значения `canonical_doc_ids` на актуальные IDs из вашего indexing smoke, если они отличаются. Из ответа возьмите `task_id`, затем:

```bash
TASK_ID="<task_id_из_start_json>"
curl -sS "http://127.0.0.1:8070/api/v1/tasks/$TASK_ID"
curl -sS "http://127.0.0.1:8070/api/v1/tasks/$TASK_ID/evidence"
```

Что увидеть:

- status содержит `knowledge_source=canonical`, `retrieval_backend=pgvector`, `status=completed`;
- evidence pack содержит источники из разных файлов demo input, включая `05_release_notes.docx` и/или `06_audit_summary.pdf`, если они попали в top evidence для запроса.

## 14. Smoke Authoring API (retrieval -> artifact + traceability)

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step
```

Что увидеть в JSON:

- `start_status=completed` и `task_status=completed`;
- `artifact_id` и `artifact_title` заполнены;
- при `--artifact-format json` поле `format` возвращается как `json`, а `content` содержит structured JSON artifact;
- `draft_generation_mode` обычно `deterministic` (если LLM не включена);
- `workflow_mode=multi_step`;
- `steps_total=4` (research/writer/reviewer/assembly);
- `traceability_sections >= 3`;
- `review_status` заполнен (`completed|needs_revision|skipped`);
- `traceability_sources >= 1`;
- `events_summary_has_running_to_completed=true`.

Как интерпретировать:

- это подтверждает, что authoring API flow формирует итоговый артефакт и сохраняет traceability link к retrieval источникам.

Проверка с реальной LLM через OpenRouter:

```bash
set -a && source backend/.env && set +a
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm
```

Что увидеть в JSON для LLM-режима:

- `draft_generation_mode=llm`;
- заполнены `draft_model_provider=openrouter` и `draft_model_name`.
- `steps_total=4` и `traceability_sections >= 3`.

## 15. Поднять Redis + Celery worker (async контур)

```bash
bash backend/scripts/async_up.sh
```

Что увидеть:

- сервисы `redis` и `celery-worker` в состоянии `running`/`healthy` (`docker compose ... ps`).

## 16. Smoke Async Authoring API + HITL

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

Примечание:

- если PostgreSQL опубликован не на `55432`, добавьте `APP_WORKER_DB_DSN=postgresql://...@host.docker.internal:<port>/langgraph` перед запуском `async_up.sh`.

Что увидеть в JSON:

- `start_status=queued`;
- первая пауза приходит как `waiting_human`, а `GET /api/v1/tasks/{task_id}/hitl` возвращает `phase=outline_review`;
- в `outline.sections[]` видны planned sections и их `source_refs`;
- после первого submit (`needs_changes`) задача снова становится `waiting_human` с `hitl_iteration=2`;
- после второго submit (`approve`) задача доходит до `task_status=completed`;
- `steps_total >= 4`;
- `traceability_sections >= 3`;
- `hitl_submit_count=2`;
- `hitl_actions_total=2` (проверка нового read-model endpoint `/api/v1/hitl/actions`).

Как интерпретировать:

- это подтверждает, что async запуск через Celery/Redis работает, а reviewer сначала видит outline approval point до section authoring;
- тот же iterative path дополнительно закреплен в реальном Docker/Celery e2e тесте `backend/tests/e2e/test_fastapi_authoring_async_celery_e2e.py`.

## 17. Расширенный demo: authoring async + HITL

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_authoring_async_hitl_case.sh --host 127.0.0.1 --port 8060 --hitl-decision-sequence needs_changes,approve
```

Что делает скрипт:

1. запускает async authoring через `authoring/start_async`;
2. дожидается `waiting_human`;
3. выполняет последовательность reviewer-решений (`needs_changes -> approve`);
4. сохраняет результат в `output/authoring_async_hitl_result.json`.

## 18. Расширенный demo: authoring + traceability

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

## 19. Завершение и остановка сервисов

Если запускали `--keep-server`, остановить API:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

Остановить PostgreSQL и удалить volume:

```bash
bash backend/scripts/async_down.sh --remove-volumes
bash backend/scripts/postgres_down.sh --remove-volumes
```
