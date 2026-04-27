# ADR-0075: XLSX parser baseline for canonical ingestion

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

После DOCX table extraction и table-aware retrieval provenance система уже умеет хорошо работать с табличным evidence. Следующий production-relevant формат для такого evidence — `.xlsx`: approval trackers, risk registers, release matrices и контрольные чеклисты часто приходят именно в Excel.

Нельзя строить отдельный ingestion path для spreadsheet-документов. XLSX должен входить в тот же canonical/indexing/retrieval контур, что и DOCX/PDF/JSON.

## Решение

1. Добавить `.xlsx` в supported extensions canonical parser.
2. Реализовать baseline parser на `openpyxl`:
   - workbook sheets становятся structural sections;
   - sheet header + rows извлекаются как canonical table;
   - строки таблицы становятся `table_row` blocks;
   - metadata включает `sheet_name`.
3. Binary demo input расширить реальным fixture `08_release_tracker.xlsx`.
4. Не вводить отдельный spreadsheet-specific retrieval stack: XLSX reuse-ит existing `CanonicalDocument`, `KnowledgeIndexingApplicationService`, vector indexing и retrieval provenance path.

## Последствия

Плюсы:

- ingestion покрывает еще один частый enterprise format;
- табличное evidence из Excel сразу доступно для retrieval/MCP/reporting;
- решение естественно продолжает уже введенный table-aware provenance path.

Минусы:

- baseline parser пока ориентирован на sheet-level tabular extraction, без merged-cells/formatting/formulas semantics;
- `.xls` и rich workbook semantics остаются вне текущего slice.
