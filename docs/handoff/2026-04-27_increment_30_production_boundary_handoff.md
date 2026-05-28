# Increment 30 Production Boundary Handoff

Date: 2026-04-27
Status: ready for stage/prod rehearsal

## What is Transmitted

Increment 30 brought the MCP and service boundary to a production-like baseline:

- Review/Approval MCP;
- Configuration Library MCP;
- unified FastMCP policy metadata;
- RBAC baseline for sensitive API/MCP operations;
- production runbook for deploy/migrate/smoke/backup/restore/rollback.

Main runbook: `docs/production_runbook.md`.

## Minimum Handoff Checklist

Before transferring the environment you need to confirm:

- `backend/scripts/postgres_up.sh` picks up PostgreSQL + pgvector.
- `backend/scripts/postgres_migrate.sh` applies all migrations.
- `backend/scripts/async_up.sh` brings up Redis + Celery worker.
- `backend/scripts/smoke_retrieval_api.sh` runs in the PostgreSQL profile.
- `backend/scripts/smoke_retrieval_async_api.sh` passes with `APP_ASYNC_PROVIDER=celery`.
- `backend/scripts/smoke_knowledge_indexing_api.sh` passes with canonical input.
- `backend/scripts/smoke_authoring_async_api.sh` goes through the HITL path.
- MCP smokes pass for Retrieval, Repository, Artifact Writer, Template Library, Review/Approval and Configuration Library.
- `APP_AUTH_ENABLED=true` gives the expected `401/403/200` at the template governance endpoint.
- `pg_dump -Fc` backup is created and restore rehearsal is described/verified.
- Full pytest gate runs with Docker async e2e and OpenRouter external LLM test.

## Known Gaps

- RBAC baseline trust-based: no signed tokens, SSO, tenant/project scoped permissions.
- MCP actor context is transferred to payload before the external auth proxy/gateway appears.
- Production metrics/dashboard remain outside the current slice.
- OCR/rich layout/table extraction goes to Increment 31.

## Next Increment

Increment 31: Knowledge Factory Hardening.

Focus:

- OCR path for scanned PDF;
- richer layout extraction;
- DOCX tables/lists/appendices;
- `.xlsx`/`.pptx` parser adapters;
- document version/read-model policy;
- configurable quality gates.
