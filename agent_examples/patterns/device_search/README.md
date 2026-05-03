# device_search — агент подбора техники

Принимает запрос на разговорном языке ("нужен планшет для чтения до 25 000 руб.")
и возвращает аналитический Markdown-отчёт: ранжирование устройств с оценками
по критериям, ссылками на источники и выдержками из реальных отзывов.

Бесплатный поиск через DuckDuckGo — API-ключ не нужен.
Требуется только `OPENROUTER_API_KEY` для LLM-вызовов.

---

## Архитектура

Три последовательных `BaseWorkflow` с двумя HITL-паузами между ними:

```
[Phase 1] DevicePlanningWorkflow
    parse_intent   — разбирает запрос: тип устройства, бюджет, цели
    map_criteria   — деcomposes цели в измеримые технические критерии

    ↓ HITL-1: показ критериев → подтвердить или скорректировать
               при корректировке Phase 1 перезапускается с уточнением

[Phase 2] DeviceResearchWorkflow
    search_listings    — ищет кандидатов через DuckDuckGo
    gather_evidence    — собирает бенчмарки и обзоры по каждому критерию
    enrich_reviews     — находит отзывы покупателей, маппит на критерии
    score_and_compare  — оценивает каждое устройство по каждому критерию

    ↓ HITL-2: показ ранжирования с числами → подтвердить или оставить комментарий

[Phase 3] DeviceReportWorkflow
    generate_report    — собирает Markdown-отчёт
```

Все три workflow разделяют один `DeviceSearchEventSink` —
единый таймлайн выполнения узлов накапливается в памяти и печатается в конце.

---

## Ключевые концепции

### Критерии с measurability

Каждый критерий получает метку `measurability`:

- `searchable` — можно проверить через поиск (ppi, RAM, ёмкость батареи).
  Для таких критериев агент реально ищет бенчмарки и обзоры.
- `inferred` — субъективно или не поддаётся прямой проверке
  (удобство держать в руках, дизайн, экосистема).
  Эти критерии участвуют в оценке и отчёте, но поисковые запросы по ним
  не делаются — на них нет объективных источников.

### Доказательная база

Каждая оценка (`CriterionScore`) содержит список `evidence`:
URL источника, заголовок, релевантный сниппет, тип
(`benchmark / expert_review / user_review`) и confidence.

При HITL-2 агент показывает не просто "экран плоховат",
а реальное измерение с порогом и ссылкой:

```
✗ Качество экрана: 4.2/10  [требуется: ppi >= 227, IPS да]
  → Разрешение 1280×800, 189 ppi — значительно ниже порога 227 ppi. TFT матрица.
  источник: https://gsmarena.com/lenovo_tab_m10-9616.php
```

### Трасса рассуждений

`DeviceSearchState.reasoning_trace` — список записей, одна на каждый узел:

```json
[
  { "node": "parse_intent", "device_type": "планшет", "budget_rub": 25000 },
  { "node": "map_criteria", "criteria": [...] },
  { "node": "search_listings",
    "queries_used": ["планшет ppi дисплей до 25000..."],
    "raw_results_count": 30,
    "will_score": ["Samsung Tab A9", "Xiaomi Pad 6"],
    "excluded_from_scoring": [{"name": "Teclast T30", "reason": "позиция > 4"}] },
  { "node": "gather_evidence",
    "criteria_skipped_inferred": ["Удобство в руке"],
    "evidence_items_total": 48 },
  { "node": "score_and_compare", "ranking": [...] }
]
```

Трасса попадает в итоговый JSON под ключом `reasoning_trace`.

---

## Структура файлов

```
device_search/
├── agent.py        # DeviceSearchAgent — оркестрация трёх фаз + два HITL-порога
├── workflow.py     # DevicePlanningWorkflow, DeviceResearchWorkflow, DeviceReportWorkflow
│                   # + _DeviceSearchHandlersMixin с семью обработчиками узлов
├── state.py        # Pydantic-контракты: DeviceSearchState, ConsumerCriterion,
│                   # CriterionScore, EvidenceItem, DeviceScore, HITLState
├── search_tools.py # DuckDuckGo-обёртки: листинги, бенчмарки, отзывы
├── prompts.py      # Шесть LLM-промптов (parse_intent → generate_report)
├── event_sink.py   # DeviceSearchEventSink — per-node тайминги, timeline
├── config.py       # DeviceSearchConfig — читает env vars
├── main.py         # Точка входа с CLI-флагами
└── sample_input/
    └── query.txt   # Дефолтный запрос для быстрого старта
```

---

## Запуск

### Быстрый старт

```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_MODEL="anthropic/claude-3-5-haiku"   # опционально

.venv/bin/python agent_examples/patterns/device_search/main.py \
  --query "Нужен планшет для чтения книг и браузинга, бюджет до 25000 рублей"
```

### Автоматический режим (без HITL-пауз)

```bash
.venv/bin/python agent_examples/patterns/device_search/main.py \
  --query "Нужен планшет для чтения" \
  --non-interactive
```

### Через общий раннер

```bash
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

---

## Разбор итогового JSON

Агент печатает результат в stdout. Ключевые поля:

| Поле | Что содержит |
|---|---|
| `reasoning_trace` | Полная трасса: что искал, что пропустил, почему |
| `ranking[i].criterion_scores[j].assessment` | Оценка с реальными числами |
| `ranking[i].criterion_scores[j].evidence` | Источники с URL и сниппетами |
| `ranking[i].review_insights` | Наблюдения из реальных отзывов |
| `node_timeline` | Тайминги каждого узла (мс) |
| `node_failures` | Узлы, упавшие с ошибкой |
| `unresolved_gaps` | Что не удалось найти или подтвердить |
| `confidence` | Средняя уверенность по доказательной базе (0–1) |
| `final_report` | Итоговый Markdown-отчёт |

Пример: посмотреть трассу из командной строки:

```bash
.venv/bin/python agent_examples/patterns/device_search/main.py \
  --query "..." --non-interactive \
  | python3 -c "
import sys, json
r = json.load(sys.stdin)
for step in r['reasoning_trace']:
    print(json.dumps(step, ensure_ascii=False, indent=2))
"
```

---

## Что менять в первую очередь

**Тип устройства** — просто меняй запрос (`--query "ноутбук для работы до 80 000 руб."`),
агент сам разберёт категорию и переведёт в английский для поиска.

**Качество поиска** — `search_tools.py::search_marketplace_listings`.
Сейчас таргетирует ixbt.com, 4pda, ichip, gsmarena. Добавь свои домены или
измени запросы под конкретный маркетплейс.

**Критерии** — `prompts.py::MAP_CRITERIA_PROMPT`. Если нужны специфические
технические параметры (например, для B2B закупок) — уточни промпт.

**Количество кандидатов** — `workflow.py::MAX_DEVICES_TO_SCORE` (сейчас 4).
Больше кандидатов → больше поисковых запросов → дольше выполнение.

**LLM-модель** — переменная `OPENROUTER_MODEL`. Более сильная модель
(claude-opus, gpt-4o) даёт точнее оценки, слабая (haiku, gemini-flash) —
быстрее и дешевле.
