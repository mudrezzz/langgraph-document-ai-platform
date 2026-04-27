# ADR-0074: Table-aware canonical retrieval provenance

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

После DOCX hardening строки таблиц уже попадают в canonical corpus как `table_row` blocks. Retrieval и MCP search умеют находить такие блоки, но source mapping оставался слишком плоским: consumer видел только `doc_id/block_id`, без явного ответа, что evidence пришел из таблицы, из какой именно таблицы и какой строки.

Это снижает production value retrieval fabric: найденный approval status трудно быстро проверить вручную и трудно объяснить в report/traceability path.

## Решение

1. Не вводить отдельный provenance store или новую retrieval архитектуру.
2. Сохранять table-aware provenance в existing canonical/vector metadata path для `table_row` blocks:
   - `source_kind=table_row`;
   - `table_id`, `table_title`, `table_columns`;
   - `row_index`, `row_values`;
   - `section_title`.
3. `CanonicalVectorRetriever` и dataset loader должны прокидывать эти поля в `RetrievedBlock.metadata`.
4. `FastMcpRetrievalService.lookup_source` должен возвращать typed provenance payload и table payload для table-backed evidence.
5. Release readiness report должен уметь показать table-aware source mapping для табличных evidence blocks.

## Последствия

Плюсы:

- найденное evidence можно объяснить и проверить как конкретную строку approval matrix;
- MCP lookup/source mapping становится пригоднее для downstream authoring/traceability;
- решение переиспользует existing canonical documents, knowledge blocks и vector metadata.

Минусы:

- metadata schema vector records становится богаче и требует аккуратной совместимости;
- report layer пока показывает агрегированную table provenance, а не полный cell-level trace.
