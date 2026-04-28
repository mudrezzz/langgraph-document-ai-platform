# ADR-0083: PDF extraction coverage and partial-failure gates

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0082 parser уже извлекает table/form-like структуры из PDF, но без явной оценки полноты extraction. В production retrieval это риск: частичное извлечение может выглядеть как нормальный success, хотя часть table-like кандидатов не распознана.

## Решение

1. Добавить coverage-метрики для PDF table extraction path:
   - `pdf_table_candidates_total`;
   - `pdf_table_candidates_extracted`;
   - `pdf_table_rows_extracted`;
   - `pdf_table_rows_failed`;
   - `pdf_table_coverage_percent`.
2. Ввести quality flag `pdf_table_extraction_partial` при частичном извлечении (`candidates_failed > 0`).
3. Прокидывать метрики в `parser_quality.issues` metadata:
   - для `pdf_tables_extracted`;
   - для `pdf_table_extraction_partial`.
4. Агрегировать на уровне indexing quality summary:
   - `documents_with_pdf_table_partial`;
   - `documents_with_pdf_form_like`.

## Последствия

Плюсы:

- partial extraction становится наблюдаемым и явно сигнализируется в quality/read-model path;
- ручная и автоматическая оценка качества retrieval evidence по PDF становится прозрачнее;
- решение сохраняет совместимость существующих API/MCP контрактов.

Минусы:

- coverage baseline пока основан на эвристических table-like candidates;
- не решает глубинные сложные layout-кейсы (merged/rotated tables), только делает их видимыми.
