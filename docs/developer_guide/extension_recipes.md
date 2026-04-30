# Extension Recipes

Документ показывает практический шаблон расширения библиотеки без нарушения существующих public contracts.

## 1. Добавление нового workflow

1. Добавьте state schema в `backend/packages/schemas/workflow` или доменный `schemas` модуль.
2. Реализуйте workflow на `framework.workflows.BaseWorkflow`.
3. Для multi-node сценария используйте `workflow_nodes(is_resume=...)` и `WorkflowNodeSpec`.
4. Прокиньте `task_context.task_id` и `task_context.correlation_id` для audit/checkpoint consistency.
5. Зарегистрируйте workflow через application service или `WorkflowFactory.register_builder(...)`.
6. Добавьте тесты invoke/resume/error + node events.

См. базовые правила: `docs/framework_extension_guide.md`.

## 2. Добавление нового tool

1. Описать typed input/output contracts.
2. Реализовать `framework.tools.BaseTool`.
3. Зарегистрировать в `ToolRegistry`.
4. Вызывать через `ToolExecutor` c `ToolExecutionPolicy`.
5. Добавить audit sink, если нужен task-level trace.
6. Покрыть retry/idempotency/failure contract tests.

## 3. Добавление нового MCP boundary

1. Добавить MCP schemas в `backend/packages/schemas/mcp`.
2. Реализовать сервис от `framework.mcp.BaseFastMcpService`.
3. Подключить `_register_toolset(...)` и `_authorize_tool(...)` для sensitive операций.
4. Добавить `backend/apps/mcp_<name>/main.py` entrypoint.
5. Добавить `run_*.sh/.ps1` и `smoke_*.sh/.ps1`.
6. Добавить unit/integration tests на прямые service-вызовы и script contracts.

## 4. Добавление persistence adapter

1. Определить Protocol/contract в framework/application слое.
2. Реализовать adapter в `backend/packages/infra`.
3. Добавить additive миграцию в `backend/migrations`.
4. Если есть latest/history split, сохранить backward-compatible latest read contract.
5. Покрыть tests на mapping, latest/history lookup и курсоры.

## 5. Минимальный quality gate для каждого extension-слайса

1. Targeted tests по измененному домену.
2. Full gate:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
RUN_DOCKER_ASYNC_E2E=1 RUN_EXTERNAL_LLM_TESTS=1 \
.venv/bin/pytest backend/tests -rs
```
