# Production Runbook

Дата обновления: 2026-04-27
Статус: Increment 30 production-boundary baseline

Этот runbook описывает минимальный stage/prod rehearsal для backend/framework контура: PostgreSQL, pgvector, FastAPI, Celery/Redis, MCP services, auth/RBAC smoke, backup/restore и rollback.

## 1. Runtime Topology

Минимальный production-like контур:

- PostgreSQL + pgvector для tasks, events, checkpoints, artifacts, templates, canonical documents, configuration library и vector index.
- FastAPI app: `apps.api.main:app`.
- Redis + Celery worker для async execution plane: authoring, retrieval, knowledge indexing и HITL continuation.
- Optional FastMCP services:
  - Retrieval MCP;
  - Repository MCP;
  - Artifact Writer MCP;
  - Template Library MCP;
  - Review/Approval MCP;
  - Configuration Library MCP.
- Optional external gateways:
  - OpenRouter для LLM authoring smoke;
  - TEI `/embed` и `/rerank` для real retrieval fabric.

## 2. Required Environment

Базовый `backend/.env` для stage/prod rehearsal:

```bash
APP_RUNTIME_PROFILE=prod
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
APP_DB_SCHEMA=app
APP_VECTOR_DIM=1536

APP_ASYNC_PROVIDER=celery
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0
APP_CELERY_QUEUE=authoring
APP_CELERY_INDEXING_QUEUE=knowledge-indexing
APP_CELERY_RETRIEVAL_QUEUE=retrieval
APP_WORKER_DB_DSN=postgresql://app:app@host.docker.internal:55432/langgraph

APP_AUTH_ENABLED=false
APP_HITL_MAX_ITERATIONS=2
APP_HITL_WAIT_TIMEOUT_SEC=1800

APP_LLM_ENABLED=false
APP_LLM_PROVIDER=openrouter
APP_LLM_STRICT=false
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT_SEC=60

TEI_BASE_URL=
TEI_EMBEDDING_URL=
TEI_RERANK_URL=
TEI_API_KEY=
TEI_TIMEOUT_SEC=30
TEI_FALLBACK_ENABLED=false

POSTGRES_DB=langgraph
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_PORT=55432
REDIS_PORT=56379
```

Notes:

- `APP_RUNTIME_PROFILE=prod` disables critical in-memory persistence fallback.
- `APP_AUTH_ENABLED=false` keeps existing smoke/demo scripts simple; switch it to `true` for RBAC rehearsal.
- For automated pytest gates, do not `source backend/.env`; pass only required variables explicitly.

## 3. Deploy And Migrate

From repository root:

```bash
python3 -m venv .venv
.venv/bin/python - <<'PY' > /tmp/langgraph_backend_requirements.txt
import tomllib
from pathlib import Path

data = tomllib.loads(Path('backend/pyproject.toml').read_text())
for item in data['project']['dependencies']:
    print(item)
PY
.venv/bin/pip install -r /tmp/langgraph_backend_requirements.txt
.venv/bin/pip install uvicorn pytest fastmcp

bash backend/scripts/postgres_up.sh
PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
```

Expected result:

- PostgreSQL container is healthy.
- Redis and Celery worker containers are running.
- Migrations apply without pending SQL errors.

## 4. FastAPI Smoke

Run the core API path:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

Then run canonical indexing and retrieval:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8011 --build-binary-demo-docs

APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
```

Expected result:

- retrieval task is `completed`;
- task history and task events are visible;
- canonical indexing stores documents and blocks;
- canonical retrieval returns evidence with `retrieval_backend=pgvector`.

## 5. Async/Celery Smoke

Run retrieval, knowledge indexing and authoring through the async execution plane:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_CELERY_RETRIEVAL_QUEUE=retrieval \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_async_api.sh --host 127.0.0.1 --port 8076

APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_CELERY_INDEXING_QUEUE=knowledge-indexing \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_knowledge_indexing_api.sh --host 127.0.0.1 --port 8075 --build-binary-demo-docs

APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_ASYNC_PROVIDER=celery \
APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0 \
APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0 \
APP_HITL_MAX_ITERATIONS=2 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_async_api.sh --host 127.0.0.1 --port 8050 --workflow-mode multi_step --hitl-required --hitl-decision-sequence needs_changes,approve
```

