# ADR-0057: Persisted template library baseline

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0052 и последующих authoring slices система уже умела собирать template-aware документы, но reusable шаблоны по-прежнему жили либо inline в `task_context.template_payload`, либо как локальный in-memory fallback. Это ограничивало повторное использование шаблонов между запросами и не позволяло устойчиво ссылаться на конкретную версию template spec в production-like authoring path.

## Решение

1. Добавить persisted template library baseline через `TemplateLibraryApplicationService` и `PostgresTemplateStore`.
2. Сохранить существующий `TemplateCatalog` boundary, расширив его поддержкой `template_version`.
3. Перевести `AuthoringApplicationService` на resolve path:
   - сначала inline `template_payload`;
   - затем persisted template library по `template_id/template_version`;
   - затем existing local compile fallback.
4. Не вводить отдельный публичный template management API/MCP на этом шаге.
5. Сохранить совместимость существующего authoring API: новые поля в `task_context` опциональны.

## Последствия

Плюсы:

- reusable templates теперь можно хранить и переиспользовать между authoring запросами;
- versioned template resolution становится частью production-compatible authoring path;
- переход к будущему template management API/MCP и governance policy упрощается.

Минусы:

- persisted library пока используется только внутренним application layer без отдельного public endpoint;
- нет policy/approval lifecycle для публикации шаблонов;
- fallback path все еще допускает local compile без store entry, что полезно для bootstrap, но ослабляет strict governance.
