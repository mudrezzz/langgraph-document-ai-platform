# Release Reproducible Flow

Update date: 2026-04-30
Status: Active (P0 ops flow)

Goal: One repeatable path to verify release readiness via `smoke_release_gate` and `release_decision_gate`.

## 1. Preconditions

- Repository: `/root/langgraph-document-ai-platform`
- Python venv + dependencies:

```bash
cd /root/langgraph-document-ai-platform
python3 -m venv .venv
PATH="$(pwd)/.venv/bin:$PATH"
pip install -e ./backend
```

- Docker + compose plugin.

## 2. Runtime bootstrap

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

If you need async/celery rehearsal:

```bash
bash backend/scripts/async_up.sh
```

## 3. Gate profile selection

Basic profiles:

- `dev`: soft checks.
- `stage`: working pre-release baseline.
- `prod`: strict SLA profile.

Recommended baseline for release rehearsal:

```bash
export APP_RUNTIME_PROFILE=prod
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
```

## 4. Step A: unified smoke gate

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

pass criterion:

- `gate_status=pass`
- `failed_checks=[]`
- checks contain valid RG codes (`RG001..RG012`, depending on the profile/LLM requirements)

## 5. Step B: final release decision

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile stage
```

The script does:

1. `smoke_release_gate`
2. full pytest gate
3. recording the final verdict of the artifact

Output artifacts:

- `backend/.release_gate/release_decision_*.json`
- `backend/.release_gate/release_decision_*.md`

## 6. Optional strict LLM token gate

Use if the release policy requires proof of a real LLM path:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true APP_RELEASE_GATE_REQUIRE_LLM_TOKENS=1 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile prod --draft-strategy llm --require-llm-tokens
```

## 7. Triage if gate fails

Minimum triage order:

1. Check `failed_checks` and their `code` (`RG...`) in JSON verdict.
2. Check `artifacts.observability_summary`.
3. Check `artifacts.retrieval_events_summary`.
4. Check `artifacts.authoring.status_payload.details`.
5. Repeat gate with the same profile after the fix.

## 8. Shutdown

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```

If async was not raised, you can skip the first step.
