# hitl_gate — асинхронный цикл ревью с HITL

Агент, демонстрирующий reviewer-in-the-loop через async API: запускает задачу,
поллит статус, при `waiting_human` подаёт решение ревьюера и повторяет цикл.

---

## Что делает

Запускает создание артефакта через `start_async`, ждёт пока задача не попросит
человеческого ревью (`waiting_human`), подаёт решение (`needs_changes` или
`approve`) и повторяет до финального `completed`.

```
POST /authoring/start_async → task_id
  → poll: waiting_human?
      → GET /hitl/{task_id}/status   — текущая итерация
      → POST /hitl/{task_id}/submit  — решение: needs_changes / approve
  → poll снова...
  → completed → GET /artifact/{id}
```

Каждое HITL-решение идемпотентно: агент передаёт `idempotency_key`,
чтобы повторная отправка не создавала дублей.

---

## Архитектурный смысл

Показывает механику HITL на уровне API-протокола — как задача переходит между
состояниями `running → waiting_human → running → completed`, как агент
программно играет роль ревьюера.

В реальном сценарии решение (`needs_changes` / `approve`) принимает человек
через UI; в примере оно передаётся через `--hitl-decisions` для автоматизации.

---

## Структура файлов

```
hitl_gate/
├── agent.py    # HitlGateAgent — async цикл с polling + HITL submissions
├── config.py   # HitlGateConfig — hitl_required, workflow params
└── prompts.py  # DEFAULT_QUERY — дефолтный запрос
```

---

## Запуск

Требуется PostgreSQL, миграции и async-воркер:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh

.venv/bin/python agent_examples/run_example.py \
  --pattern hitl_gate \
  --hitl-decisions needs_changes,approve
```

Остановить инфраструктуру после запуска:

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```

---

## Параметр `--hitl-decisions`

Список решений для последовательного применения через запятую.
Агент расходует их по одному на каждый `waiting_human`.

Примеры:
- `approve` — одно одобрение, если задача ждёт один раз
- `needs_changes,approve` — сначала отклонить, потом одобрить
- `needs_changes,needs_changes,approve` — два отклонения, потом одобрение

---

## Что менять в первую очередь

1. `prompts.py` — изменить запрос.
2. `config.py` — изменить `hitl_required` или `workflow_mode`.
3. `agent.py::run()` — заменить `decisions` из параметра на реальный UI-ввод.
