# ADR-0008: Baseline persistence on PostgreSQL + pgvector

- Status: Accepted
- Date: 2026-04-17

## Context

After implementing the LangGraph runtime and API lifecycle, it was necessary to replace the purely in-memory persistence with a real baseline storage layer compatible with the target stack (`PostgreSQL + pgvector`).

## Solution

1. Implement SQL-backed adapters:
   - `PostgresDocumentRepository`;
   - `LangGraphPostgresCheckpointStore`;
   - `PgVectorStoreAdapter`.
2. Enter `PostgresSettings` with env configuration:
   - `APP_DB_DSN`;
   - `APP_DB_SCHEMA`;
   - `APP_VECTOR_DIM`.
3. Add baseline migration `backend/migrations/0001_baseline.sql`.
4. Add scripts for applying migrations:
   - `backend/scripts/apply_migrations.py`;
   - `backend/scripts/apply_migrations.ps1`.
5. Save controlled fallback in dev/test until runtime profiles appear.

## Consequences

Pros:

- the architecture has moved closer to the target persistence stack;
- a repeatable path for database initialization through migrations has appeared;
- the adapters contract is ready to connect production persistence.

Cons:

- fallback mode requires a separate policy for prod;
- there is no end-to-end integration with the real LangGraph checkpointer API yet.
