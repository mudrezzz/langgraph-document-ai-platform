# LangGraph Document AI Platform

Этот репозиторий реализует внутренний framework-слой и прикладные сервисы системы документных AI-агентов на базе LangGraph.

## Источник требований

Базовые требования и целевая архитектура описаны в:

- `docs/тз_на_систему_документных_ai_агентов_на_lang_graph.md`
- `docs/blueprint_oop_слой_и_архитектура_системы_на_lang_graph.md`

## Статус

Текущий инкремент: `Increment 8`.

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

## Структура

```text
backend/
  apps/
    api/
  examples/
    cases/
  migrations/
  packages/
    framework/
    schemas/
    infra/
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

### Как интерпретировать результат demo/smoke

Скрипт возвращает JSON со следующими полями:

- `start_status`: результат старта задачи (`completed` или `interrupted`);
- `task_status`: финальный статус после вызовов `start/status`;
- `evidence_blocks`: сколько блоков попало в evidence pack;
- `top_sources`: первые источники из evidence pack (быстрая sanity-проверка релевантности);
- `resume_status`: статус после `resume`;
- `resume_decision`: решение, переданное в `resume` (`rerun`, `continue`, ...);
- `history_returned`: сколько задач вернул endpoint истории `GET /api/v1/tasks`;
- `history_contains_task`: попала ли только что запущенная задача в историю.

Нормальный для текущей версии результат:

- `start_status=completed`;
- `task_status=completed`;
- `evidence_blocks >= 1`;
- в `top_sources` присутствуют документы из кейса, например `METH-001`, `GOV-021`, `OPS-002`;
- `resume_status=completed`;
- `history_returned >= 1`;
- `history_contains_task=true`.

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
- API отдает историю задач через `GET /api/v1/tasks`.

## Что будет в следующих итерациях

- runtime profiles (`dev/stage/prod`) и отключение fallback в `prod`;
- реальный LangGraph checkpointer поверх PostgreSQL;
- FastMCP runtime-сервисы (`Retrieval MCP`, `Repository MCP`, далее `Artifact Writer MCP`);
- расширение reference-case: переход от retrieval-only к связке retrieval + authoring + traceability;
- расширение API-истории задач (фильтры, курсоры, аудит изменений статусов).

## Тестовая стратегия

1. Unit: `backend/tests/unit/*`
2. Integration (FastAPI TestClient): `backend/tests/integration/*`
3. E2E (реальный `uvicorn`): `backend/tests/e2e/*`

## Запуск тестов

```bash
python -m pytest backend/tests -q
```

## Локальный запуск PostgreSQL профиля

### Windows (PowerShell)

1. Подготовить env-файл:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
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

1. Подготовить env-файл:

```bash
cp ./backend/.env.example ./backend/.env
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
APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash ./backend/scripts/smoke_retrieval_api.sh --port 8010
```

5. Остановить PostgreSQL и удалить volume:

```bash
bash ./backend/scripts/postgres_down.sh --remove-volumes
```

Отдельный e2e прогон PostgreSQL контура (Windows/Linux):

```bash
python -m pytest backend/tests/e2e/test_fastapi_retrieval_e2e_postgres.py -q
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

После каждого инкремента обновляются три документа:

1. `README.md` — текущее состояние, структура, правила работы.
2. `docs/adr/*.md` — принятые архитектурные решения.
3. `docs/architecture/System_Architecture_Overview.md` — актуальный снимок архитектуры и GAP к целевой модели.
