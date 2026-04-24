# ADR-0041: Indexed canonical summary retrieval

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

Canonical retrieval уже мог использовать pgvector для detail blocks через `CanonicalVectorRetriever`, но summary слой оставался in-memory: `load_canonical_knowledge_dataset(...)` строил `RetrievedBlock` из `section_summaries`, а `HierarchicalRAGPipeline` искал их через `InMemoryRetriever`.

Для production retrieval fabric это неполно: summary/detail hierarchy должна работать из indexed corpus, иначе large corpus будет требовать загрузки canonical documents в память перед каждым retrieval task.

## Решение

1. Knowledge Indexing пишет embeddings для двух типов canonical artifacts:
   - `knowledge_block_embedding` для `content_blocks`;
   - `knowledge_summary_embedding` для `section_summaries`.
2. Добавить `CanonicalSummaryVectorRetriever` поверх того же `PgVectorStoreAdapter`.
3. Сохранить `CanonicalVectorRetriever` для detail layer.
4. В `build_retrieval_workflow(... knowledge_source="canonical" ...)` использовать pgvector summary/detail retrievers, если доступны `embedding_gateway` и `vector_store`.
5. Оставить in-memory fallback для demo/bootstrap режима и тестов без vector store.
6. Разделять summary/detail records через `metadata.kind`, а наружу возвращать обычный `RetrievedBlock` с `metadata.block_kind`.

## Последствия

Плюсы:

- hierarchical retrieval больше не требует in-memory summary layer при indexed canonical corpus;
- summary/detail records живут в одном vector store и фильтруются через metadata;
- текущие API и workflow state contracts не меняются;
- demo fallback остается совместимым.

Минусы:

- summary embeddings увеличивают объем `app.embeddings`;
- metadata schema для vector records пока свободная и требует дальнейшей стабилизации в retrieval adapter contracts.
