# ADR-0081: PDF table extraction baseline for canonical ingestion

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0080 PDF path уже давал `reading_order_index` и `layout_kind`, но это оставалось эвристическим hint-слоем. Для production retrieval/traceability нужен тот же уровень source precision, что уже есть для DOCX/XLSX: таблицы в `extracted_tables` и строки как canonical `table_row` blocks.

## Решение

1. Добавить baseline table extraction в PDF parser:
   - для `layout_kind=table_like` пробовать собрать табличную спецификацию;
   - поддержать lightweight patterns: `|`-разделители, key-value rows, multi-column spacing;
   - при успехе создавать `CanonicalTable` (`PDF-T-*`) и `table_row` blocks.
2. Прокидывать provenance для PDF table rows:
   - `source_kind=table_row`;
   - `table_id`, `row_index`;
   - `page_number`, `reading_order_index`, `layout_kind`, `layout_source`, `bbox`.
3. Добавить parser quality flag `pdf_tables_extracted`.
4. Не вводить отдельный PDF-table store: переиспользовать существующий canonical store + retrieval metadata path.

## Последствия

Плюсы:

- retrieval/source mapping для PDF теперь может ссылаться на конкретную строку таблицы, а не только на page block;
- унификация с DOCX/XLSX table-aware path;
- без breaking changes в API/MCP контрактах.

Минусы:

- extraction остаётся best-effort heuristic baseline и не покрывает сложные merged/rotated tables;
- для сложных PDF потребуется отдельный hardening slice (специализированный table detector/parser).
