# Environment & Config Reference

Update date: 2026-04-30
Status: Active (P0 reference)

The document documents runtime env contracts and their effects.

Source of truth: `backend/apps/api/dependencies.py`, `backend/apps/api/security.py`, `backend/apps/worker/celery_app.py`, `backend/packages/infra/*`, `backend/scripts/smoke_release_gate.py`.

## 1. Core runtime / persistence

| Variable | Default | Effect |
|---|---|---|
| `APP_RUNTIME_PROFILE` | `dev` | Profile `dev|stage|prod`; in `prod` fallback persistence is disabled. |
| `APP_DB_DSN` | - | PostgreSQL DSN for API/persistence adapters. |
| `APP_DB_SCHEMA` | `app` | SQL schema for Postgres adapters. |
| `APP_VECTOR_DIM` | `1536` | Embeddings dimension for vector path. |

## 2. Auth / RBAC

| Variable | Default | Effect |
|---|---|---|
| `APP_AUTH_ENABLED` | `false` | Enables role checks in API and MCP sensitive operations. |

At `APP_AUTH_ENABLED=true`:

- API uses `X-Actor-Id`, `X-Actor-Roles`.
- MCP write/sensitive tools expect `actor`, `roles` in payload.

## 3. Async execution plane

| Variable | Default | Effect |
|---|---|---|
| `APP_ASYNC_PROVIDER` | `inline` | Provider async execution: `inline|celery`. |
| `APP_CELERY_BROKER_URL` | `redis://127.0.0.1:56379/0` | Broker for celery worker. |
| `APP_CELERY_RESULT_BACKEND` | broker value | Result backend celery. |
| `APP_CELERY_QUEUE` | `authoring` | Authoring tasks/HITL continuation queue. |
| `APP_CELERY_INDEXING_QUEUE` | `knowledge-indexing` | Queue knowledge indexing tasks. |
| `APP_CELERY_RETRIEVAL_QUEUE` | `retrieval` | Queue retrieval tasks. |
| `APP_WORKER_DB_DSN` | `postgresql://app:app@host.docker.internal:55432/langgraph` | DSN for worker in `docker-compose.async.yml` (compose-level override). |

## 4. LLM authoring

| Variable | Default | Effect |
|---|---|---|
| `APP_LLM_ENABLED` | `false` | Includes LLM draft path for authoring. |
| `APP_LLM_STRICT` | `false` | With `true` LLM configuration errors do not fall back in deterministic mode. |
| `APP_LLM_PROVIDER` | `openrouter` | Provider (`openrouter`, `vllm_mock`, other). |
| `OPENROUTER_API_KEY` | - | OpenRouter API key. |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Base URL OpenRouter API. |
| `OPENROUTER_TIMEOUT_SEC` | `60` | Timeout OpenRouter HTTP calls. |
| `OPENROUTER_APP_NAME` | `langgraph-document-ai-platform` | App name header for OpenRouter. |
| `OPENROUTER_APP_URL` | `http://localhost` | App URL header for OpenRouter. |
| `VLLM_MODEL_NAME` | `mock-vllm-model` | Model name for `APP_LLM_PROVIDER=vllm_mock`. |

## 5. TEI embedding/rerank gateways

| Variable | Default | Effect |
|---|---|---|
| `TEI_BASE_URL` | empty | Base URL TEI; used to derive `/embed` and `/rerank`. |
| `TEI_EMBEDDING_URL` | empty | Explicit endpoint embeddings (precedence over `TEI_BASE_URL`). |
| `TEI_RERANK_URL` | empty | Explicit endpoint rerank (precedence over `TEI_BASE_URL`). |
| `TEI_API_KEY` | empty | Optional API key for TEI HTTP requests. |
| `TEI_TIMEOUT_SEC` | `30` | Timeout TEI requests. |
| `TEI_FALLBACK_ENABLED` | `false` | Allows deterministic fallback in case of TEI error. |

