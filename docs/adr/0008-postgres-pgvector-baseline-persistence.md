# ADR-0008: Baseline persistence на PostgreSQL + pgvector

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

После внедрения LangGraph runtime и API lifecycle было необходимо заменить чисто in-memory persistence на реальный baseline слой хранения, совместимый с целевым стеком (`PostgreSQL + pgvector`).

## Решение

1. Реализовать SQL-backed adapters:
   - `PostgresDocumentRepository`;
   - `LangGraphPostgresCheckpointStore`;
   - `PgVectorStoreAdapter`.
2. Ввести `PostgresSettings` c env-конфигурацией:
   - `APP_DB_DSN`;
   - `APP_DB_SCHEMA`;
   - `APP_VECTOR_DIM`.
3. Добавить baseline миграцию `backend/migrations/0001_baseline.sql`.
4. Добавить скрипты применения миграций:
   - `backend/scripts/apply_migrations.py`;
   - `backend/scripts/apply_migrations.ps1`.
5. Сохранить controlled fallback в dev/test до появления runtime profiles.

## Последствия

Плюсы:

- архитектура приблизилась к целевому persistence стеку;
- появился повторяемый путь инициализации БД через миграции;
- контракт adapters готов к подключению production persistence.

Минусы:

- fallback-режим требует отдельной политики для prod;
- пока нет end-to-end интеграции с реальным LangGraph checkpointer API.