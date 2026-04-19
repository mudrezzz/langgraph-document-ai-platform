# Ubuntu 24 First Bootstrap Checklist

- Дата: 2026-04-19
- Репозиторий: `https://github.com/mudrezzz/langgraph-document-ai-platform`
- Ветка: `main`

## 1. Быстрый чеклист команд (10 шагов)

```bash
# 1) Базовые пакеты
sudo apt update && sudo apt install -y git curl python3 python3-venv python3-pip ca-certificates gnupg

# 2) Клонируем репозиторий
git clone https://github.com/mudrezzz/langgraph-document-ai-platform.git

# 3) Переходим в проект
cd langgraph-document-ai-platform

# 4) Создаем venv
python3 -m venv .venv

# 5) Активируем venv
source .venv/bin/activate

# 6) Ставим минимальные зависимости для запуска/тестов
python -m pip install -U pip
python -m pip install fastapi uvicorn pydantic psycopg[binary] pytest

# 7) Готовим env-файл backend
cp backend/.env.example backend/.env

# 8) Поднимаем PostgreSQL + pgvector
bash backend/scripts/postgres_up.sh

# 9) Накатываем миграции и делаем smoke
bash backend/scripts/postgres_migrate.sh
APP_DB_DSN=postgresql://app:app@localhost:55432/langgraph APP_DB_SCHEMA=app \
  bash backend/scripts/smoke_retrieval_api.sh --port 8010

# 10) Прогоняем тесты и чистим postgres
python -m pytest backend/tests -q
bash backend/scripts/postgres_down.sh --remove-volumes
```

## 2. Что считать успешным запуском

- в smoke JSON:
  - `start_status=completed`
  - `task_status=completed`
  - `evidence_blocks >= 1`
  - `history_contains_task=true`
- тесты проходят:
  - минимум `unit/integration` должны быть зеленые;
  - postgres e2e могут быть `skipped`, если docker daemon недоступен.

## 3. Стартовый промпт для Codex-чата на Linux сервере

```text
Работаем в репозитории https://github.com/mudrezzz/langgraph-document-ai-platform, ветка main.
Контекст: реализованы retrieval API, LangGraph runtime, PostgreSQL+pgvector persistence, persistent task registry и endpoint истории задач.
Проект перенесен на Ubuntu 24; в backend/scripts уже есть bash-скрипты для postgres/migrations/smoke/demo.

Нужно продолжить следующую итерацию:
1) ввести runtime profiles dev/stage/prod и отключить fallback persistence в prod;
2) расширить GET /api/v1/tasks фильтрами (status, task_type, from/to) и курсорной пагинацией;
3) добавить task_events для аудита переходов статусов;
4) обновить README, ADR и System Architecture Overview;
5) добавить/обновить unit/integration/e2e тесты и прогнать smoke.

Требования:
- комментарии в коде на русском;
- после каждого инкремента обновлять README, docs/adr/* и docs/architecture/System_Architecture_Overview.md.
```
