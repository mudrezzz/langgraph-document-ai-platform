# ADR-0043: Retrieval quality gates

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

Production Retrieval Fabric должен не только возвращать evidence blocks, но и явно фиксировать слабые места результата. В ТЗ и backlog уже были выделены low evidence count, low confidence, missing methodology/source refs и unresolved gaps. До этого `EvidencePack.unresolved_gaps` и `confidence_notes` существовали в schema, но не заполнялись framework layer.

## Решение

1. Добавить `RetrievalQualityPolicy` в framework RAG layer:
   - `min_evidence_count`;
   - `min_confidence_score`;
   - `required_document_types`.
2. Применять policy внутри `EvidenceBuilder`, потому что это единая точка сборки normalized `EvidencePack`.
3. Заполнять:
   - `EvidencePack.unresolved_gaps`;
   - `EvidencePack.confidence_notes`.
4. Поддержать gates:
   - low evidence count;
   - low confidence;
   - missing required document types, включая `methodology`;
   - missing source refs.
5. В retrieval task details сохранять:
   - `quality_gate_status`;
   - `unresolved_gaps`;
   - `confidence_notes`.
6. Release readiness report показывает retrieval confidence, quality gate и unresolved gaps.

## Последствия

Плюсы:

- quality diagnostics становятся частью существующего API/evidence contract без миграций;
- authoring и MCP consumers получают unresolved gaps через тот же `EvidencePack`;
- release demo может явно показывать confidence и gaps;
- policy остается framework-level и не привязана к конкретному domain dataset.

Минусы:

- текущий статус gate остается advisory, workflow не переводится в failed при warning gaps;
- thresholds пока заданы в bootstrap, а не в отдельном runtime config object.
