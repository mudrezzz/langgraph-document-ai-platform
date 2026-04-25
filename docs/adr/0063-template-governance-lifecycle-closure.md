# ADR-0063: Template governance lifecycle closure

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0060 и ADR-0062 template library уже имела `draft|published` и exclusive publish invariant. Этого было достаточно для baseline authoring, но governance оставалась незавершенной:

- operator не мог явно помечать template version как deprecated или archived;
- HTTP API и MCP не давали общего explicit lifecycle transition path, кроме publish;
- authoring explicit version lookup по-прежнему мог брать version без distinction между deprecated и archived;
- governance audit не фиксировался в persisted metadata.

Для reusable template library этого уже недостаточно: library стала public service boundary и должна поддерживать минимально production-compatible lifecycle без введения отдельного approval subsystem.

## Решение

1. Закрыть lifecycle статусы reusable template version до набора:
   - `draft`;
   - `published`;
   - `deprecated`;
   - `archived`.
2. Сохранить `publish_template(template_id, version)` как backward-compatible shortcut, но реализовывать publish через общий status-transition path.
3. Добавить explicit lifecycle transition boundary:
   - application: `TemplateLibraryApplicationService.set_template_status(...)`;
   - HTTP API: `POST /api/v1/templates/{template_id}/status`;
   - MCP: `set_template_status` tool.
4. Хранить lightweight governance audit внутри existing `metadata` поля template record:
   - `metadata.governance.current_status`;
   - `metadata.governance.updated_at`;
   - `metadata.governance.updated_by`;
   - `metadata.governance.reason`;
   - `metadata.governance.status_history[]`.
5. Зафиксировать минимальные transition rules:
   - `draft -> published|deprecated|archived`;
   - `published -> draft|deprecated|archived`;
   - `deprecated -> draft|published|archived`;
   - `archived` terminal и не реактивируется.
6. Ужесточить authoring resolution policy:
   - без явного `template_version` разрешен только `published` template;
   - explicit `template_version` может читать `draft|published|deprecated`;
   - explicit `archived` template для authoring запрещен.
7. Не вводить отдельный governance store, approval workflow или RBAC subsystem в этом slice.

## Последствия

Плюсы:

- template library получает законченный минимальный lifecycle для production-like operations;
- API, MCP, authoring и persistence используют единый governance contract;
- archived templates перестают случайно использоваться в authoring path;
- governance audit остается в existing persistence model без новой архитектурной ветки.

Минусы:

- approval chain, reviewer assignment и RBAC по-прежнему отсутствуют;
- governance audit хранится как metadata JSONB, а не как отдельный normalized event store;
- archived version нельзя реактивировать без создания новой version или ручного DB вмешательства.
