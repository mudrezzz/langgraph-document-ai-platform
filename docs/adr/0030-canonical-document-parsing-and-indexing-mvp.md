# ADR-0030: Canonical document parsing и indexing MVP

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

После `Increment 24` framework layer получил extension guide и contract tests. Следующий крупный GAP к целевой архитектуре - Knowledge Factory: canonical document model, parsing, quality flags и indexing workflow.

Полный целевой слой включает PDF/DOCX/OCR, отдельные таблицы canonical documents / knowledge blocks и pgvector-backed indexing. Для первого backend/framework среза нужен меньший вертикальный шаг, который можно проверить на существующем release go/no-go demo.

## Решение

1. Расширить `schemas.documents` типизированными canonical contracts:
   - `CanonicalStructureNode`;
   - `CanonicalContentBlock`;
   - `CanonicalTable`;
   - `CanonicalSectionSummary`;
   - `CanonicalDocument`.
2. Добавить `domain_docs` как отдельный domain package.
3. Реализовать `CanonicalDocumentParser` для text-like MVP форматов:
   - `.md`;
   - `.txt`;
   - `.json`.
4. Добавить `KnowledgeIndexingWorkflow` поверх `BaseWorkflow`.
5. На первом срезе сохранять canonical payload через существующий `DocumentApplicationService` и `app.documents`, без новой миграции.
6. Добавить smoke `smoke_knowledge_indexing.sh/.ps1`, который индексирует текущий release go/no-go multifile demo input.

## Последствия

Плюсы:

- появился первый reusable `domain_docs` слой;
- canonical ingestion можно тестировать без FastAPI и без новой БД-схемы;
- текущий demo сценарий получил Knowledge Factory smoke.

Минусы:

- PDF/DOCX/OCR еще не реализованы;
- canonical documents и knowledge blocks пока не разнесены по отдельным таблицам;
- retrieval пока не читает indexed canonical corpus напрямую.
