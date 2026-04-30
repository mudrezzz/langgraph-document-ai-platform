# Environment & Config Reference

Дата обновления: 2026-04-30  
Статус: Active (P0 reference)

Документ фиксирует runtime env-контракты и их эффекты.

Источник истины: `backend/apps/api/dependencies.py`, `backend/apps/api/security.py`, `backend/apps/worker/celery_app.py`, `backend/packages/infra/*`, `backend/scripts/smoke_release_gate.py`.

## 1. Core runtime / persistence

| Variable | Default | Effect |
|---|---|---|
| `APP_RUNTIME_PROFILE` | `dev` | Профиль `dev|stage|prod`; в `prod` отключается fallback persistence. |
| `APP_DB_DSN` | - | DSN PostgreSQL для API/persistence adapters. |
| `APP_DB_SCHEMA` | `app` | SQL schema для Postgres adapters. |
| `APP_VECTOR_DIM` | `1536` | Размерность embeddings для vector path. |

## 2. Auth / RBAC

| Variable | Default | Effect |
|---|---|---|
| `APP_AUTH_ENABLED` | `false` | Включает role checks в API и MCP sensitive operations. |

При `APP_AUTH_ENABLED=true`:

- API использует `X-Actor-Id`, `X-Actor-Roles`.
- MCP write/sensitive tools ожидают `actor`, `roles` в payload.

## 3. Async execution plane

| Variable | Default | Effect |
|---|---|---|
| `APP_ASYNC_PROVIDER` | `inline` | Провайдер async execution: `inline|celery`. |
| `APP_CELERY_BROKER_URL` | `redis://127.0.0.1:56379/0` | Broker для celery worker. |
| `APP_CELERY_RESULT_BACKEND` | broker value | Result backend celery. |
| `APP_CELERY_QUEUE` | `authoring` | Очередь authoring tasks/HITL continuation. |
| `APP_CELERY_INDEXING_QUEUE` | `knowledge-indexing` | Очередь knowledge indexing tasks. |
| `APP_CELERY_RETRIEVAL_QUEUE` | `retrieval` | Очередь retrieval tasks. |
| `APP_WORKER_DB_DSN` | `postgresql://app:app@host.docker.internal:55432/langgraph` | DSN для worker в `docker-compose.async.yml` (compose-level override). |

## 4. LLM authoring

| Variable | Default | Effect |
|---|---|---|
| `APP_LLM_ENABLED` | `false` | Включает LLM draft path для authoring. |
| `APP_LLM_STRICT` | `false` | При `true` ошибки конфигурации LLM не фолбэчатся в deterministic mode. |
| `APP_LLM_PROVIDER` | `openrouter` | Провайдер (`openrouter`, `vllm_mock`, другое). |
| `OPENROUTER_API_KEY` | - | API ключ OpenRouter. |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Модель OpenRouter. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Base URL OpenRouter API. |
| `OPENROUTER_TIMEOUT_SEC` | `60` | Timeout OpenRouter HTTP calls. |
| `OPENROUTER_APP_NAME` | `langgraph-document-ai-platform` | App name header for OpenRouter. |
| `OPENROUTER_APP_URL` | `http://localhost` | App URL header for OpenRouter. |
| `VLLM_MODEL_NAME` | `mock-vllm-model` | Model name для `APP_LLM_PROVIDER=vllm_mock`. |

## 5. TEI embedding/rerank gateways

| Variable | Default | Effect |
|---|---|---|
| `TEI_BASE_URL` | empty | Базовый URL TEI; используется для derive `/embed` и `/rerank`. |
| `TEI_EMBEDDING_URL` | empty | Явный endpoint embeddings (приоритет над `TEI_BASE_URL`). |
| `TEI_RERANK_URL` | empty | Явный endpoint rerank (приоритет над `TEI_BASE_URL`). |
| `TEI_API_KEY` | empty | Optional API key для TEI HTTP requests. |
| `TEI_TIMEOUT_SEC` | `30` | Timeout TEI запросов. |
| `TEI_FALLBACK_ENABLED` | `false` | Разрешает deterministic fallback при ошибке TEI. |