## 6. OCR / parsing quality

| Variable | Default | Effect |
|---|---|---|
| `APP_OCR_ENABLED` | `true` | Enables OCR fallback path in parser. |
| `APP_OCR_PROVIDER` | `sidecar` | OCR provider (`sidecar` or `ocrmypdf`). |
| `APP_OCR_LANGUAGE` | `eng` | Text OCRmyPDF (`-l` flag). |
| `APP_OCR_TIMEOUT_SEC` | `120` | Timeout OCRmyPDF subprocess. |

## 7. Knowledge indexing quality policy

| Variable | Default | Effect |
|---|---|---|
| `APP_INDEXING_QUALITY_POLICY_NAME` | `default_indexing_quality_policy_v1` | Name policy in output summary. |
| `APP_INDEXING_QUALITY_BLOCKING_FLAGS` | empty | CSV quality flags blocking accepted path. |
| `APP_INDEXING_QUALITY_WARNING_ONLY_FLAGS` | empty | CSV warning-only flags. |
| `APP_INDEXING_ALLOW_RECOVERED_OCR` | `true` | Allows accepted path after successful OCR recover. |
| `APP_INDEXING_OCR_RECOVERY_BLOCKING_FLAG` | `pdf_no_extractable_text` | Flag considered blocking before recovery. |
| `APP_INDEXING_OCR_RECOVERY_SUCCESS_FLAG` | `ocr_applied` | Successful recovery flag. |
| `APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE` | `0` | Low-confidence threshold for form-like PDF extraction. |
| `APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING` | `false` | Does low form-confidence blocking. |
| `APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE` | `0` | Low-confidence OCR score threshold. |
| `APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING` | `false` | Does low OCR-confidence blocking. |

## 8. HITL limits and SLA aggregates

| Variable | Default | Effect |
|---|---|---|
| `APP_HITL_MAX_ITERATIONS` | `2` | Maximum reviewer loop iterations. |
| `APP_HITL_WAIT_TIMEOUT_SEC` | `1800` | Time window for waiting for human decision. |
| `APP_SLA_TASK_DURATION_MS` | empty | SLA threshold for task duration (observability). |
| `APP_SLA_QUEUE_WAIT_MS` | empty | SLA threshold for queue wait (observability). |

Note: an empty/invalid/`<=0` SLA threshold value disables the corresponding breach check.

## 9. Release gate policy env

Source: `backend/scripts/smoke_release_gate.py`.

| Variable | Default | Effect |
|---|---|---|
| `APP_RELEASE_GATE_PROFILE` | `dev` | Gate policy profile (`dev|stage|prod`). |
| `APP_RELEASE_GATE_MIN_EVENTS_TOTAL` | profile value | Minimum events for retrieval checks. |
| `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS` | profile value | Minimum total tasks in observability checks. |
| `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES` | profile value | Upper limit of duration SLA breaches (`-1` disables). |
| `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES` | profile value | Upper limit of queue wait breaches (`-1` disables). |
| `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS` | profile value | Require non-zero `llm_tokens_total` + `draft_generation_mode=llm`. |

## 10. Logging

| Variable | Default | Effect |
|---|---|---|
| `APP_LOG_LEVEL` | `INFO` | Structured runtime logs level (`infra.logging.runtime`). |

## 11. Recommended baseline profiles

- Local dev:
  - `APP_RUNTIME_PROFILE=dev`
  - `APP_ASYNC_PROVIDER=inline`
- Stage-like verification:
  - `APP_RUNTIME_PROFILE=stage`
- `APP_ASYNC_PROVIDER=inline` or `celery`
- Prod-like rehearsal:
  - `APP_RUNTIME_PROFILE=prod`
  - `APP_AUTH_ENABLED=true`
- `APP_ASYNC_PROVIDER=celery` (if the next circuit is checked)

## 12. Related documents

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/mcp_reference.md`
- `docs/developer_guide/operations_and_release.md`