Expected result:

- queued tasks move to `running` and then `completed` or `waiting_human` as expected;
- observability summary shows async task counts;
- iterative HITL path reaches final `completed` after `needs_changes,approve`.

## 6. MCP Smoke

Run MCP service smokes from repository root:

```bash
APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_repository_mcp.sh

APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_artifact_writer_mcp.sh

APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_template_library_mcp.sh

APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_retrieval_mcp.sh --build-binary-demo-docs

APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_review_approval_mcp.sh

APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
bash backend/scripts/smoke_configuration_library_mcp.sh
```

Expected result:

- every smoke exits with code `0`;
- MCP metadata exposes `transport`, `service_scope`, `operation_scopes`, `auth_policy` and `tool_required_roles`;
- write/approval tools work with auth disabled.

## 7. RBAC Rehearsal

Switch `APP_AUTH_ENABLED=true` and restart the API process. Then keep API running:

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
APP_AUTH_ENABLED=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010 --keep-server
```

Check template governance:

```bash
curl -i -X PUT "http://127.0.0.1:8010/api/v1/templates/rbac_demo" \
  -H 'Content-Type: application/json' \
  -d '{"version":"1","sections":[{"section_id":"overview","title":"Overview"}]}'

curl -i -X PUT "http://127.0.0.1:8010/api/v1/templates/rbac_demo" \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-Id: alice' \
  -H 'X-Actor-Roles: template_admin' \
  -d '{"version":"1","sections":[{"section_id":"overview","title":"Overview"}]}'
```

Expected result:

- first request returns `401 Unauthorized`;
- second request returns `200 OK`.

Stop the kept server:

```bash
kill "$(cat backend/.smoke_uvicorn_8010.pid)" && rm -f backend/.smoke_uvicorn_8010.pid
```

## 8. Backup And Restore

Create a compressed PostgreSQL backup:

```bash
mkdir -p backend/.backups
docker exec langgraph-db pg_dump -U app -d langgraph -Fc > backend/.backups/langgraph_$(date -u +%Y%m%dT%H%M%SZ).dump
```

Restore rehearsal into the same local profile requires stopping writers first:

```bash
bash backend/scripts/async_down.sh

BACKUP_FILE="backend/.backups/<backup-file>.dump"
docker exec -i langgraph-db dropdb -U app --if-exists langgraph
docker exec -i langgraph-db createdb -U app langgraph
cat "${BACKUP_FILE}" | docker exec -i langgraph-db pg_restore -U app -d langgraph --clean --if-exists

PATH="$(pwd)/.venv/bin:$PATH" bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
```

Expected result:

- restore command exits with code `0`;
- migrations are idempotent after restore;
- FastAPI smoke passes again.

## 9. Rollback

Application rollback:

1. Stop API/MCP processes.
2. Stop async workers: `bash backend/scripts/async_down.sh`.
3. Deploy the previous git revision or container image.
4. Restart workers and API.
5. Run FastAPI smoke and one MCP smoke.

Database rollback:

- SQL migrations are additive in the current baseline.
- Use backup/restore for rollback rehearsal.
- Before applying new migrations in stage/prod, capture a fresh `pg_dump -Fc` backup.

Rollback acceptance:

- `smoke_retrieval_api.sh` passes;
- `smoke_retrieval_async_api.sh` passes when Celery is enabled;
- at least one persisted MCP smoke passes;
- `GET /api/v1/tasks/observability/summary` responds after the rollback.

## 10. Release Gate

Before handoff, run the full automated gate without sourcing `backend/.env`:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
RUN_DOCKER_ASYNC_E2E=1 RUN_EXTERNAL_LLM_TESTS=1 \
.venv/bin/pytest backend/tests -rs
```

Required result for this baseline:

- all unit/integration/e2e tests pass;
- Docker async e2e runs;
- OpenRouter external LLM test runs when credentials are present.

## 11. Shutdown

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh
```

For destructive local cleanup only:

```bash
bash backend/scripts/async_down.sh --remove-volumes
bash backend/scripts/postgres_down.sh --remove-volumes
```
