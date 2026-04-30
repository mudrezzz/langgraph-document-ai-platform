# Quickstart

Дата обновления: 2026-04-30  
Статус: Entry point для нового разработчика

Этот quickstart отвечает на вопрос:  
`я зашел в docs/developer_guide, что делать дальше?`

## 1. За 10 минут: понять карту проекта

Пройди в таком порядке:

1. `docs/developer_guide/public_contract_surface.md`
2. `docs/developer_guide/framework_concepts.md`
3. `docs/developer_guide/examples_catalog.md`

Результат:

- понимаешь, что считается stable/experimental;
- видишь, где framework, где application/domain/infra;
- выбираешь ближайший пример под свою задачу.

## 2. Выбери цель и иди по маршруту

## Цель A: расширить существующий функционал

Иди по шагам:

1. `docs/developer_guide/extension_handbook.md`  
   Выбери тип расширения: `workflow | tool | MCP | persistence | domain`.
2. `docs/developer_guide/extension_recipes.md`  
   Возьми минимальный change set и quality gate.
3. Нужны контракты:
   - HTTP: `docs/developer_guide/api_reference.md`
   - MCP: `docs/developer_guide/mcp_reference.md`
4. После изменений:
   - обнови `docs/DOCS_BACKLOG.md`
   - проверь docs contracts:  
     `.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py`

## Цель B: быстро создать нового агента/agent flow

В этом проекте “агент” обычно собирается как:  
`workflow + tools + (опционально) MCP/API boundary`.

Быстрый путь:

1. `docs/developer_guide/framework_concepts.md`  
   Понять runtime модель (`BaseWorkflow`, async plane, HITL).
2. `docs/developer_guide/extension_handbook.md`  
   Разделы `Workflow extension` и `Tool extension`.
3. `docs/framework_extension_guide.md`  
   Проверить framework constraints и extension hooks.
4. Нужен внешний интерфейс:
   - API endpoint: `docs/developer_guide/api_reference.md`
   - MCP tool: `docs/developer_guide/mcp_reference.md`
5. Используй пример для старта:
   - retrieval-first
   - authoring-first
   - mcp-first  
   из `docs/developer_guide/examples_catalog.md`.

## Цель C: разобраться с прод-путем и release

1. `docs/developer_guide/env_profile_snippets.md`
2. `docs/developer_guide/release_reproducible_flow.md`
3. `docs/developer_guide/operations_and_release.md`
4. `docs/developer_guide/observability_reference.md`

## 3. Что читать по роли

- Integrator:  
  `examples_catalog -> api_reference -> mcp_reference -> env_profile_snippets`
- Contributor:  
  `framework_concepts -> extension_handbook -> extension_recipes -> adr_reading_map`
- Maintainer:  
  `maintainer_playbook -> observability_reference -> release_reproducible_flow`

## 4. Если нужно именно поднять окружение

Этот quickstart про навигацию по документации.  
Для runtime/bootstrap используй:

1. `docs/developer_guide/env_profile_snippets.md`
2. `docs/developer_guide/manual_demo_checks.md`
3. `backend/scripts/README.md`

## 5. Минимальный definition of done для первой задачи

После первого изменения в коде:

1. Есть working path через smoke/demo.
2. Обновлены релевантные docs.
3. Обновлен `docs/DOCS_BACKLOG.md`.