## 6. OCR / parsing quality

| Variable | Default | Effect |
|---|---|---|
| `APP_OCR_ENABLED` | `true` | Включает OCR fallback path в parser. |
| `APP_OCR_PROVIDER` | `sidecar` | OCR provider (`sidecar` или `ocrmypdf`). |
| `APP_OCR_LANGUAGE` | `eng` | Язык OCRmyPDF (`-l` flag). |
| `APP_OCR_TIMEOUT_SEC` | `120` | Timeout OCRmyPDF subprocess. |

## 7. Knowledge indexing quality policy

| Variable | Default | Effect |
|---|---|---|
| `APP_INDEXING_QUALITY_POLICY_NAME` | `default_indexing_quality_policy_v1` | Имя policy в output summary. |
| `APP_INDEXING_QUALITY_BLOCKING_FLAGS` | empty | CSV quality flags, блокирующие accepted path. |
| `APP_INDEXING_QUALITY_WARNING_ONLY_FLAGS` | empty | CSV warning-only flags. |
| `APP_INDEXING_ALLOW_RECOVERED_OCR` | `true` | Разрешает accepted path после успешного OCR recover. |
| `APP_INDEXING_OCR_RECOVERY_BLOCKING_FLAG` | `pdf_no_extractable_text` | Флаг, считающийся blocking до recovery. |
| `APP_INDEXING_OCR_RECOVERY_SUCCESS_FLAG` | `ocr_applied` | Флаг успешного recovery. |
| `APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE` | `0` | Порог low-confidence для form-like PDF extraction. |
| `APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING` | `false` | Делает low form-confidence blocking. |
| `APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE` | `0` | Порог low-confidence OCR score. |
| `APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING` | `false` | Делает low OCR-confidence blocking. |

## 8. HITL limits and SLA aggregates

| Variable | Default | Effect |
|---|---|---|
| `APP_HITL_MAX_ITERATIONS` | `2` | Максимум итераций reviewer loop. |
| `APP_HITL_WAIT_TIMEOUT_SEC` | `1800` | Временное окно ожидания human decision. |
| `APP_SLA_TASK_DURATION_MS` | empty | SLA threshold для task duration (observability). |
| `APP_SLA_QUEUE_WAIT_MS` | empty | SLA threshold для queue wait (observability). |

Примечание: пустое/невалидное/`<=0` значение SLA-порогов отключает соответствующую проверку breach.

## 9. Release gate policy env

Источник: `backend/scripts/smoke_release_gate.py`.

| Variable | Default | Effect |
|---|---|---|
| `APP_RELEASE_GATE_PROFILE` | `dev` | Профиль gate policy (`dev|stage|prod`). |
| `APP_RELEASE_GATE_MIN_EVENTS_TOTAL` | profile value | Минимум событий для retrieval checks. |
| `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS` | profile value | Минимум total tasks в observability checks. |
| `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES` | profile value | Верхняя граница duration SLA breaches (`-1` disables). |
| `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES` | profile value | Верхняя граница queue wait breaches (`-1` disables). |
| `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS` | profile value | Требовать non-zero `llm_tokens_total` + `draft_generation_mode=llm`. |

## 10. Logging

| Variable | Default | Effect |
|---|---|---|
| `APP_LOG_LEVEL` | `INFO` | Уровень structured runtime logs (`infra.logging.runtime`). |

## 11. Recommended baseline profiles

- Local dev:
  - `APP_RUNTIME_PROFILE=dev`
  - `APP_ASYNC_PROVIDER=inline`
- Stage-like verification:
  - `APP_RUNTIME_PROFILE=stage`
  - `APP_ASYNC_PROVIDER=inline` или `celery`
- Prod-like rehearsal:
  - `APP_RUNTIME_PROFILE=prod`
  - `APP_AUTH_ENABLED=true`
  - `APP_ASYNC_PROVIDER=celery` (если проверяется очередной контур)

## 12. Связанные документы

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/mcp_reference.md`
- `docs/developer_guide/operations_and_release.md`
