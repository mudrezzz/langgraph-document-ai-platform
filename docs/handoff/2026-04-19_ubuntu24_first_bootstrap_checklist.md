# Ubuntu 24 First Bootstrap Checklist

- Date: 2026-04-19
- Repository: `https://github.com/mudrezzz/langgraph-document-ai-platform`
- Branch: `main`

## 1. Quick command checklist (10 steps)

```bash
#1) Basic packages
sudo apt update && sudo apt install -y git curl python3 python3-venv python3-pip ca-certificates gnupg

#2) Clone the repository
git clone https://github.com/mudrezzz/langgraph-document-ai-platform.git

#3) Go to the project
cd langgraph-document-ai-platform

#4) Create venv
python3 -m venv .venv

# 5) Activate venv
source .venv/bin/activate

# 6) Install minimal dependencies for launch/tests
python -m pip install -U pip
python -m pip install fastapi uvicorn pydantic psycopg[binary] pytest

# 7) Prepare the backend env file
cp backend/.env.example backend/.env

# 8) Raise PostgreSQL + pgvector
bash backend/scripts/postgres_up.sh

# 9) Roll out migrations and make smoke
bash backend/scripts/postgres_migrate.sh
APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010

# 10) Run tests and clean postgres
python -m pytest backend/tests -q
bash backend/scripts/postgres_down.sh --remove-volumes
```

## 2. What is considered a successful launch

- in smoke JSON:
  - `start_status=completed`
  - `task_status=completed`
  - `evidence_blocks >= 1`
  - `history_contains_task=true`
- tests pass:
- at least `unit/integration` should be green;
- postgres e2e can be `skipped` if docker daemon is not available.

## 3. Start prompt for Codex chat on a Linux server

```text
We are working in the repository https://github.com/mudrezzz/langgraph-document-ai-platform, main branch.
Context: retrieval API, LangGraph runtime, PostgreSQL+pgvector persistence, persistent task registry and task history endpoint are implemented.
The project has been moved to Ubuntu 24; backend/scripts already has bash scripts for postgres/migrations/smoke/demo.

We need to continue with the next iteration:
1) enter runtime profiles dev/stage/prod and disable fallback persistence in prod;
2) expand GET /api/v1/tasks with filters (status, task_type, from/to) and cursor pagination;
3) add task_events to audit status transitions;
4) update README, ADR and System Architecture Overview;
5) add/update unit/integration/e2e tests and run smoke.

Requirements:
- comments in the code in Russian;
- after each increment, update README, docs/adr/* and docs/architecture/System_Architecture_Overview.md.
```
