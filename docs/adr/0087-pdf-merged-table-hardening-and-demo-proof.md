# ADR-0087: PDF merged-table hardening and demo proof contract

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После ADR-0085 parser уже извлекал form-like и rotated PDF структуры, но сложные pipe-like таблицы с wrapped/merged rows оставались частично потерянными. Также для ручного acceptance в demo не хватало явного машинно-проверяемого proof, что extraction сработал именно на реальном `06_audit_summary.pdf`.

## Решение

1. Усилить pipe-table extraction:
   - сохранять пустые ячейки (не схлопывать их раньше времени);
   - распознавать markdown separator rows (`| --- | --- |`);
   - склеивать continuation rows в предыдущую строку (merged/wrapped cell values).
2. Добавить demo proof payload в smoke path:
   - direct smoke (`smoke_knowledge_indexing.py`) отдает `pdf_demo_proof` для `06_audit_summary.pdf`;
   - API smoke (`smoke_knowledge_indexing_api.py`) также отдает `pdf_demo_proof` через task details.
3. В `pdf_demo_proof` фиксировать базовые acceptance признаки:
   - `found`;
   - `doc_id`;
   - `tables_total` / `table_rows_total` (или `blocks_total` в API path);
   - `has_pdf_tables_extracted`;
   - `has_pdf_form_like_blocks_detected`;
   - `has_pdf_rotated_layout_detected`.

## Последствия

Плюсы:

- повышается устойчивость extraction для реальных PDF таблиц с wrapped rows;
- ручной demo smoke получает явное доказательство работоспособности по конкретному PDF fixture;
- решение аддитивно и не ломает API/MCP contracts.

Минусы:

- merged-table эвристики по-прежнему baseline и требуют дальнейшего тюнинга на реальном корпусе;
- `pdf_demo_proof` ориентирован на demo fixture и не заменяет полноценный production quality dashboard.
