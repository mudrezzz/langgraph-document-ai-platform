# ADR-0082: PDF form-like extraction and demo fixture hardening

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0081 PDF parser уже извлекает table-like блоки в `extracted_tables`, но release/governance документы часто содержат form-like key/value секции (approval forms, gate checklists), где данные представлены не как классическая таблица.

Без явной поддержки form-like layouts часть важных полей деградирует до обычных paragraph blocks и теряет table-row provenance в retrieval/report path.

## Решение

1. Расширить PDF table extraction baseline:
   - form-like key/value blocks также отправляются в tabular extraction path;
   - table metadata и row metadata получают `pdf_table_kind` (`form_like|pipe_table|spaced_table`).
2. Добавить parser quality flag `pdf_form_like_blocks_detected`.
3. Обновить demo fixture `06_audit_summary.pdf`, чтобы он содержал:
   - complex table-like release controls;
   - form-like release gate block.
4. Зафиксировать в тестах, что demo PDF дает:
   - `pdf_tables_extracted`;
   - `pdf_form_like_blocks_detected`;
   - canonical `table_row` blocks с `pdf_table_kind=form_like`.

## Последствия

Плюсы:

- retrieval/source mapping получает более точный provenance для form-like PDF sections;
- demo smoke теперь проверяет не только table-like, но и form-like extraction в реальном кейсе;
- сохраняется совместимость публичных API/MCP контрактов.

Минусы:

- form-like extraction пока heuristic и требует будущего hardening для нестандартных шаблонов;
- возможны частичные извлечения в сложных многострочных формах.
