# Agent Examples

Каталог Python-агентов, демонстрирующих разные способы работы с фреймворком.
Каждый пример — самодостаточный паттерн: своя папка, свой `agent.py`, свой README.

---

## Каталог паттернов

| Паттерн | Что показывает | Модель исполнения | Инфраструктура |
|---|---|---|---|
| [`retrieval_first`](#retrieval_first) | Поиск по документам + EvidencePack | In-process (прямой вызов workflow) | Не нужна |
| [`authoring_first`](#authoring_first) | Создание артефакта через API | API-driven (HTTP → фреймворк) | PostgreSQL |
| [`hitl_gate`](#hitl_gate) | Асинхронный цикл ревью с HITL | API-driven async + polling | PostgreSQL + async worker |
| [`device_search`](#device_search) | Поиск товаров по запросу на разговорном языке | In-process, три фазы, два HITL | Не нужна |

---

## Архитектурный контекст

Паттерны разделены на два класса по модели исполнения:

**In-process** — агент импортирует фреймворк как библиотеку и вызывает
`workflow.invoke()` напрямую внутри одного Python-процесса. Не нужен HTTP,
нет сетевых задержек, трасса выполнения полностью видна в памяти.
Это целевая модель для новых агентов.

**API-driven** — агент общается с развёрнутым бэкендом через HTTP (`/start`,
`/task/{id}`, `/hitl/submit`). Нужна PostgreSQL и, для async-пути, воркер.
`authoring_first` и `hitl_gate` пока в этом режиме, запланирован replatform.

---

## Паттерны

### retrieval_first

Минимальный агент поиска по документарному корпусу. Принимает текстовый
запрос, прогоняет его через `RetrievalWorkflow` (in-process), возвращает
`EvidencePack` — найденные блоки документов с источниками и confidence.

Показывает: как собрать агента как Python-композицию поверх framework
contracts без единого HTTP-вызова.

```
Запрос → RetrievalWorkflow.invoke() → EvidencePack (блоки, источники, gaps)
```

**Запуск:**
```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

[Подробный README →](patterns/retrieval_first/README.md)

---

### authoring_first

Агент создания артефакта: задаёт вопрос API фреймворка, дожидается
синхронного ответа, возвращает готовый артефакт с traceability-секциями.

Показывает: как работает `/authoring/start` → `/task/{id}` → `/artifact/{id}`
цикл; как получить итоговый документ с полной трассируемостью.

```
Запрос → POST /authoring/start → GET /task/{id} → GET /artifact/{id} → Артефакт
```

**Запуск:**
```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

[Подробный README →](patterns/authoring_first/README.md)

---

### hitl_gate

Агент с асинхронным циклом ревью. Запускает задачу через `start_async`,
поллит статус, при `waiting_human` подаёт решение ревьюера (`needs_changes`
или `approve`), повторяет до завершения.

Показывает: как встроить reviewer-in-the-loop в агент; как управлять
идемпотентными HITL-решениями через API.

```
start_async → poll(waiting_human) → submit_hitl_review → poll → … → completed
```

**Запуск:**
```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

[Подробный README →](patterns/hitl_gate/README.md)

---

### device_search

Агент поиска и подбора техники по запросу на разговорном языке. Берёт запрос
вида "нужен планшет для чтения до 25 000 руб." и возвращает Markdown-отчёт
с ранжированием устройств, оценками по критериям и ссылками на источники.

Показывает: трёхфазную оркестрацию на `BaseWorkflow`; два интерактивных
HITL-порога; доказательную базу (каждая оценка подкреплена реальными URL);
`WorkflowNodeEventSink` для потайминга узлов.

```
parse_intent → map_criteria
    ↓ HITL-1: согласование критериев
search_listings → gather_evidence → enrich_reviews → score_and_compare
    ↓ HITL-2: согласование результатов
generate_report
```

**Запуск (интерактивный):**
```bash
export OPENROUTER_API_KEY="sk-or-..."
.venv/bin/python agent_examples/patterns/device_search/main.py \
  --query "Нужен планшет для чтения книг, бюджет до 25000 рублей"
```

**Запуск (автоматический, без пауз):**
```bash
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

[Подробный README →](patterns/device_search/README.md)

---

## Общий раннер

Все паттерны можно запустить через единый раннер:

```bash
.venv/bin/python agent_examples/run_example.py --pattern <имя>
```

Доступные имена: `retrieval_first`, `authoring_first`, `hitl_gate`, `device_search`.

Dry-run (без реальных вызовов LLM/API):
```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

---

## Тесты

```bash
# Unit + smoke — retrieval_first
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py

# Контракт структуры всех паттернов
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py

# Общий раннер
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
```

---

## Структура

```
agent_examples/
├── run_example.py           # общий раннер
├── common/                  # FrameworkClient, shared utilities
└── patterns/
    ├── retrieval_first/     # in-process document retrieval
    ├── authoring_first/     # API-driven artifact authoring
    ├── hitl_gate/           # async HITL review loop
    └── device_search/       # in-process marketplace search
```
