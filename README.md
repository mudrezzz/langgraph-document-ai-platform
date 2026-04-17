# LangGraph Document AI Platform

Этот репозиторий реализует внутренний framework-слой и прикладные сервисы системы документных AI-агентов на базе LangGraph.

## Источник требований

Базовые требования и целевая архитектура описаны в:

- `docs/тз_на_систему_документных_ai_агентов_на_lang_graph.md`
- `docs/blueprint_oop_слой_и_архитектура_системы_на_lang_graph.md`

## Статус

Текущий инкремент: `Increment 4`.

Сделано:

- создан и расширен каркас `backend`;
- реализованы framework contracts и базовые реализации;
- добавлены concrete adapter skeleton в `infra/*`;
- реализован `RetrievalPackWorkflow` как первый рабочий вертикальный срез;
- добавлен API boundary (`apps/api`) с typed retrieval endpoints;
- добавлены application services для task lifecycle, checkpoint и resume;
- добавлены интеграционные тесты на каждый endpoint;
- добавлен smoke-runner script для локального HTTP прогона endpoint-ов.

## Структура

```text
backend/
  apps/
    api/
  packages/
    framework/
    schemas/
    infra/
    domain_rag/
    application/
  scripts/
  tests/
docs/
  adr/
  architecture/
```

## Обязательные документы сопровождения

После каждого инкремента обновляются три документа:

1. `README.md` — текущее состояние, структура, правила работы.
2. `docs/adr/*.md` — принятые архитектурные решения.
3. `docs/architecture/System_Architecture_Overview.md` — актуальный снимок архитектуры и GAP к целевой модели.

## Правила кодовой базы

- комментарии в коде пишутся на русском языке;
- интерфейсы и контракты задаются типизированно;
- бизнес-логика не прячется в интеграционных glue-скриптах;
- LangGraph остается runtime для оркестрации;
- framework-слой должен быть компактным и прозрачным.

## Запуск тестов

```bash
python -m pytest backend/tests -q
```

## Smoke запуск API

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\smoke_retrieval_api.ps1
```

## Дальнейший фокус

Следующий инкремент: интеграция `BaseWorkflow` с реальным LangGraph runtime, плюс перевод ключевых in-memory adapters на PostgreSQL/pgvector-backed реализации.