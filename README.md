# LangGraph Document AI Platform

Этот репозиторий реализует внутренний framework-слой и прикладные сервисы системы документных AI-агентов на базе LangGraph.

## Источник требований

Базовые требования и целевая архитектура описаны в:

- `docs/тз_на_систему_документных_ai_агентов_на_lang_graph.md`
- `docs/blueprint_oop_слой_и_архитектура_системы_на_lang_graph.md`

## Статус

Текущий инкремент: `Increment 28`.

Сделано:

- создан и расширен каркас `backend`;
- реализованы framework contracts и базовые реализации;
- добавлены concrete adapter skeleton в `infra/*`;
- реализован `RetrievalPackWorkflow` как первый рабочий вертикальный срез;
- добавлен API boundary (`apps/api`) с typed retrieval endpoints;
- `BaseWorkflow` переведен на LangGraph runtime execution (`invoke/resume` через compiled graph);
- добавлены error/interrupt/resume ветки и интеграционные тесты API;
- добавлен baseline persistence слой на PostgreSQL + pgvector + baseline миграция;
- добавлен референсный реалистичный кейс `saa_release_readiness` с тестовыми knowledge layers;
- добавлены отдельные e2e тесты FastAPI на реальном `uvicorn`.
- добавлены скрипты bootstrap PostgreSQL профиля (`postgres_up.ps1`, `postgres_migrate.ps1`, `postgres_down.ps1`) и шаблон `backend/.env.example`;
- добавлен e2e тест с реальным PostgreSQL контейнером и улучшена диагностика старта `uvicorn` в e2e фикстурах.
- `TaskRegistry` вынесен в persistence слой: добавлен `PostgresTaskRegistry` + миграция `0002_task_registry.sql`;
- добавлен endpoint истории задач `GET /api/v1/tasks` и покрытие integration/e2e для него.
- добавлены Linux-скрипты (`.sh`) для Ubuntu 24: postgres up/migrate/down, migrations, smoke, demo;
- подготовлен handoff-документ для переноса разработки на Linux-сервер:
  - `docs/handoff/2026-04-19_ubuntu24_server_handoff.md`.
