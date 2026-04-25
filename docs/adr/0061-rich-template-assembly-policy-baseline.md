# ADR-0061: Rich template assembly policy baseline

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0052, ADR-0053 и ADR-0060 reusable template library уже умела хранить `TemplateSpec`, а authoring уже поддерживал template-aware section contracts, deterministic assembly и `markdown|json` export. Но assembly policy оставалась слишком узкой:

- `assembly_rules` фактически управляли только `section_order`, `include_writer_draft`, `include_traceability`;
- optional/conditional sections нельзя было описать в самом template payload;
- JSON export и section traceability для custom templates отставали от richer assembly semantics;
- traceability по умолчанию оставалась в основном release-readiness specific.

Для reusable authoring framework этого недостаточно: templates нужны не только для одного demo report, но и для более широкого класса документов, где appendix sections, evidence-driven sections и reviewer-only sections должны включаться детерминированно из policy, а не из ad hoc логики orchestration.

## Решение

1. Расширить normalized `TemplateSpec.sections` минимальным richer policy набором:
   - `required`;
   - `include_if_has_evidence`;
   - `include_if_review_status`;
   - `section_group`.
2. Расширить normalized `TemplateSpec.assembly_rules` полями:
   - `include_sections`;
   - `exclude_sections`;
   - `allowed_section_groups`.
3. Оставить `DocumentAssembler` единым source of truth для section selection:
   - required sections включаются всегда, если не попали под явный exclude/group filter;
   - optional sections включаются по evidence или review status policy;
   - include/exclude/group filters применяются как deterministic assembly gate.
4. Заставить `ArtifactExporter` переиспользовать тот же section-selection path, чтобы markdown и JSON не расходились по составу секций.
5. Сделать `OutlinePlanner` template-aware:
   - если есть `TemplateSpec` и `SectionContract` list, traceability строится по тем же template sections, а не по hardcoded release-readiness layout.
6. Сохранить backward compatibility:
   - старый release-readiness fallback path остается рабочим;
   - existing authoring API не меняется;
   - templates без новых полей продолжают вести себя как раньше.

## Последствия

Плюсы:

- reusable templates теперь могут описывать optional appendix/evidence/reviewer sections без изменения application orchestration;
- markdown export, JSON export и traceability становятся консистентными для custom templates;
- richer template semantics остаются в existing `TemplateCompiler` / `DocumentAssembler` / `OutlinePlanner`, без параллельной архитектуры.

Минусы:

- policy пока intentionally минимальна: нет произвольных boolean expressions, nested rule engine или per-section rendering strategies;
- traceability still derives source refs из existing contracts/evidence heuristics, а не из отдельного section planning graph;
- более развитая template governance и richer authoring layout policy остаются следующими slice'ами.
