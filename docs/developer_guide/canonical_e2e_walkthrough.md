# Canonical E2E Walkthrough

Дата обновления: 2026-04-30  
Статус: Active (P0 practical guide)

Цель walkthrough: пройти полный путь `documents -> indexing -> retrieval -> authoring -> HITL -> artifact` через реальные API/scripts.

## 1. Подготовка окружения

```bash
cd /root/langgraph-document-ai-platform
PATH="$(pwd)/.venv/bin:$PATH"
python3 -m venv .venv
pip install -e ./backend

bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

Базовый runtime для walkthrough:

```bash
export APP_RUNTIME_PROFILE=stage
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
export APP_ASYNC_PROVIDER=inline
```

## 2. Documents -> canonical indexing

Задача: разобрать demo corpus, применить quality policy, сохранить canonical documents + knowledge blocks.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8075 --build-binary-demo-docs
```

Проверяем в JSON-выводе:

- `status=completed`
- `file_types` содержит binary форматы (`pdf`, `docx`, `xlsx`, `pptx`)
- `quality_gate_status` присутствует

## 3. Indexing -> retrieval (canonical source)

Задача: выполнить retrieval поверх canonical corpus и pgvector индекса.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

Проверяем:

- `retrieval_backend=pgvector`
- `embeddings_indexed > 0`
- `selected_blocks` не пустой
- в details есть `quality_gate_status` и `unresolved_gaps`

## 4. Retrieval -> authoring artifact

Задача: получить итоговый authoring артефакт с traceability.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step
```

Проверяем:

- `task_status=completed`
- endpoint `GET /api/v1/tasks/{task_id}/artifact` возвращает `artifact_id`, `content`, `traceability`
- в `traceability` есть `retrieval_task_id` и `source_refs`

## 5. Authoring -> HITL loop -> final artifact

Задача: пройти review/approve контур с итерацией `needs_changes -> approve`.

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

Проверяем:

- задача проходит через `waiting_human`
- в `GET /api/v1/hitl/actions` фиксируются reviewer actions
- финальный `artifact` доступен после approve

## 6. End-to-end report proof

Для человекочитаемого сквозного артефакта:

```bash
APP_RUNTIME_PROFILE=stage \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/demo_release_go_no_go_multifile_case.sh --host 127.0.0.1 --port 8022
```

Результат:

- `backend/examples/cases/release_go_no_go_multifile_case/output/release_readiness_report.md`
- разделы `Canonical Quality Summary` и `Canonical Source Mapping`

## 7. Завершение

```bash
bash backend/scripts/postgres_down.sh --remove-volumes
```
