# ADR-0070: Unified FastMCP Service Policies

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

К середине Increment 30 в платформе уже есть несколько FastMCP boundaries:

- retrieval;
- repository;
- artifact writer;
- template library;
- review/approval;
- configuration library.

Все они построены по одному общему паттерну, но фактически metadata и error mapping оставались частично ad-hoc: каждый сервис сам собирал `tool_names`, не было общего поля `service_scope`, не был зафиксирован единый `operation_scope`, а error mapping в MCP-friendly `ValueError` повторялся вручную в каждом сервисе.

Для production-like MCP surface такой уровень расхождений уже нежелателен: новые boundary будут копировать разные локальные паттерны, а внешний интегратор не сможет рассчитывать на единообразный service contract.

## Решение

1. Расширить `BaseFastMcpService` как единый policy carrier для FastMCP boundaries.
2. Зафиксировать единый metadata contract для всех MCP сервисов:
   - `service_name`;
   - `version`;
   - `transport=fastmcp`;
   - `service_scope`;
   - `policy_version=mcp-policy-v1`;
   - `tool_names`;
   - `operation_scopes`;
   - `input_validation` / `output_validation`;
   - `error_mapping`;
   - `audit_payload_fields`.
3. Добавить helper `_register_toolset(...)`, который:
   - валидирует tool naming (`snake_case`);
   - регистрирует единый `tool_names` list;
   - вычисляет или принимает explicit `operation_scope` для каждого tool.
4. Использовать простую operation-scope модель:
   - `read` для `get/list/lookup/search/find/compare`;
   - `write` для `upsert/write/publish/set/submit`;
   - `action` для execution-style tools вроде `build_evidence_pack`.
5. Добавить helper `_operation_error(...)` и перевести MCP services на единый error mapping вместо ручного `raise ValueError(str(exc))` в каждой реализации.
6. Не ломать существующие tool names и runtime entrypoints; policy change должен быть additive и backward-compatible для текущих callers.

## Последствия

Плюсы:

- все FastMCP boundaries теперь отдают единообразный metadata payload;
- новые MCP services проще добавлять по одному шаблону;
- auth/RBAC, audit и operational runbook проще строить поверх уже унифицированного metadata surface;
- тесты могут проверять MCP policy contract централизованно, а не только per-service behavior.

Минусы:

- metadata payload стал шире, чем в ранних MVP slices;
- `operation_scope` пока heuristic-based и может потребовать refinement при появлении более сложных tool semantics;
- unified error mapping пока по-прежнему основан на `ValueError`, а не на отдельной richer MCP error taxonomy.
