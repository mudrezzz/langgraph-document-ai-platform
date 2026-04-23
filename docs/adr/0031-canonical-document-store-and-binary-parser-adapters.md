# ADR-0031: Canonical document store и binary parser adapters

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

ADR-0030 добавил первый Knowledge Factory MVP: canonical contracts, `domain_docs`, parser `.md/.txt/.json` и `KnowledgeIndexingWorkflow`. Но canonical payload сохранялся через общий document repository boundary, а не через отдельный read-model слой. Также целевой ТЗ требует поддержку PDF/DOCX parsing стандартными библиотеками.

## Решение

1. Добавить отдельный persistence/read-model слой:
   - `app.canonical_documents`;
   - `app.knowledge_blocks`;
   - миграция `backend/migrations/0009_canonical_knowledge_store.sql`.
2. Добавить `CanonicalDocumentApplicationService`.
3. Добавить `PostgresCanonicalDocumentStore` с in-memory fallback для dev/test.
4. Переключить `KnowledgeIndexingApplicationService` на canonical store boundary.
5. Расширить parser boundary форматами `.docx` и `.pdf`.
6. Использовать lazy imports:
   - `python-docx` для DOCX;
   - `PyMuPDF` для PDF.
7. Зафиксировать зависимости в `backend/pyproject.toml`, но оставить ошибки adapter-level явными, если runtime окружение еще не установило optional package.

## Последствия

Плюсы:

- canonical documents и derived knowledge blocks больше не смешаны с generic document repository;
- retrieval fabric сможет читать `app.knowledge_blocks` как следующий шаг;
- binary parser boundary заложен без принудительного выполнения PDF/DOCX tests в окружении без зависимостей.

Минусы:

- требуется новая миграция `0009`;
- PDF/DOCX parsing пока базовый и не включает OCR, tables или rich layout extraction;
- retrieval еще не переключен на canonical knowledge blocks.
