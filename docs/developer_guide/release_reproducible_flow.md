# Release Reproducible Flow

Дата обновления: 2026-04-30  
Статус: Active (P0 ops flow)

Цель: один повторяемый путь проверки релизной готовности через `smoke_release_gate` и `release_decision_gate`.

## 1. Preconditions

- Репозиторий: `/root/langgraph-document-ai-platform`
- Python venv + зависимости:

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

Если нужен async/celery rehearsal:

```bash
bash backend/scripts/async_up.sh
```

## 3. Gate profile selection

Базовые профили:

- `dev`: мягкие проверки.
- `stage`: рабочий pre-release baseline.
- `prod`: strict SLA profile.

Рекомендуемый baseline для репетиции релиза:

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

Критерий pass:

- `gate_status=pass`
- `failed_checks=[]`
- checks содержат валидные RG-коды (`RG001..RG012`, в зависимости от профиля/LLM требований)

## 5. Step B: final release decision

```bash
APP_RUNTIME_PROFILE=prod \
APP_DB_DSN=postgresql://app:app@127.0.0.1:55432/langgraph \
APP_DB_SCHEMA=app \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/release_decision_gate.sh --host 127.0.0.1 --port 8090 --gate-profile stage
```

Скрипт выполняет:

1. `smoke_release_gate`
2. full pytest gate
3. запись итогового verdict артефакта

Выходные артефакты:

- `backend/.release_gate/release_decision_*.json`
- `backend/.release_gate/release_decision_*.md`

## 6. Optional strict LLM token gate

Используйте, если release policy требует доказательства реального LLM path:

```bash
OPENROUTER_API_KEY="$(awk -F= '/^OPENROUTER_API_KEY=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_MODEL="$(awk -F= '/^OPENROUTER_MODEL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
OPENROUTER_BASE_URL="$(awk -F= '/^OPENROUTER_BASE_URL=/{print substr($0, index($0,"=")+1)}' backend/.env)" \
APP_LLM_ENABLED=true APP_LLM_PROVIDER=openrouter APP_LLM_STRICT=true APP_RELEASE_GATE_REQUIRE_LLM_TOKENS=1 \
PATH="$(pwd)/.venv/bin:$PATH" \
bash backend/scripts/smoke_release_gate.sh --host 127.0.0.1 --port 8088 --gate-profile prod --draft-strategy llm --require-llm-tokens
```

## 7. Triage if gate fails

Минимальный порядок triage:

1. Проверить `failed_checks` и их `code` (`RG...`) в JSON verdict.
2. Проверить `artifacts.observability_summary`.
3. Проверить `artifacts.retrieval_events_summary`.
4. Проверить `artifacts.authoring.status_payload.details`.
5. Повторить gate с тем же профилем после фикса.

## 8. Shutdown

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```

Если async не поднимался, первый шаг можно пропустить.
