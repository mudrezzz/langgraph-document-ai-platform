# ADR-0080: PDF reading-order and layout-kind baseline

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0079 в retrieval появился page-level provenance для PDF, но evidence по-прежнему оставался слишком грубым: не хватало baseline-сигнала о порядке чтения блоков и признака табличной структуры внутри страницы.

Для ручной проверки в demo/report и для downstream retrieval/rerank нужно минимум два дополнительных поля:

- `reading_order_index` (порядок блока на странице);
- `layout_kind` (`paragraph|table_like`).

## Решение

1. В PDF parser path добавить reading-order нормализацию:
   - сортировка layout blocks по `y/x`;
   - запись `reading_order_index` в metadata.
2. Добавить lightweight layout эвристику:
   - `layout_kind=table_like`, если блок похож на табличный (`|`-разделители, key-value row pattern, multi-column spacing);
   - иначе `layout_kind=paragraph`.
3. В parser quality flags добавить `pdf_table_like_blocks_detected` при наличии хотя бы одного `table_like` блока.
4. Прокинуть новые поля без изменения публичных API:
   - canonical retrieval dataset;
   - pgvector metadata mapping;
   - MCP `lookup_source` typed provenance;
   - release report canonical source mapping.

## Последствия

Плюсы:

- evidence из PDF становится лучше объяснимым: видно страницу, порядок и тип layout блока;
- в report/MCP можно явно отделять paragraph vs table-like evidence;
- решение остается совместимым с текущими contracts.

Минусы:

- `table_like` — эвристика и не заменяет полноценное table extraction;
- reading order best-effort и зависит от качества block coordinates конкретного PDF.
