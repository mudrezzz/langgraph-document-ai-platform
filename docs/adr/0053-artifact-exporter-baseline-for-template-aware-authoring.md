# ADR-0053: Artifact exporter baseline for template-aware authoring

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После выделения `DocumentAssembler` и template-aware assembly pipeline authoring уже умел строить section-oriented итоговый документ, но весь выход все еще фактически считался markdown-first. В scope `Increment 28` изначально был заложен `ArtifactExporter`, чтобы отделить deterministic assembly от формата выдачи артефакта.

## Решение

1. Добавить `domain_authoring.ArtifactExporter` как отдельный domain service.
2. Оставить `DocumentAssembler` ответственным только за deterministic assembly content.
3. Делегировать `AuthoringApplicationService` финальный export в `ArtifactExporter`.
4. Поддержать baseline export formats:
   - `markdown` как текущий backward-compatible путь;
   - `json` как structured template-aware artifact payload.
5. Для `json` export использовать те же `TemplateSpec`, `section_artifacts`, `review_result` и assembly visibility rules (`include_writer_draft`, `include_traceability`).

## Последствия

Плюсы:

- появляется явная boundary между assembly и artifact rendering;
- authoring становится менее привязанным к markdown-only output;
- путь к дальнейшим export formats (`html`, `docx`, external delivery adapters) становится проще.

Минусы:

- export policy пока минимальная и поддерживает только `markdown|json`;
- json export пока не вынесен в отдельный public schema contract, а опирается на deterministic payload shape.
