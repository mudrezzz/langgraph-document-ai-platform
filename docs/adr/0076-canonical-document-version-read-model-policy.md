# ADR-0076: Canonical document version read-model policy

- Статус: Accepted
- Дата: 2026-04-27

## Контекст

К Increment 31 canonical ingestion уже сохраняет production-relevant document formats и indexed retrieval corpus. Но persistence policy все еще была фактически single-version per `doc_id`: повторный indexing перезаписывал document row и latest knowledge blocks, а historical version lookup отсутствовал.

Для production retrieval fabric этого недостаточно. Нужны:

1. stable canonical identity по `doc_id`;
2. latest-by-default чтение без ломки существующих API и retrieval path;
3. explicit version lookup для source tracing и controlled re-index semantics.

## Решение

1. Сохранить existing latest-read contract:
   - `app.canonical_documents` и `app.knowledge_blocks` остаются latest snapshot по `doc_id`.
2. Добавить separate history read-model:
   - `app.canonical_document_versions`;
   - `app.knowledge_block_versions`.
3. `CanonicalDocumentApplicationService` работает по policy:
   - `get_document(doc_id)` -> latest version;
   - `get_document(doc_id, version=...)` -> explicit historical version;
   - `list_documents(...)` -> latest only;
   - `list_versions(doc_id, ...)` -> history list.
4. Knowledge indexing request получает explicit `document_version`.
5. Re-index semantics:
   - latest snapshot и latest vectors replace-ятся по `doc_id`;
   - historical canonical versions сохраняются и доступны для explicit lookup;
   - vector index остается latest-oriented, без отдельного historical vector plane.
6. Retrieval MCP `lookup_source` принимает optional `version` и также может резолвить historical `block_ref` формата `doc_id:version:block_id`.

## Последствия

Плюсы:

- сохраняется backward compatibility для existing canonical retrieval и MCP flows;
- появляется audit/source-trace path к historical canonical versions;
- re-index semantics становятся явными и predictable.

Минусы:

- historical retrieval search через pgvector пока не поддерживается как отдельный search plane;
- vector index отражает только latest snapshot, поэтому historical lookup доступен для source resolution, а не для общего semantic search.
