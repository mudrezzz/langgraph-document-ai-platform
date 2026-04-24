# ADR-0050: TemplateCompiler and template-aware section contracts

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0049 authoring domain уже поддерживал section contracts, packets и deterministic section authoring, но секции по-прежнему были фактически зафиксированы на release-readiness use case. Для более широкого набора аналитических сценариев нужен был template-aware слой, который мог бы задавать section structure без переписывания authoring orchestration.

## Решение

1. Добавить `TemplateCompiler` в `domain_docs`.
2. Оставить `TemplateSpec` как typed template contract и разрешить компиляцию из `task_context.template_id` + `task_context.template_payload`.
3. Расширить `SectionContractBuilder`, чтобы он умел строить section contracts из `TemplateSpec`.
4. Интегрировать template-aware path в `AuthoringApplicationService` как optional internal behavior:
   - default template: `release_readiness`;
   - custom templates через `task_context.template_id` и `task_context.template_payload`.
5. Публичный API при этом не менять.

## Последствия

Плюсы:

- authoring layer больше не зашит только под release-readiness report;
- появляется reusable template boundary для будущих document-generation scenarios;
- section contracts и section artifacts теперь могут строиться из внешне задаваемого template spec.

Минусы:

- template storage/catalog пока отсутствует, используется inline payload в `task_context`;
- deterministic assembly пока еще не template-driven до конца.
