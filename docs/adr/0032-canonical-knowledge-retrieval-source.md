# ADR-0032: Canonical knowledge retrieval source

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

ADR-0031 добавил canonical store и `knowledge_blocks`, но retrieval продолжал использовать только demo dataset loaders (`case_dataset_id`, `case_dataset_path`, `case_dataset_dir`). Это оставляло разрыв между Knowledge Factory output и Retrieval Fabric.

## Решение

1. Добавить loader `load_canonical_knowledge_dataset(...)`, который строит:
   - summary blocks из `CanonicalDocument.section_summaries`;
   - detail blocks из `app.knowledge_blocks`.
2. Расширить `build_retrieval_workflow(...)` режимом `knowledge_source="canonical"`.
3. Расширить `RetrievalApplicationService` и API `task_context`:
   - `knowledge_source: "canonical"`;
   - `canonical_doc_ids: list[str] | str` для ограничения корпуса.
4. Сохранить существующий default путь через demo case datasets для обратной совместимости.
5. Добавить smoke `smoke_canonical_retrieval.sh/.ps1`, который выполняет:
   - canonical indexing demo input;
   - retrieval поверх canonical store;
   - проверку evidence pack и `knowledge_source=canonical`.

## Последствия

Плюсы:

- Knowledge Factory output впервые используется Retrieval Fabric напрямую;
- demo corpus может проходить path `documents -> canonical documents -> knowledge_blocks -> evidence pack`;
- API contract остается backward-compatible.

Минусы:

- retrieval по canonical store пока lexical/in-memory после чтения read-model;
- pgvector/embedding write path еще не подключен;
- canonical source smoke запускает indexing и retrieval в одном процессе для fallback-контура.
