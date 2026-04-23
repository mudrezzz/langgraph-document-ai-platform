# ADR-0035: Knowledge Indexing task lifecycle API

Дата: 2026-04-23

Статус: Accepted

## Контекст

Knowledge Factory уже умел парсить документы, сохранять canonical documents, derived `knowledge_blocks` и embeddings. Но indexing запускался только как application service / smoke script, поэтому не выполнялся один из критериев Increment 25: indexing task должен быть видимым в task registry и task events так же, как retrieval и authoring tasks.

## Решение

1. Добавить endpoint `POST /api/v1/tasks/knowledge-indexing/start`.
2. Запускать indexing через `KnowledgeIndexingApplicationService.start_task`.
3. Создавать task record с `task_type=knowledge_indexing`.
4. При успехе сохранять checkpoint payload и переводить task в `completed`.
5. При ошибке сохранять валидный initial payload и переводить task в `failed`.
6. Писать task details:
   - counts по documents/content blocks/section summaries;
   - `indexed_doc_ids`;
   - `file_types`;
   - `embeddings_indexed`;
   - `quality_flags`;
   - `quality_summary`;
   - `quality_gate_status`.
7. Добавить API smoke `smoke_knowledge_indexing_api.sh/.ps1`.

## Последствия

- Knowledge Indexing теперь проверяется через общий task lifecycle API.
- `GET /api/v1/tasks/{task_id}` работает для indexing tasks без отдельного status endpoint.
- `GET /api/v1/tasks/events/summary?task_type=knowledge_indexing` показывает переходы indexing задач.
- Quality gate пока является summary policy (`passed|warning|failed`), а не блокирующим production policy layer.
- Canonical `doc_id` должен быть стабильным между относительным и абсолютным path запуском.
- Canonical vector retrieval при наличии `canonical_doc_ids` обязан фильтровать embeddings по этим document ids, чтобы старые indexing-прогоны в той же БД не загрязняли evidence pack.
