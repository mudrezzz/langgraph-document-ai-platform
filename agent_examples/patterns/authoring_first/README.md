# authoring_first — создание артефакта через API

Агент, демонстрирующий API-driven путь: запускает задачу через HTTP-эндпоинт,
дожидается результата и возвращает готовый артефакт с traceability-секциями.

---

## Что делает

Отправляет запрос на создание документа через `POST /authoring/start`,
синхронно дожидается завершения задачи и возвращает артефакт — структурированный
документ с разделами traceability (откуда взяты данные).

```
Запрос
  → POST /authoring/start  → task_id
  → GET  /task/{task_id}   → статус (polling до completed)
  → GET  /artifact/{id}    → артефакт + traceability
```

---

## Архитектурный смысл

Это паттерн **API-driven**: агент общается с развёрнутым бэкендом через HTTP.
Полезно, когда агент работает в отдельном процессе или на другой машине,
и не может напрямую импортировать фреймворк.

Обратная сторона — нужна инфраструктура (PostgreSQL), есть сетевые задержки,
трасса видна только через API. Для новых агентов рекомендуется in-process
паттерн (`retrieval_first`, `device_search`).

---

## Структура файлов

```
authoring_first/
├── agent.py    # AuthoringFirstAgent — start → poll → get artifact
├── config.py   # AuthoringFirstConfig — workflow_mode, draft_strategy, dataset
└── prompts.py  # DEFAULT_QUERY — дефолтный вопрос
```

---

## Запуск

Требуется запущенный PostgreSQL с применёнными миграциями:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

---

## Что менять в первую очередь

1. `prompts.py` — изменить запрос (`DEFAULT_QUERY`).
2. `config.py` — переключить `workflow_mode` (`standard` / `deep`) или `draft_strategy`.
3. `agent.py` — добавить post-processing артефакта под свои нужды.
