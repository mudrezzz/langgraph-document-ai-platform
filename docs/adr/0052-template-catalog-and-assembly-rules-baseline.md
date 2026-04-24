# ADR-0052: Template catalog and assembly rules baseline

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0051 authoring уже умел компилировать template specs и собирать template-aware документы, но два важных пробела оставались:

- не было отдельной boundary для `get_template_spec` / template catalog;
- `TemplateSpec` не хранил assembly rules как typed часть шаблона.

Это мешало двигаться к reusable template-driven document generation beyond inline payloads.

## Решение

1. Добавить минимальный `TemplateCatalog` boundary и `InMemoryTemplateCatalog` в `domain_docs`.
2. Расширить `TemplateSpec` полем `assembly_rules`.
3. Научить `TemplateCompiler` компилировать и нормализовать `assembly_rules`, а также задавать default rule для section order.
4. Использовать `assembly_rules` в `DocumentAssembler` для определения section order, а также управления видимостью `Writer Draft` и `Section Traceability`.
5. Сохранить backward compatibility:
   - inline `template_payload` все еще поддерживается;
   - при отсутствии catalog entry используется local compile fallback.

## Последствия

Плюсы:

- появляется reusable boundary под будущий `get_template_spec` API/MCP;
- template-driven assembly становится более явной и управляется из `TemplateSpec`;
- дальнейший переход к persisted template library упрощается.

Минусы:

- catalog пока только in-memory baseline;
- assembly rules пока ограничены базовыми deterministic semantics: `section_order`, `include_writer_draft`, `include_traceability`.
