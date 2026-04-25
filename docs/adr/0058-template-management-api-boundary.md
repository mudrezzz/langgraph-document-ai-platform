# ADR-0058: Template management API boundary

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0057 persisted template library уже существовала как внутренняя application boundary, и authoring мог использовать versioned templates. Но сама library еще не имела публичной service boundary: шаблоны можно было сохранить только через внутренний container wiring или тестовый setup, что не соответствовало цели сделать reusable templates управляемой частью платформы.

## Решение

1. Добавить минимальный public API boundary для template management:
   - `PUT /api/v1/templates/{template_id}`;
   - `GET /api/v1/templates/{template_id}`;
   - `GET /api/v1/templates`.
2. Использовать existing `TemplateLibraryApplicationService` и `TemplateCompiler`, не вводя параллельную template architecture.
3. Сохранить scope минимальным: только upsert/get/list без delete, review workflow или RBAC.
4. Не вводить Template MCP на этом шаге; сначала стабилизировать HTTP service boundary.

## Последствия

Плюсы:

- reusable templates теперь можно управляемо регистрировать и читать через публичный API;
- persisted template library становится реально используемой service boundary, а не только внутренним wiring слоем;
- следующий шаг к template MCP или governance policy упрощается.

Минусы:

- API пока не имеет auth/RBAC и approval lifecycle для изменения шаблонов;
- нет delete/archive semantics и нет version promotion policy;
- template management пока ограничен HTTP boundary без отдельного MCP/read-model специализации.
