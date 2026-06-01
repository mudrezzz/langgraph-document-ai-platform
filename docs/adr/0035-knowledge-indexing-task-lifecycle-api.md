# ADR-0035: Knowledge Indexing task lifecycle API

Date: 2026-04-23

Status: Accepted

## Context

Knowledge Factory already knew how to parse documents, save canonical documents, derived `knowledge_blocks` and embeddings. But indexing was only run as an application service/smoke script, so one of the Increment 25 criteria was not met: the indexing task must be visible in the task registry and task events in the same way as retrieval and authoring tasks.

## Solution

1. Add endpoint `POST /api/v1/tasks/knowledge-indexing/start`.
2. Start indexing via `KnowledgeIndexingApplicationService.start_task`.
3. Create a task record with `task_type=knowledge_indexing`.
4. If successful, save the checkpoint payload and change the task to `completed`.
5. If there is an error, save a valid initial payload and transfer the task to `failed`.
6. Write task details:
- counts by documents/content blocks/section summaries;
   - `indexed_doc_ids`;
   - `file_types`;
   - `embeddings_indexed`;
   - `quality_flags`;
   - `quality_summary`;
   - `quality_gate_status`.
7. Add smoke API `smoke_knowledge_indexing_api.sh/.ps1`.

## Consequences

- Knowledge Indexing is now checked through the common task lifecycle API.
- `GET /api/v1/tasks/{task_id}` works for indexing tasks without a separate status endpoint.
- `GET /api/v1/tasks/events/summary?task_type=knowledge_indexing` shows task indexing transitions.
- Quality gate is still a summary policy (`passed|warning|failed`), and not a blocking production policy layer.
- Canonical `doc_id` must be stable between relative and absolute path runs.
- Canonical vector retrieval, if there are `canonical_doc_ids`, must filter embeddings by these document ids so that old indexing runs in the same database do not pollute the evidence pack.
