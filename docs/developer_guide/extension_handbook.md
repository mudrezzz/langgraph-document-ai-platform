# Extension Handbook

Дата обновления: 2026-04-30  
Статус: Active (P0 extension set)

Цель: дать repeatable path для расширений по ключевым типам изменений framework-слоя.

Базовые документы:

- `docs/framework_extension_guide.md`
- `docs/developer_guide/extension_recipes.md`
- `docs/developer_guide/public_contract_surface.md`

## 1. Workflow extension playbook

Когда использовать: новый workflow/state-machine path (retrieval/authoring/indexing-like сценарии).

Минимальный change set:

1. Добавить/обновить state contract:
   - `backend/packages/schemas/workflow/*` (или доменные `schemas`).
2. Реализовать workflow:
   - `backend/packages/domain_*/**/workflows.py`
   - на базе `framework.workflows.BaseWorkflow`.
3. Добавить task lifecycle orchestration:
   - `backend/packages/application/*_service.py`.
4. Подключить API endpoint (если внешний contract нужен):
   - `backend/apps/api/main.py`
   - `backend/packages/schemas/api/contracts.py`.
5. Добавить smoke/test coverage:
   - `backend/tests/*`
   - `backend/scripts/smoke_*`.

Критические правила:

- сохранять `task_context.task_id` для checkpoint consistency;
- не ломать `invoke/resume` compatibility;
- сохранять node events в task audit через existing sink path.

## 2. Tool extension playbook

Когда использовать: новый domain tool для workflow execution.

Минимальный change set:

1. Реализовать `BaseTool`-совместимый инструмент (`framework.tools` contracts).
2. Зарегистрировать tool в registry/executor path.
3. Задать execution policy (retry/idempotency/audit).
4. Прописать typed input/output models в `schemas`.
5. Добавить unit tests на success/retry/failure/idempotency.

Критические правила:

- все публичные payload-ы типизировать через Pydantic;
- чувствительные операции должны быть совместимы с RBAC policy.

## 3. MCP extension playbook

Когда использовать: новый MCP boundary или расширение существующего.

Минимальный change set:

1. Добавить MCP contracts:
   - `backend/packages/schemas/mcp/<service>.py`.
2. Реализовать сервис:
   - `backend/packages/infra/fastmcp/<service>_service.py`
   - на базе `BaseFastMcpService`.
3. Зарегистрировать toolset с корректными scopes/roles:
   - `_register_toolset(...)`
   - `_authorize_tool(...)` для write/sensitive операций.
4. Добавить app entrypoint:
   - `backend/apps/mcp_<service>/main.py`.
5. Добавить scripts:
   - `backend/scripts/run_<service>_mcp.sh/.ps1`
   - `backend/scripts/smoke_<service>_mcp.sh/.ps1/.py`.

Критические правила:

- соблюдать naming/scope policy (`read|write|action`);
- errors отдавать через единый operation error mapping;
- обновлять `docs/developer_guide/mcp_reference.md`.

## 4. Persistence extension playbook

Когда использовать: новый store/read-model или расширение текущей схемы данных.

Минимальный change set:

1. Определить interface/contract (framework/application слой).
2. Реализовать adapter в `backend/packages/infra/postgres/*`.
3. Добавить additive миграцию:
   - `backend/migrations/00xx_*.sql`.
4. Встроить в DI:
   - `backend/apps/api/dependencies.py`.
5. Добавить tests:
   - mapping/read-model/cursor/history paths.

Критические правила:

- additive migrations only;
- не ломать latest/history read contracts;
- фиксировать новые runtime effects в `env_config_reference.md` (если есть новые env).

## 5. Domain extension playbook

Когда использовать: новая бизнес-логика в `domain_docs`, `domain_rag`, `domain_authoring` или новом `domain_*` модуле.

Минимальный change set:

1. Добавить domain contracts/models в `schemas`.
2. Добавить domain services/workflows.
3. Интегрировать через application service (не напрямую в API).
4. Добавить smoke/demo proof path в `backend/scripts`.
5. Обновить docs:
   - concept/reference/guides + `docs/DOCS_BACKLOG.md`.

Критические правила:

- домен не должен обходить task lifecycle;
- observability fields для новых long-running path должны попадать в existing summary endpoints.

## 6. Definition of done for any extension

Extension считается завершенным, если:

1. Контракты типизированы и покрыты тестами.
2. Есть smoke proof path (script or API flow).
3. Обновлены соответствующие docs разделы.
4. Обновлен `docs/DOCS_BACKLOG.md`.
