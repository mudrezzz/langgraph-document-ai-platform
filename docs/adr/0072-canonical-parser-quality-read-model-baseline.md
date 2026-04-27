# ADR-0072: Canonical parser quality read-model baseline

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

Increment 31 начинает Knowledge Factory Hardening. До этого canonical ingestion хранил только плоский `quality_flags` список на уровне документа и aggregated `quality_summary` на уровне indexing task details.

Этого достаточно для MVP gate `passed|warning|failed`, но недостаточно для production hardening:

- нельзя понять parser family и extraction mode по документу;
- нельзя отделить info/warning/blocking parser issues;
- сложно видеть, какие документы содержат tables, нуждаются в OCR или потеряли структуру;
- следующие slices (`OCR`, rich layout, DOCX tables/lists, `.xlsx/.pptx`) будут добавлять extraction behavior без измеримого read-model слоя.

## Решение

1. Добавить typed parser quality contracts в `schemas.documents`:
   - `ParserQualityIssue`;
   - `ParserQualitySummary`.
2. Расширить `CanonicalDocument` полем `parser_quality` без изменения existing ingestion API contract.
3. `CanonicalDocumentParser` теперь обязан заполнять:
   - `parser_family`;
   - `extraction_mode`;
   - counts (`blocks/headings/lists/tables/pages`);
   - typed issues и mirrored `flags`.
4. Existing `quality_flags` сохраняются как backward-compatible coarse signal и продолжают использоваться текущим indexing quality gate.
5. `KnowledgeIndexingApplicationService` прокидывает parser diagnostics в task details и aggregated `quality_summary`:
   - `parser_families`;
   - `extraction_modes`;
   - `parser_issues_total`;
   - `documents_with_tables`;
   - `documents_needing_ocr`.
6. Retrieval/reporting surfaces получают `parser_quality` только как read-model metadata, без отдельной parser-specific runtime ветки.

## Последствия

Плюсы:

- появляется production-compatible измерительный слой для parser hardening;
- smoke/demo/report теперь могут показывать parser diagnostics по документам;
- будущие OCR/table/layout slices можно внедрять поверх уже существующего typed quality read-model;
- existing APIs и quality gate semantics остаются совместимыми.

Минусы:

- quality gate по-прежнему опирается на `quality_flags`, а не на fully configurable production policy layer;
- parser quality counters пока ограничены текущими `.md/.txt/.json/.docx/.pdf` adapters;
- extracted tables/layout blocks еще не сохраняются как отдельные canonical entities.
