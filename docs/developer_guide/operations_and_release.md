# Operations And Release

This document captures a production-like run for an external developer: smoke matrix -> release decision gate -> full pytest gate.

For a linear step-by-step scenario, also use:

- `docs/developer_guide/release_reproducible_flow.md`

## 1. Runtime prerequisites

- `.venv` with dependencies (`pip install -e ./backend`)
- Docker + docker compose
- `backend/.env` with `OPENROUTER_*` (for optional external LLM tests)

## 2. Unified release-gate smoke

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

Expect `gate_status=pass` and empty `failed_checks`.

## 3. Final release decision gate

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile stage
```

The result is stored in `backend/.release_gate/release_decision_*.json` and `.md`.

## 4. Full test gate (mandatory)

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
RUN_DOCKER_ASYNC_E2E=1 RUN_EXTERNAL_LLM_TESTS=1 \
.venv/bin/pytest backend/tests -rs
```

Note: Do not use `source backend/.env` in the test gate.

## 5. Where to look at llm_tokens consumption

`llm_tokens_*` appear only when authoring actually goes through the LLM path.

Minimum smoke to check token usage:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm
```

Next in the smoke response, check `details.llm_tokens_prompt`, `details.llm_tokens_completion`, `details.llm_tokens_total`.

## 6. Related documents

- `docs/developer_guide/release_reproducible_flow.md`
- `docs/production_runbook.md`
- `docs/manual_smoke_postgres_runbook.md`
- `backend/scripts/README.md`
