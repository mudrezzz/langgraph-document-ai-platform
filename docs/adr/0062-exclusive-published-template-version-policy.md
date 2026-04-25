# ADR-0062: Exclusive published template version policy

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0060 template library уже получила lifecycle `draft|published`, а authoring без явного `template_version` стал брать последнюю published version. Но publish semantics все еще были слишком слабыми: один `template_id` мог иметь несколько published versions одновременно.

Для production-like template governance это создает двусмысленность:

- default authoring resolution по published template перестает быть однозначным policy decision;
- HTTP API, MCP и authoring path формально остаются совместимыми, но operator не получает простого invarianta "у шаблона одна активная published version";
- rollback/promotion сценарии становятся менее предсказуемыми.

## Решение

1. Оставить lifecycle статусы без расширения:
   - `draft`;
   - `published`.
2. Изменить publish semantics так, чтобы для одного `template_id` одновременно оставалась только одна published version.
3. При вызове `publish_template(template_id, version)`:
   - выбранная версия получает статус `published`;
   - все остальные published versions того же `template_id` автоматически демотируются в `draft`.
4. Применить это правило одинаково в fallback store, PostgreSQL store, HTTP API и MCP path через existing `TemplateLibraryApplicationService` boundary.
5. Сохранить backward compatibility:
   - API/MCP contracts не меняются;
   - explicit `get_template(template_id, version)` по-прежнему позволяет читать любую version независимо от статуса.

## Последствия

Плюсы:

- published template resolution становится однозначным и проще для operator/runtime;
- publish начинает работать как реальный promotion step, а не просто как добавление еще одной active version;
- authoring, HTTP API и MCP используют одинаковый exclusive-publish invariant.

Минусы:

- publish больше не хранит несколько параллельных active published branches;
- rollback требует повторного publish нужной старой version;
- richer governance с approval history, archived/deprecated states и promotion audit остается отдельным следующим slice.
