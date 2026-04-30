# Operations And Release

Этот документ фиксирует production-like прогон для внешнего разработчика: smoke matrix -> release decision gate -> full pytest gate.

Для линейного пошагового сценария используйте также:

- `docs/developer_guide/release_reproducible_flow.md`

## 1. Runtime prerequisites

- `.venv` с зависимостями (`pip install -e ./backend`)
- Docker + docker compose
- `backend/.env` с `OPENROUTER_*` (для optional external LLM tests)

## 2. Unified release-gate smoke

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

Ожидается `gate_status=pass` и пустой `failed_checks`.

## 3. Final release decision gate

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile stage
```

Результат сохраняется в `backend/.release_gate/release_decision_*.json` и `.md`.

## 4. Полный тестовый gate (обязательный)

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
RUN_DOCKER_ASYNC_E2E=1 RUN_EXTERNAL_LLM_TESTS=1 \
.venv/bin/pytest backend/tests -rs
```

Примечание: не используйте `source backend/.env` в тестовом gate.

## 5. Где смотреть llm_tokens расход

`llm_tokens_*` появляются только когда authoring реально проходит через LLM path.

Минимальный smoke для проверки token usage:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
APP_RUNTIME_PROFILE=prod APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph APP_DB_SCHEMA=app \
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_authoring_api.sh --host 127.0.0.1 --port 8030 --workflow-mode multi_step --draft-strategy llm --require-llm
```

Далее в ответе smoke проверяйте `details.llm_tokens_prompt`, `details.llm_tokens_completion`, `details.llm_tokens_total`.

## 6. Связанные документы

- `docs/developer_guide/release_reproducible_flow.md`
- `docs/production_runbook.md`
- `docs/manual_smoke_postgres_runbook.md`
- `backend/scripts/README.md`
