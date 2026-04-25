# ADR-0059: Template Library MCP boundary

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0057 и ADR-0058 persisted template library уже существовала как application boundary и как public HTTP API. Но в MCP-контуре reusable templates еще не были доступны: агентам и automation path приходилось либо работать через HTTP, либо обходить service boundary прямым container wiring.

Для platform-wide authoring это неудобно: templates должны быть доступны тем же образом, как уже доступны repository documents, retrieval search и generated artifacts. При этом нельзя вводить отдельную MCP-specific template архитектуру, иначе template compilation и persistence начнут расходиться между HTTP, authoring и MCP путями.

## Решение

1. Добавить отдельный FastMCP boundary `template-library-mcp`.
2. Включить только минимальные tools:
   - `upsert_template`;
   - `get_template`;
   - `list_templates`.
3. Реализовать MCP service поверх existing `TemplateLibraryApplicationService`:
   - `upsert_template` сначала вызывает `compile_template(...)`, затем сохраняет compiled `TemplateSpec`;
   - `get_template` и `list_templates` читают те же persisted records, что и HTTP/API и authoring path.
4. Добавить typed MCP schemas в `schemas.mcp.template_library`.
5. Добавить runtime/smoke scripts по тому же operational pattern, что уже используется для Retrieval/Repository/Artifact Writer MCP.

## Последствия

Плюсы:

- reusable templates теперь доступны и через MCP, что делает template library частью общего agent-facing service surface;
- MCP path переиспользует existing compiler/persistence boundaries и не расходится с HTTP/API путем;
- authoring automation можно строить через MCP tools без дополнительной glue-логики.

Минусы:

- MCP boundary пока ограничен только CRUD-like read/write path без delete/archive/version-promotion semantics;
- нет auth/RBAC и governance policy для template changes;
- template governance lifecycle closure выполнен в ADR-0063.