- добавлены runtime profiles (`APP_RUNTIME_PROFILE=dev|stage|prod`) с отключением fallback persistence в `prod`;
- расширен endpoint `GET /api/v1/tasks`:
  - фильтры `status`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`);
- добавлен аудит переходов статусов:
  - таблица `app.task_events` (`backend/migrations/0003_task_events.sql`);
  - запись событий при создании задачи и при смене статуса.
- добавлен endpoint аудита переходов статусов `GET /api/v1/tasks/events`:
  - фильтры `task_id`, `task_type`, `from`, `to`;
  - курсорная пагинация (`cursor`, `next_cursor`, `has_more`).
- расширен endpoint аудита `GET /api/v1/tasks/events`:
  - фильтры `from_status`, `to_status`.
- добавлен агрегированный endpoint аудита `GET /api/v1/tasks/events/summary`:
  - сводка `total_events`, `unique_tasks`;
  - группировка переходов `from_status -> to_status` с полем `total`.
- исправлен Linux demo-скрипт `backend/scripts/demo_saa_release_readiness_case.sh` (устранена ошибка парсинга JSON вывода smoke).
- в `smoke_retrieval_api.sh` добавлен режим `--keep-server` для ручной post-smoke проверки API по `task_id`.
- добавлен production checkpointer LangGraph поверх PostgreSQL (`PostgresLangGraphCheckpointer`) с подключением в runtime compile/invoke.
- в retrieval lifecycle гарантирован единый `thread_id` для LangGraph checkpointing через `task_context.task_id` (ветки `start` и `resume`).
- вынесен storage реального LangGraph checkpointer в выделенные таблицы:
  - `app.langgraph_checkpoints`;
  - `app.langgraph_checkpoint_blobs`;
  - `app.langgraph_checkpoint_writes`;
  - миграция `backend/migrations/0004_langgraph_checkpoint_storage.sql`.
- добавлена cleanup-политика `keep_latest/delete` в `PostgresLangGraphCheckpointer.prune(...)`.
- добавлена миграция индексов для аналитических фильтров task events:
  - `backend/migrations/0005_task_events_status_filter_indexes.sql`.
- добавлен file-based demo-кейс `release_go_no_go_case`:
  - входной markdown `release_packet.md`;
  - сборка retrieval dataset через `build_release_packet_dataset.py`;
  - осмысленный итоговый артефакт `release_readiness_report.md`.
- добавлен end-to-end demo pipeline:
  - Linux: `backend/scripts/demo_release_go_no_go_case.sh`;
  - Windows: `backend/scripts/demo_release_go_no_go_case.ps1`.
- добавлено e2e покрытие старта задачи с `task_context.case_dataset_path`.
- усилена надежность smoke/demo-скриптов:
  - приоритет python из `./.venv`;
  - ранняя проверка наличия модуля `uvicorn`.
- добавлен multi-file ingestion в retrieval start через `task_context.case_dataset_dir`:
  - поддержка входных файлов `.md`, `.txt`, `.json`;
  - сборка summary/detail блоков напрямую из директории без промежуточного JSON.
- добавлен новый multi-file demo-кейс `release_go_no_go_multifile_case`:
  - Linux: `backend/scripts/demo_release_go_no_go_multifile_case.sh`;
  - Windows: `backend/scripts/demo_release_go_no_go_multifile_case.ps1`.
  - текущий вариант demo запускает canonical indexing API, retrieval по `canonical_doc_ids` и пишет report с quality/source mapping.
- smoke-скрипты расширены параметром директории датасета:
  - `--case-dataset-dir` (Linux);
  - `-CaseDatasetDir` (Windows).
- добавлен Retrieval MCP MVP:
  - `apps/mcp_retrieval/main.py`;
  - `FastMcpRetrievalService` с tools `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source`;
  - скрипты `run_retrieval_mcp.sh/.ps1` и `smoke_retrieval_mcp.sh/.ps1`.
- добавлен Repository MCP MVP:
  - `apps/mcp_repository/main.py`;
  - `FastMcpRepositoryService` с tool-ами `upsert_document`, `get_document`, `list_documents`;
  - скрипты `run_repository_mcp.sh/.ps1` и `smoke_repository_mcp.sh/.ps1`.
- добавлен Artifact Writer MCP MVP:
  - `apps/mcp_artifact_writer/main.py`;
  - `FastMcpArtifactWriterService` с tool-ами `write_artifact`, `get_artifact`, `list_artifacts`;
  - `PostgresArtifactStore` + миграция `backend/migrations/0006_artifact_store.sql`;
  - скрипты `run_artifact_writer_mcp.sh/.ps1` и `smoke_artifact_writer_mcp.sh/.ps1`.
- добавлен Authoring API MVP:
  - `POST /api/v1/tasks/authoring/start`;
  - `GET /api/v1/tasks/{task_id}/artifact`;
  - orchestration `retrieval -> draft -> artifact` через `AuthoringApplicationService`.
- добавлена персистентная traceability-связь task -> artifact:
  - `PostgresTaskArtifactRegistry`;
  - таблица `app.task_artifacts` (`backend/migrations/0007_task_artifacts.sql`).
- reviewer actions вынесены в отдельный persistence/read-model слой:
  - `PostgresHitlActionStore`;
  - таблица `app.hitl_actions` (`backend/migrations/0008_hitl_actions.sql`);
  - endpoint истории `GET /api/v1/hitl/actions` с фильтрами и курсорами.
- добавлены authoring smoke/demo скрипты:
  - `smoke_authoring_api.sh/.ps1`;
  - `demo_release_authoring_traceability_case.sh/.ps1`.
- добавлена опциональная реальная LLM-интеграция authoring через OpenRouter:
  - env-конфиг `APP_LLM_*`, `OPENROUTER_*`;
  - режимы генерации draft: `auto`, `deterministic`, `llm`;
  - fallback на deterministic draft при недоступности LLM (когда `APP_LLM_STRICT=false`).
- добавлен внешний integration тест для real LLM:
  - `backend/tests/integration/test_authoring_openrouter_external.py` (активируется только с `RUN_EXTERNAL_LLM_TESTS=1`).
- authoring flow расширен до multi-step этапов:
  - `research -> writer -> reviewer -> assembly`;
  - `workflow_mode` в API (`single_pass|multi_step`);
  - в статусе задачи и metadata артефакта сохраняется `steps_summary`.
- traceability расширен до секций итогового артефакта:
  - `traceability.sections[]` с `section_id`, `title`, `review_status`, `source_refs`.
- добавлен async authoring запуск через Celery/Redis:
  - endpoint `POST /api/v1/tasks/authoring/start_async`;
  - worker app `apps/worker` + Celery task `run_authoring_task`;
  - docker-compose контур `backend/docker-compose.async.yml` (`redis` + `celery-worker`).
- добавлен базовый HITL API:
  - `GET /api/v1/tasks/{task_id}/hitl`;
  - `POST /api/v1/tasks/{task_id}/hitl/submit`;
  - статус задачи `waiting_human` и продолжение пайплайна после submit.
- HITL расширен до итеративного цикла:
  - policy `needs_changes -> rewrite -> reviewer_rerun -> waiting_human(iteration+1)`;
  - защита submit: `idempotency_key` + `expected_iteration`;
  - лимиты и SLA: `APP_HITL_MAX_ITERATIONS`, `APP_HITL_WAIT_TIMEOUT_SEC`;
  - async continuation после submit через dispatcher plane (`inline|celery`) и worker task `run_authoring_hitl_action`.
- добавлены async/HITL smoke и demo скрипты:
  - `smoke_authoring_async_api.sh/.ps1`;
  - `demo_release_authoring_async_hitl_case.sh/.ps1`;
  - `async_up/down.sh` и `async_up/down.ps1`.
- добавлен framework hardening слой:
  - root roadmap `BACKLOG.md`;
  - guide расширения framework `docs/framework_extension_guide.md`;
  - ADR `docs/adr/0029-framework-hardening-and-extension-guide.md`;
  - unit contract tests для agents/tools/mcp/db/stores.
- добавлен Knowledge Factory MVP:
  - типизированные canonical document contracts;
  - пакет `domain_docs`;
  - parser `.md/.txt/.json/.docx/.pdf` в `CanonicalDocumentParser`;
  - `KnowledgeIndexingWorkflow` поверх `BaseWorkflow`;
  - API endpoint `POST /api/v1/tasks/knowledge-indexing/start`;
  - smoke `smoke_knowledge_indexing.sh/.ps1` и `smoke_knowledge_indexing_api.sh/.ps1` для release go/no-go multifile input.
- добавлен отдельный canonical persistence/read-model слой:
  - `PostgresCanonicalDocumentStore`;
  - `CanonicalDocumentApplicationService`;
  - таблицы `app.canonical_documents` и `app.knowledge_blocks`;
  - миграция `backend/migrations/0009_canonical_knowledge_store.sql`.
- retrieval подключен к canonical Knowledge Factory output:
  - `task_context.knowledge_source=canonical`;
  - `task_context.canonical_doc_ids`;
  - smoke `smoke_canonical_retrieval.sh/.ps1`.
- canonical detail retrieval подключен к embedding/pgvector path:
  - `KnowledgeIndexingApplicationService` индексирует embeddings для `knowledge_blocks`;
  - `PgVectorStoreAdapter.query_similar(...)`;
  - `CanonicalVectorRetriever`;
  - smoke показывает `retrieval_backend=pgvector`.
- начат `Increment 26: Framework Runtime Closure`:
  - `ToolExecutor` расширен runtime policy (`ToolExecutionPolicy`);
  - добавлены retry, idempotency key handling и audit records для framework tools;
  - `ToolContext` поддерживает `node_name`, `correlation_id`, `idempotency_key`;
  - добавлены contract tests для retry/idempotency/audit behavior.
  - `BaseWorkflow` поддерживает multi-node `WorkflowNodeSpec` hooks для invoke/resume graph;
  - добавлен `WorkflowExecutionContext` с `task_id`, `correlation_id`, `node_name`;
  - `SubgraphWorkflow` поддерживает `invoke_as_subgraph(...)` и parent context propagation.
  - `BaseWorkflow` эмитит node-level events (`started/completed/failed`);
  - retrieval и knowledge-indexing workflows пишут node events в существующий `task_events` audit через `event_payload.event_kind=workflow_node`.
  - `WorkflowFactory` поддерживает DI-friendly builders, capability metadata и явные ошибки duplicate/missing registration.
- начат `Increment 27: Production Retrieval Fabric`:
  - Knowledge Indexing индексирует embeddings для canonical `section_summaries`;
  - добавлен pgvector-backed `CanonicalSummaryVectorRetriever`;
  - canonical retrieval использует pgvector summary/detail layers при наличии embedding gateway и vector store.
  - `TeiEmbeddingGateway` и `TeiRerankGateway` поддерживают real TEI HTTP endpoints с env-конфигом и deterministic fallback.
  - `EvidenceBuilder` применяет retrieval quality gates и заполняет `unresolved_gaps`/`confidence_notes`.
  - Retrieval MCP расширен indexed canonical tools `search_summaries`, `search_blocks`, `lookup_source` поверх existing canonical/vector adapters.

## Структура

```text
backend/
  apps/
    api/
    mcp_artifact_writer/
    mcp_repository/
    mcp_retrieval/
    worker/
  examples/
    cases/
  migrations/
  packages/
    framework/
    schemas/
    infra/
    domain_docs/
    domain_rag/
    application/
  scripts/
  tests/
