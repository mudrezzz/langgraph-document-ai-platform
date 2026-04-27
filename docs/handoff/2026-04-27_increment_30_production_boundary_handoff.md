# Increment 30 Production Boundary Handoff

Дата: 2026-04-27
Статус: ready for stage/prod rehearsal

## Что Передается

Increment 30 довел MCP и service boundary до production-like baseline:

- Review/Approval MCP;
- Configuration Library MCP;
- unified FastMCP policy metadata;
- RBAC baseline для sensitive API/MCP operations;
- production runbook для deploy/migrate/smoke/backup/restore/rollback.

Основной runbook: `docs/production_runbook.md`.

## Минимальный Handoff Checklist

Перед передачей окружения нужно подтвердить:

- `backend/scripts/postgres_up.sh` поднимает PostgreSQL + pgvector.
- `backend/scripts/postgres_migrate.sh` применяет все миграции.
- `backend/scripts/async_up.sh` поднимает Redis + Celery worker.
- `backend/scripts/smoke_retrieval_api.sh` проходит в PostgreSQL профиле.
- `backend/scripts/smoke_retrieval_async_api.sh` проходит с `APP_ASYNC_PROVIDER=celery`.
- `backend/scripts/smoke_knowledge_indexing_api.sh` проходит с canonical input.
- `backend/scripts/smoke_authoring_async_api.sh` проходит HITL path.
- MCP smokes проходят для Retrieval, Repository, Artifact Writer, Template Library, Review/Approval и Configuration Library.
- `APP_AUTH_ENABLED=true` дает ожидаемые `401/403/200` на template governance endpoint.
- `pg_dump -Fc` backup создан и restore rehearsal описан/проверен.
- Полный pytest gate проходит с Docker async e2e и OpenRouter external LLM test.

## Known Gaps

- RBAC baseline trust-based: нет signed tokens, SSO, tenant/project scoped permissions.
- MCP actor context передается в payload до появления внешнего auth proxy/gateway.
- Production metrics/dashboard остаются вне текущего среза.
- OCR/rich layout/table extraction переходит в Increment 31.

## Следующий Инкремент

Increment 31: Knowledge Factory Hardening.

Фокус:

- OCR path для scanned PDF;
- richer layout extraction;
- DOCX tables/lists/appendices;
- `.xlsx`/`.pptx` parser adapters;
- document version/read-model policy;
- configurable quality gates.
