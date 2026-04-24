# ADR-0051: Template-aware deterministic assembly

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0050 authoring уже поддерживал `TemplateCompiler`, template-aware section contracts и `section_artifacts`, но финальная deterministic assembly все еще оставалась по сути release-readiness specific и опиралась в основном на общий writer draft. Это ограничивало reuse для других document-generation сценариев.

## Решение

1. Расширить `DocumentAssembler`, чтобы он умел собирать документ из:
   - `TemplateSpec`;
   - `section_artifacts`;
   - reviewer summary и traceability.
2. Сохранить backward compatibility:
   - без template/section artifacts assembler продолжает старый release-readiness path;
   - при наличии template-aware данных используется section-oriented deterministic assembly.
3. Не менять публичные API и artifact contract shape.

## Последствия

Плюсы:

- deterministic assembly становится reusable для разных template-driven задач;
- section artifacts начинают влиять на итоговый документ, а не только жить в metadata;
- следующий шаг к полноценному section-by-section authoring pipeline упрощается.

Минусы:

- assembly пока еще не использует отдельные assembly rules/catalog beyond inline `TemplateSpec`;
- writer draft по-прежнему сохраняется как часть итогового документа для наблюдаемости и обратной совместимости.
