# Env Profile Snippets

Update date: 2026-04-30
Status: Active (P1 onboarding ergonomics)

Ready-made minimal env profiles for quick launch.

## 1. Local dev (sync + fallback-friendly)

```bash
export APP_RUNTIME_PROFILE=dev
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
export APP_VECTOR_DIM=1536
export APP_ASYNC_PROVIDER=inline
export APP_AUTH_ENABLED=false
```

Recommended smoke:

```bash
bash backend/scripts/smoke_retrieval_api.sh --host 127.0.0.1 --port 8010
```

## 2. Stage-like (canonical + gates)

```bash
export APP_RUNTIME_PROFILE=stage
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
export APP_VECTOR_DIM=1536
export APP_ASYNC_PROVIDER=inline
export APP_AUTH_ENABLED=true
export APP_SLA_TASK_DURATION_MS=180000
export APP_SLA_QUEUE_WAIT_MS=20000
```

Recommended smoke:

```bash
bash backend/scripts/smoke_canonical_retrieval.sh --build-binary-demo-docs
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile stage
```

## 3. Prod-like rehearsal (celery + strict gates)

```bash
export APP_RUNTIME_PROFILE=prod
export APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph
export APP_DB_SCHEMA=app
export APP_VECTOR_DIM=1536
export APP_AUTH_ENABLED=true

export APP_ASYNC_PROVIDER=celery
export APP_CELERY_BROKER_URL=redis://127.0.0.1:56379/0
export APP_CELERY_RESULT_BACKEND=redis://127.0.0.1:56379/0
export APP_CELERY_QUEUE=authoring
export APP_CELERY_INDEXING_QUEUE=knowledge-indexing
export APP_CELERY_RETRIEVAL_QUEUE=retrieval

export APP_SLA_TASK_DURATION_MS=120000
export APP_SLA_QUEUE_WAIT_MS=10000
export APP_RELEASE_GATE_PROFILE=prod
```

Optional for LLM strict gate:

```bash
export APP_LLM_ENABLED=true
export APP_LLM_PROVIDER=openrouter
export APP_LLM_STRICT=true
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=openai/gpt-4o-mini
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export APP_RELEASE_GATE_REQUIRE_LLM_TOKENS=1
```

Recommended smoke:

```bash
bash backend/scripts/async_up.sh
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile prod
```

## 4. Quick sanity checks

For the current shell:

```bash
echo "$APP_RUNTIME_PROFILE $APP_ASYNC_PROVIDER $APP_AUTH_ENABLED"
```

Checking API availability:

```bash
curl -sS http://127.0.0.1:8088/health
```

## 5. Related documents

- `docs/developer_guide/env_config_reference.md`
- `docs/developer_guide/quickstart.md`
- `docs/developer_guide/release_reproducible_flow.md`
