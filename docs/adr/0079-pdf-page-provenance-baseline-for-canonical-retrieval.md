# ADR-0079: PDF page provenance baseline for canonical retrieval

- Статус: Accepted
- Дата: 2026-04-28

## Контекст

После table-aware provenance (ADR-0074) retrieval fabric уже объясняет строки таблиц, но для PDF evidence оставался разрыв: в indexed retrieval и `lookup_source` нельзя было стабильно увидеть страницу источника и layout hint (`bbox`/layout source). Это снижает проверяемость evidence в ручном smoke/demo и в production traceability.

Также в PDF parser path обнаружен риск коллизий `block_id` на многостраничных документах (локальная нумерация внутри страницы).

## Решение

1. Зафиксировать page-level provenance baseline для PDF blocks в existing canonical metadata path:
   - `source_kind=page_block`;
   - `page_number`;
   - `layout_source`;
   - `bbox` (когда доступен).
2. Исправить PDF parser на глобальную нумерацию `block_id` по документу, чтобы исключить коллизии на multi-page PDF.
3. Прокинуть page provenance без нового storage слоя:
   - в canonical dataset loader;
   - в pgvector retrieval metadata mapping;
   - в `FastMcpRetrievalService.lookup_source` typed provenance payload.
4. Обновить release readiness report source mapping, чтобы он показывал page refs/layout source для PDF evidence.

## Последствия

Плюсы:

- evidence из PDF становится проверяемым по странице в report и MCP lookup;
- multi-page PDF ingestion не теряет уникальность block identity;
- решение переиспользует существующие canonical/vector/read-model contracts без breaking API changes.

Минусы:

- это baseline только для page-level provenance; полноценно rich layout semantics (table/image/form/reading order) остаются отдельным будущим срезом;
- `bbox` остается best-effort полем и зависит от качества layout extraction конкретного PDF.
