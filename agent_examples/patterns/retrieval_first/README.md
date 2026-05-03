# retrieval_first — in-process поиск по документам

Минимальный агент, показывающий как собрать агента как Python-композицию
поверх framework contracts — без HTTP, без инфраструктуры, одним `invoke()`.

---

## Что делает

Принимает текстовый вопрос, прогоняет его через `RetrievalWorkflow` прямо
в памяти, возвращает `EvidencePack`: набор релевантных блоков документов
с источниками, confidence-заметками и списком неразрешённых пробелов.

```
Запрос
  → RetrievalWorkflow.invoke()
      → EvidencePack
          selected_blocks    — блоки документов
          selected_sources   — источники (doc_id, version, block_id)
          confidence_notes   — объяснения уверенности
          unresolved_gaps    — что не нашли
```

---

## Архитектурный смысл

Это паттерн **in-process**: агент импортирует фреймворк как библиотеку
и вызывает `workflow.invoke()` напрямую. Нет сетевых задержек,
нет необходимости поднимать бэкенд, вся трасса видна в Python-объектах.

Это целевая модель для новых агентов — в противовес API-driven паттернам
(`authoring_first`, `hitl_gate`), которые общаются с фреймворком через HTTP.

---

## Структура файлов

```
retrieval_first/
├── agent.py    # RetrievalFirstAgent — вызывает workflow и формирует ответ
├── workflow.py # run_retrieval_workflow() — тонкая обёртка над RetrievalWorkflow
├── tools.py    # build_default_filters() — фильтры документов для поиска
├── config.py   # RetrievalFirstConfig — case_dataset_id, requester
├── prompts.py  # DEFAULT_QUERY — дефолтный вопрос
├── main.py     # точка входа
└── tests/      # unit + smoke тесты
```

---

## Запуск

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

Через общий раннер:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

Dry-run (проверить без реальных вызовов):

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

---

## Тесты

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
```

---

## Что менять в первую очередь

1. `prompts.py` — изменить вопрос (`DEFAULT_QUERY`).
2. `tools.py` — изменить `document_types` и фильтры поиска.
3. `config.py` — переключить `case_dataset_id` или `requester`.
