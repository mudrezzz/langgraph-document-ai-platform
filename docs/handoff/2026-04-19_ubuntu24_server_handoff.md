# Handoff: Ubuntu 24 Server Migration

- Date: 2026-04-19
- Latest commit: `d4e4613`
- Repository: `https://github.com/mudrezzz/langgraph-document-ai-platform`
- Main branch: `main`

## 1. Current state of the project

The system already supports:

- typed FastAPI API for retrieval lifecycle:
  - `POST /api/v1/tasks/retrieval/start`
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/evidence`
  - `POST /api/v1/tasks/{task_id}/resume`
- `GET /api/v1/tasks` (task history)
- LangGraph execution inside `BaseWorkflow` (`invoke/resume`);
- persistence baseline via PostgreSQL + pgvector;
- persistent `TaskRegistry` (`app.tasks`, migration `0002_task_registry.sql`);
- test coverage:
- unit / integration / e2e (including postgres e2e);
- reference-case:
  - `saa_release_readiness_case`;
- smoke/demo scripts.

## 2. What needs to be done in the new chat (next iteration)

Goal of server iteration:

1. Deploy and test the project on Ubuntu 24 (not on Windows).
2. Enter runtime profiles (`dev/stage/prod`) and disable fallback persistence in `prod`.
3. Expand the task history API:
- filters (`status`, `task_type`, time range);
- cursor pagination.
4. Add auditing of task status transitions (`task_events`).

## 3. Minimal Ubuntu 24 environment

Install packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl ca-certificates gnupg
```

Install Docker + Compose plugin (official Docker repo) and add the user to the `docker` group.

Requirements for Python dependencies of the project:

- `fastapi`
- `uvicorn`
- `pydantic`
- `psycopg[binary]`
- `pytest`
- other dependencies from the `requirements`/poetry/uv-file of the project (if added in future iterations)

## 4. Basic launch on the server

```bash
git clone https://github.com/mudrezzz/langgraph-document-ai-platform.git
cd langgraph-document-ai-platform

cp backend/.env.example backend/.env
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh

APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010

python -m pytest backend/tests -q

bash backend/scripts/postgres_down.sh --remove-volumes
```

## 5. Starting text for a new chat

```text
We are working with the repository https://github.com/mudrezzz/langgraph-document-ai-platform, main branch.
Context: retrieval API, LangGraph runtime, PostgreSQL+pgvector persistence, persistent task registry and task history endpoint are implemented.
We need to continue the server iteration on Ubuntu 24:
1) enter runtime profiles dev/stage/prod and disable fallback in prod;
2) expand GET /api/v1/tasks with filters and cursor pagination;
3) add task_events to audit status transitions;
4) update README, ADR and System Architecture Overview;
5) cover new unit/integration/e2e changes with tests and run smoke.
Comments in the code are in Russian.
```

## 6. Quick bootstrap checklist

See separate document:

- `docs/handoff/2026-04-19_ubuntu24_first_bootstrap_checklist.md`
