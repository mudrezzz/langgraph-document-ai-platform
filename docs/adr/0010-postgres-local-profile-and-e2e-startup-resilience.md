# ADR-0010: Local PostgreSQL profile and stability of e2e API launch

- Status: Accepted
- Date: 2026-04-18

## Context

After `Increment 5` persistence adapters and migrations were already added, but there was no standardized way to quickly get PostgreSQL up and running locally and run smoke/e2e scripts in the same profile.

Additionally, it turned out that e2e fixtures on a real `uvicorn` crashed too early with `connection refused` during server startup, without informative diagnostics.

## Solution

1. Fix the standard local PostgreSQL profile:
   - `backend/docker-compose.postgres.yml`;
   - `backend/.env.example`;
   - `backend/scripts/postgres_up.ps1`;
   - `backend/scripts/postgres_migrate.ps1`;
   - `backend/scripts/postgres_down.ps1`.
2. Add a separate e2e circuit with real PostgreSQL:
   - `backend/tests/e2e/test_fastapi_retrieval_e2e_postgres.py`.
3. Strengthen the reliability of the e2e-start API:
- while waiting for `/health`, treat `URLError` as a temporary state;
- when `uvicorn` terminates early, throw an error from `stdout/stderr` process.

## Consequences

Pros:

- local PostgreSQL bootstrap has become reproducible and documented;
- e2e coverage checks not only in-memory mode, but also real DB runtime;
- API startup failures are now diagnosed faster via stderr, without “silent” timeouts.

Cons:

- e2e PostgreSQL requires Docker and runs longer than in-memory e2e;
- the test circuit is more difficult to maintain due to its dependence on the external container.