docs/
  adr/
  architecture/
  handoff/
```

## Reference Case: SAA Release Readiness

### Что это за кейс

Это постоянный демонстрационный сценарий, приближенный к реальной задаче аналитика: собрать `evidence pack` для раздела ТЗ по readiness к релизу SAA-платформы.

Данные кейса лежат в:

- `backend/examples/cases/saa_release_readiness_case/input/knowledge_layers.json`

В датасете уже есть:

- `summary` слой (методология и operations);
- `detail` слой (требования, безопасность, governance);
- source metadata (`doc_id`, `version`, `section`, `tags`, `document_type`).

### Как запускать кейс

1. Быстрый демонстрационный запуск (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_saa_release_readiness_case.ps1
```

2. Быстрый демонстрационный запуск (Linux):

```bash
bash ./backend/scripts/demo_saa_release_readiness_case.sh --host 127.0.0.1 --port 8010
```

3. Гибкий smoke запуск с параметрами (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_retrieval_api.ps1 `
  -HostName 127.0.0.1 `
  -Port 8000 `
  -CaseDatasetId saa_release_readiness `
  -Query "Какие ограничения и approval точки важны перед релизом?"
```

4. Гибкий smoke запуск с параметрами (Linux):

```bash
bash ./backend/scripts/smoke_retrieval_api.sh \
  --host 127.0.0.1 \
  --port 8000 \
  --case-dataset-id saa_release_readiness \
  --query "Какие ограничения и approval точки важны перед релизом?"
```

5. Smoke c оставлением API поднятым для ручного `curl` (Linux):

```bash
bash ./backend/scripts/smoke_retrieval_api.sh \
  --host 127.0.0.1 \
  --port 8010 \
  --keep-server

# после проверки:
kill "$(cat ./backend/.smoke_uvicorn_8010.pid)" && rm -f ./backend/.smoke_uvicorn_8010.pid
```

6. Расширенный file-based demo (Linux):

```bash
bash ./backend/scripts/demo_release_go_no_go_case.sh --host 127.0.0.1 --port 8020
```

7. Расширенный file-based demo (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_release_go_no_go_case.ps1
```

8. Расширенный multi-file demo (Linux):

```bash
bash ./backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

9. Расширенный multi-file demo (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_release_go_no_go_multifile_case.ps1
```

10. Запуск Retrieval MCP (Linux):

```bash
pip install fastmcp
bash ./backend/scripts/run_retrieval_mcp.sh
```

11. Запуск Retrieval MCP (Windows):

```powershell
pip install fastmcp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_retrieval_mcp.ps1
```

12. Smoke Retrieval MCP indexed tools (Linux):

```bash
bash ./backend/scripts/smoke_retrieval_mcp.sh --build-binary-demo-docs
```

13. Smoke Retrieval MCP indexed tools (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_retrieval_mcp.ps1 -BuildBinaryDemoDocs
```

14. Запуск Repository MCP (Linux):

```bash
pip install fastmcp
bash ./backend/scripts/run_repository_mcp.sh
```

15. Запуск Repository MCP (Windows):

```powershell
pip install fastmcp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_repository_mcp.ps1
```

16. Smoke Repository MCP (Linux):

```bash
bash ./backend/scripts/smoke_repository_mcp.sh
```

17. Smoke Repository MCP (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_repository_mcp.ps1
```

18. Запуск Artifact Writer MCP (Linux):

```bash
pip install fastmcp
bash ./backend/scripts/run_artifact_writer_mcp.sh
```

17. Запуск Artifact Writer MCP (Windows):

```powershell
pip install fastmcp
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_artifact_writer_mcp.ps1
```

18. Smoke Artifact Writer MCP (Linux):

```bash
bash ./backend/scripts/smoke_artifact_writer_mcp.sh
```

19. Smoke Artifact Writer MCP (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_artifact_writer_mcp.ps1
```

20. Smoke Authoring API (Linux):

```bash
bash ./backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step
```

21. Smoke Authoring API (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_authoring_api.ps1 -HostName 127.0.0.1 -Port 8030 -WorkflowMode multi_step
```

22. Smoke Authoring API c обязательной LLM-генерацией (Linux):

```bash
set -a && source backend/.env && set +a
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
bash ./backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm
```

23. Demo Authoring + Traceability (Linux):

```bash
bash ./backend/scripts/demo_release_authoring_traceability_case.sh --host 127.0.0.1 --port 8040
```

24. Demo Authoring + Traceability (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_release_authoring_traceability_case.ps1 -HostName 127.0.0.1 -Port 8040
```

25. Поднять Redis + Celery worker (Linux):

```bash
bash ./backend/scripts/async_up.sh
```

26. Smoke Async Authoring API + HITL (Linux):

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
bash ./backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

27. Demo Async Authoring + HITL (Linux):

```bash
set -a && source backend/.env && set +a
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
bash ./backend/scripts/demo_release_authoring_async_hitl_case.sh --host 127.0.0.1 --port 8060 --hitl-decision-sequence needs_changes,approve
```

28. Остановить Redis + Celery worker (Linux):

```bash
bash ./backend/scripts/async_down.sh
```

29. Smoke Knowledge Indexing (Linux):

```bash
bash ./backend/scripts/smoke_knowledge_indexing.sh --build-binary-demo-docs
```

30. Smoke Knowledge Indexing (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_knowledge_indexing.ps1 -BuildBinaryDemoDocs
```

31. Smoke Canonical Retrieval (Linux):

```bash
bash ./backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

32. Smoke Canonical Retrieval (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_canonical_retrieval.ps1 -BuildBinaryDemoDocs
```

33. Smoke Knowledge Indexing API task lifecycle (Linux):

```bash
bash ./backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
```

34. Smoke Knowledge Indexing API task lifecycle (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_knowledge_indexing_api.ps1 -BuildBinaryDemoDocs
```

Примечание: если PostgreSQL на нестандартном порту, задайте `APP_WORKER_DB_DSN=postgresql://...@host.docker.internal:<port>/langgraph` перед `async_up.sh`.

## Reference Case: Release Go/No-Go (File-Based)

Новый сценарий показывает реалистичный поток "документ -> retrieval -> отчет":

1. Входной файл:
   - `backend/examples/cases/release_go_no_go_case/input/release_packet.md`
2. Автогенерация dataset:
   - `backend/examples/cases/release_go_no_go_case/output/release_packet_dataset.generated.json`
3. Запуск retrieval с `task_context.case_dataset_path`.
4. Итоговый отчет:
   - `backend/examples/cases/release_go_no_go_case/output/release_readiness_report.md`

Что проверяем в этом demo:

- корректность file-based ingest в retrieval pipeline;
- сохранение task lifecycle и audit events в том же контуре API;
- интерпретируемый результат для релизного решения (GO/NO-GO, blockers, approvals).

## Reference Case: Release Go/No-Go (Multi-File Canonical)

Сценарий показывает canonical ingestion директории с несколькими документами:

1. Входная папка:
   - `backend/examples/cases/release_go_no_go_multifile_case/input`
2. Запуск Knowledge Indexing API с `.md/.txt/.json/.docx/.pdf`.
3. Запуск retrieval с `task_context.knowledge_source=canonical` и `canonical_doc_ids`.
4. Итоговый отчет:
   - `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`

Этот кейс удобен для демонстрации реального потока, где данные приходят не из одного файла, а из набора артефактов релизного пакета, проходят canonical parsing/indexing и затем попадают в retrieval evidence pack через pgvector-backed canonical retrieval.

### Как интерпретировать результат demo/smoke

Скрипт возвращает JSON со следующими полями:

- `indexing_status`: финальный статус Knowledge Indexing task;
- `quality_gate_status`: `passed|warning|failed` по canonical quality summary;
- `retrieval_status`: финальный статус retrieval task;
- `knowledge_source`: ожидаемо `canonical`;
- `retrieval_backend`: ожидаемо `pgvector`;
- `evidence_blocks`: сколько блоков попало в evidence pack;
- `top_sources`: первые источники из evidence pack (быстрая sanity-проверка релевантности);
- `resume_status`: статус после `resume`;
- `resume_decision`: решение, переданное в `resume` (`rerun`, `continue`, ...);
- `history_returned`: сколько задач вернул endpoint истории `GET /api/v1/tasks`;
- `history_contains_task`: попала ли только что запущенная задача в историю.
- `events_returned`: сколько событий вернул endpoint аудита `GET /api/v1/tasks/events` для текущей задачи;
- `events_has_running_to_completed`: найден ли переход `running -> completed`.
- `events_summary_total`: сколько событий попало в агрегированную сводку `GET /api/v1/tasks/events/summary`;
- `events_summary_unique_tasks`: по скольким задачам построена сводка;
- `events_summary_has_running_to_completed`: есть ли в сводке переход `running -> completed`.

Нормальный для текущей версии результат:

- `start_status=completed`;
- `task_status=completed`;
- `evidence_blocks >= 1`;
- в `top_sources` присутствуют документы из кейса, например `METH-001`, `GOV-021`, `OPS-002`;
- `resume_status=completed`;
- `history_returned >= 1`;
- `history_contains_task=true`;
- `events_returned >= 2`;
- `events_has_running_to_completed=true`.
- `events_summary_total >= 2`;
- `events_summary_unique_tasks = 1` для smoke по одному `task_id`;
- `events_summary_has_running_to_completed=true`.

Если `evidence_blocks=0` или в `top_sources` нет ожидаемых документов кейса, это сигнал, что сломалась маршрутизация retrieval или dataset wiring.

## Что уже работает

- end-to-end путь `start -> status -> evidence -> resume` через FastAPI;
- execution workflow через LangGraph runtime в `BaseWorkflow`;
- unit/integration/e2e тесты (`TestClient` и реальный `uvicorn`);
- baseline persistence adapters и SQL migration scaffold;
- демонстрационный сценарий с реальными тестовыми данными;
- локальный PostgreSQL профиль поднимается/мигрируется через PowerShell и Bash scripts;
- e2e сценарий проверяется и в in-memory режиме, и с реальным PostgreSQL;
- lifecycle задач хранится в персистентном реестре (`PostgresTaskRegistry`);
- API отдает историю задач через `GET /api/v1/tasks` с фильтрами и курсорной пагинацией;
- API отдает аудит событий через `GET /api/v1/tasks/events` с фильтрами и курсорной пагинацией;
- API отдает агрегированную сводку аудита через `GET /api/v1/tasks/events/summary`;
- переходы статусов фиксируются в аудит-таблице `app.task_events`;
- `prod` профиль запрещает in-memory fallback persistence.
- LangGraph runtime использует PostgreSQL checkpointer в БД-контуре и `InMemorySaver` в fallback-контуре.
- task payload продолжает храниться в `app.checkpoints`, а runtime checkpointing вынесен в отдельный storage-контур `app.langgraph_*`.
- retrieval start поддерживает file-based датасет через `task_context.case_dataset_path`;
- retrieval start поддерживает загрузку из директории через `task_context.case_dataset_dir`;
- добавлен новый реалистичный demo-кейс release go/no-go с генерацией итогового markdown-отчета.
- добавлен Retrieval MCP MVP (`build_evidence_pack`) как первый FastMCP runtime сервис.
- добавлен Repository MCP MVP (`upsert_document/get_document/list_documents`) как второй FastMCP runtime сервис.
- document repository поддерживает list-операцию для MCP read-model (`limit/offset`).
- добавлен Artifact Writer MCP MVP (`write_artifact/get_artifact/list_artifacts`) как третий FastMCP runtime сервис.
- artifact store поддерживает list-операцию для MCP read-model (`limit/offset`, `artifact_type`).
- добавлен authoring API flow (`authoring/start`, `tasks/{task_id}/artifact`) с итоговым draft-артефактом.
- сохраняется traceability link `task -> artifact -> retrieval sources` в `app.task_artifacts`.
- authoring draft поддерживает реальную LLM (OpenRouter) с режимами `auto|deterministic|llm`.
- embeddings/rerank поддерживают TEI HTTP endpoints:
  - `TEI_BASE_URL` задает общий endpoint, из которого строятся `/embed` и `/rerank`;
  - `TEI_EMBEDDING_URL` и `TEI_RERANK_URL` могут задать endpoints явно;
  - `TEI_API_KEY` добавляется как Bearer token, если требуется;
  - `TEI_TIMEOUT_SEC` задает timeout;
  - `TEI_FALLBACK_ENABLED=true` разрешает deterministic fallback при transport/API ошибке.
- multi-step authoring поддерживает шаги `research -> writer -> reviewer -> assembly` и сохраняет их в `steps_summary`.
- traceability возвращает секции итогового артефакта (`traceability.sections`) с привязкой к источникам.
- async запуск authoring поддерживается через Celery/Redis очередь (`start_async`).
- HITL контур поддерживает итеративные ревизии с паузой `waiting_human`, idempotency submit и async continuation через worker.
- Docker/Celery e2e покрывает как базовый approve-flow, так и iterative path `needs_changes -> approve`.
- начат `Increment 28: Domain Authoring Extraction`:
  - добавлен пакет `backend/packages/domain_authoring`;
  - выделены `OutlinePlanner`, `SectionReviewService`, `DocumentAssembler`, `ResearchSummaryBuilder`, `WriterDraftService`;
  - `AuthoringApplicationService` интегрирует domain services через DI без изменения внешних API;
  - выбор LLM strategy/fallback остается в application layer, а research/writer composition вынесены в domain layer;
  - traceability/source-ref mapping и HITL human feedback formatting тоже перенесены в `domain_authoring`.
  - введены typed `SectionContract` и `SectionPacket`, а section contracts сохраняются в authoring state и artifact metadata.
  - добавлен `SectionAuthoringService`, который строит deterministic `section_artifacts` и `SectionDigest` из section packets.
  - добавлен `TemplateCompiler`, а authoring поддерживает template-aware section contracts через `task_context.template_id/template_payload`.
  - deterministic assembly теперь template-aware и может собирать итоговый документ из `TemplateSpec` + `section_artifacts`.
- framework extension path зафиксирован в `docs/framework_extension_guide.md`.
- `BACKLOG.md` фиксирует roadmap завершения backend/framework части и обязательный demo acceptance harness.
- `domain_docs` умеет строить canonical document payload для `.md/.txt/.json/.docx/.pdf`.
- `KnowledgeIndexingWorkflow` сохраняет canonical documents и derived knowledge blocks через отдельный canonical store boundary.
- retrieval start поддерживает canonical knowledge source через `task_context.knowledge_source=canonical`.
- canonical detail retrieval использует vector index для `knowledge_blocks`, если доступен embedding gateway + vector store.
- retrieval quality gates доступны в task details и evidence pack:
  - `quality_gate_status`;
  - `unresolved_gaps`;
  - `confidence_notes`.
- Retrieval MCP поддерживает отдельный indexed smoke path через `smoke_retrieval_mcp.sh/.ps1`.

## Контракт POST /api/v1/tasks/retrieval/start (task_context)

Поддерживаемые поля в `task_context`:

- `case_dataset_id` — загрузка встроенного demo-датасета по id;
- `case_dataset_path` — загрузка датасета из JSON-файла на диске (file-based режим).
- `case_dataset_dir` — загрузка датасета из директории файлов (`.md/.txt/.json`).
- `knowledge_source=canonical` — загрузка retrieval blocks из canonical store (`app.canonical_documents` + `app.knowledge_blocks`).
- `canonical_doc_ids` — опциональное ограничение canonical retrieval конкретными `doc_id`.

Приоритет источников: `knowledge_source=canonical` -> `case_dataset_path` -> `case_dataset_dir` -> `case_dataset_id`.

## Контракт POST /api/v1/tasks/authoring/start

Поля запроса:

- `query`
- `filters`
- `task_context`
  - поддерживает `template_id` и `template_payload` для template-aware authoring section contracts.
- `artifact_type` (по умолчанию `release_report`)
- `artifact_title` (опционально)
- `artifact_format` (по умолчанию `markdown`)
- `draft_strategy` (`auto|deterministic|llm`, по умолчанию `auto`)
- `workflow_mode` (`single_pass|multi_step`, по умолчанию `multi_step`)
- `hitl_required` (`true|false`, по умолчанию `false`)

Ответ:

- `task_id`
- `status`

## Контракт POST /api/v1/tasks/authoring/start_async

Поля запроса совпадают с `authoring/start`.

Ответ:

- `task_id`
- `status` (`queued`)

## Контракт GET /api/v1/tasks/{task_id}/artifact

Ответ:

- `task_id`
- `artifact_id`
- `artifact_type`
- `title`
- `content`
- `format`
- `metadata`
- `traceability`:
  - `retrieval_task_id`
  - `source_refs` (`doc_id`, `version`, `block_id`)
  - `sections[]`:
    - `section_id`
    - `title`
    - `review_status`
    - `source_refs` (`doc_id`, `version`, `block_id`)

## Контракт GET /api/v1/tasks/{task_id}/hitl

Ответ:

- `task_id`
- `status`
- `required`
- `current_iteration`
- `max_iterations`
- `deadline_at`
- `can_submit`
- `pending_action_id`
- `pending_reason`
- `reviewer_notes`
- `actions[]` (`action_id`, `iteration`, `decision`, `status`, `idempotency_key`, `comment`, `metadata`, `created_at`)

## Контракт POST /api/v1/tasks/{task_id}/hitl/submit

Поля запроса:

- `decision` (`approve|needs_changes|reject`)
- `comment`
- `metadata`
- `idempotency_key` (опционально, для dedup повторных submit)
- `expected_iteration` (опционально, optimistic guard)

Ответ:

- `task_id`
- `status`
- `current_node`
- `details`

## Контракт GET /api/v1/hitl/actions

Параметры:

- `limit` (1..200)
- `cursor` (opaque cursor следующей страницы)
- `task_id`
- `decision`
- `status`
- `reviewer`
- `from` / `to` (ISO datetime, фильтрация по `created_at`)

Ответ:

- `items[]` (`action_id`, `task_id`, `iteration`, `decision`, `status`, `comment`, `idempotency_key`, `metadata`, `created_at`)
- `limit`
- `total_returned`
- `next_cursor`
- `has_more`

## MCP Контракты (MVP)

- Retrieval MCP:
  - tools `build_evidence_pack`, `search_summaries`, `search_blocks`, `lookup_source`;
  - smoke scripts `backend/scripts/smoke_retrieval_mcp.sh/.ps1`;
  - схемы `backend/packages/schemas/mcp/retrieval.py`.
- Repository MCP:
  - tools `upsert_document`, `get_document`, `list_documents`;
  - схемы `backend/packages/schemas/mcp/repository.py`.
- Artifact Writer MCP:
  - tools `write_artifact`, `get_artifact`, `list_artifacts`;
  - схемы `backend/packages/schemas/mcp/artifact_writer.py`.

## Knowledge Factory MVP

Canonical ingestion работает через отдельный persistence/read-model слой:

- parser: `domain_docs.parsing.CanonicalDocumentParser`;
- workflow: `domain_docs.indexing.KnowledgeIndexingWorkflow`;
- application boundary: `KnowledgeIndexingApplicationService`;
- API endpoint: `POST /api/v1/tasks/knowledge-indexing/start`;
- canonical boundary: `CanonicalDocumentApplicationService`;
- storage: `PostgresCanonicalDocumentStore`;
- SQL tables: `app.canonical_documents`, `app.knowledge_blocks`.

Поддерживаемые форматы текущего среза:

- `.md`;
- `.txt`;
- `.json`;
- `.docx` через `python-docx`;
- `.pdf` через `PyMuPDF`.

Smoke текущего demo input:

```bash
bash ./backend/scripts/smoke_knowledge_indexing.sh --build-binary-demo-docs
bash ./backend/scripts/smoke_knowledge_indexing_api.sh --build-binary-demo-docs
bash ./backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

Ожидаемый результат:

- `documents_total=6`;
- `content_blocks_total > 0`;
- `stored_blocks_for_indexed_docs_total > 0` в direct/canonical retrieval smoke;
- `stored_blocks_total > 0` в API smoke details;
- `embeddings_indexed > 0`;
- `quality_gate_status=passed|warning`;
- `events_summary_has_running_to_completed=true` в Knowledge Indexing API smoke;
- `knowledge_source=canonical` в canonical retrieval smoke;
- `retrieval_backend=pgvector` в canonical retrieval smoke;
- `evidence_blocks > 0`;
- `file_types` содержит `md`, `txt`, `json`, `docx`, `pdf`.

## Контракт GET /api/v1/tasks

Параметры:

- `limit` (1..200)
- `cursor` (opaque cursor следующей страницы)
- `status` (например `running`, `completed`, `failed`, `interrupted`)
- `task_type` (например `retrieval_pack`)
- `from` / `to` (ISO datetime, фильтрация по `updated_at`)

Ответ:

- `items`: список задач;
- `limit`: размер страницы;
- `total_returned`: сколько элементов вернулось в текущем ответе;
- `next_cursor`: курсор следующей страницы или `null`;
- `has_more`: есть ли следующая страница.

## Контракт GET /api/v1/tasks/events

Параметры:

- `limit` (1..200)
- `cursor` (opaque cursor следующей страницы)
- `task_id`
- `task_type`
- `from_status`
- `to_status`
- `from` / `to` (ISO datetime, фильтрация по `created_at`)

Ответ:

- `items`: список событий переходов;
- `limit`: размер страницы;
- `total_returned`: сколько событий вернулось в текущем ответе;
- `next_cursor`: курсор следующей страницы или `null`;
- `has_more`: есть ли следующая страница.

## Контракт GET /api/v1/tasks/events/summary

Параметры:

- `task_id`
- `task_type`
- `from_status`
- `to_status`
- `from` / `to` (ISO datetime, фильтрация по `created_at`)

Ответ:

- `total_events`: общее число событий по фильтру;
- `unique_tasks`: число уникальных `task_id` по фильтру;
- `transitions`: агрегированные переходы со структурой `from_status`, `to_status`, `total`.

## Что будет в следующих итерациях

- унификация контрактов и операционных политик для Retrieval/Repository/Artifact Writer MCP;
- ingestion расширение на PDF/DOCX/OCR с quality gates;
- агрегированные read-model/дашборды поверх `task_events` и `task_artifacts` (по периодам, task_type, SLA).

## Тестовая стратегия

1. Unit: `backend/tests/unit/*`
2. Integration (FastAPI TestClient): `backend/tests/integration/*`
3. E2E (реальный `uvicorn`): `backend/tests/e2e/*`

## Запуск тестов

```bash
python3 -m pytest backend/tests -q
```

Внешний integration тест с реальной LLM:

```bash
set -a && source backend/.env && set +a
RUN_EXTERNAL_LLM_TESTS=1 python3 -m pytest -q backend/tests/integration/test_authoring_openrouter_external.py
```

## Локальный запуск PostgreSQL профиля

### Windows (PowerShell)

1. Подготовить `backend/.env` (см. `docs/manual_smoke_postgres_runbook.md`):

```powershell
# Создайте backend/.env вручную с APP_DB_DSN/APP_DB_SCHEMA/APP_RUNTIME_PROFILE
```

2. Поднять контейнер PostgreSQL + pgvector:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\postgres_up.ps1
```

3. Применить миграции:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\postgres_migrate.ps1
```

4. Запустить smoke в PostgreSQL-режиме:

```powershell
$env:APP_DB_DSN = "postgresql://app:app@localhost:55432/langgraph"
$env:APP_DB_SCHEMA = "app"
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_retrieval_api.ps1 -Port 8010
```

5. Остановить PostgreSQL и удалить volume:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\postgres_down.ps1 -RemoveVolumes
```

### Linux (Ubuntu 24, Bash)

1. Подготовить `backend/.env` (см. `docs/manual_smoke_postgres_runbook.md`):

```bash
# Создайте backend/.env вручную с APP_DB_DSN/APP_DB_SCHEMA/APP_RUNTIME_PROFILE
```

2. Поднять контейнер PostgreSQL + pgvector:

```bash
bash ./backend/scripts/postgres_up.sh
```

3. Применить миграции:

```bash
bash ./backend/scripts/postgres_migrate.sh
```

4. Запустить smoke в PostgreSQL-режиме:

```bash
APP_RUNTIME_PROFILE=stage APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash ./backend/scripts/smoke_retrieval_api.sh --port 8010
```

5. Остановить PostgreSQL и удалить volume:

```bash
bash ./backend/scripts/postgres_down.sh --remove-volumes
```

Отдельный e2e прогон PostgreSQL контура (Windows/Linux):

```bash
python3 -m pytest backend/tests/e2e/test_fastapi_retrieval_e2e_postgres.py -q
```

## Применение миграций

Windows:

```powershell
$env:APP_DB_DSN = "postgresql://user:password@localhost:5432/langgraph"
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\apply_migrations.ps1
```

Linux:

```bash
APP_DB_DSN=postgresql://user:password@localhost:5432/langgraph \
  bash ./backend/scripts/apply_migrations.sh
```

## Обязательные документы сопровождения

После каждого инкремента обновляются документы сопровождения:

1. `README.md` — текущее состояние, структура, правила работы.
2. `docs/adr/*.md` — принятые архитектурные решения.
3. `docs/architecture/System_Architecture_Overview.md` — актуальный снимок архитектуры и GAP к целевой модели.
4. `BACKLOG.md` — roadmap и статус следующих инкрементов, если меняется план.
5. `docs/framework_extension_guide.md` — правила расширения framework, если меняются extension patterns.
