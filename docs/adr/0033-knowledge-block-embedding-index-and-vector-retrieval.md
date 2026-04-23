# ADR-0033: Knowledge block embedding index и vector retrieval

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

ADR-0032 подключил Retrieval Fabric к canonical `knowledge_blocks`, но detail retrieval оставался read-model + lexical/in-memory path. Целевой retrieval fabric должен использовать indexed corpus, embeddings и pgvector.

## Решение

1. Расширить `KnowledgeIndexingApplicationService` optional embedding indexing:
   - embedding gateway строит vector для каждого canonical content block;
   - vector store пишет embedding в `app.embeddings`;
   - metadata связывает vector с `block_ref`, `doc_id`, `block_id`, source path, document type, tags и текстом блока.
2. Сделать локальный `TeiEmbeddingGateway` 1536-dimensional deterministic hashing-vector, совместимый с baseline `VECTOR(1536)`.
3. Расширить `PgVectorStoreAdapter` методом `query_similar(...)`:
   - fallback cosine similarity для unit/smoke;
   - PostgreSQL path через pgvector cosine distance.
4. Добавить `CanonicalVectorRetriever` для canonical detail retrieval.
5. Оставить summary retrieval через section summaries и lexical scorer; vector path применяется к detail blocks.

## Последствия

Плюсы:

- canonical path теперь проходит `documents -> knowledge_blocks -> embeddings -> vector detail retrieval -> evidence`;
- smoke показывает `embeddings_indexed` и `retrieval_backend=pgvector`;
- PostgreSQL path использует существующую таблицу `app.embeddings`.

Минусы:

- локальный embedding gateway остается deterministic stub, а не real TEI HTTP client;
- summary layer пока не векторизуется отдельно;
- metadata хранит текст блока для восстановления retrieval result, что нужно пересмотреть при больших корпусах.
