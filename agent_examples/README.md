# Agent Examples (Python)

Дата обновления: 2026-04-30

Это отдельная витрина Python-агентов на базе фреймворка.

Ключевая идея:

- `retrieval_first` уже показывает целевой стиль: in-process framework usage;
- `authoring_first` и `hitl_gate` пока в переходном API-driven режиме и будут replatform по roadmap.

## Структура

```text
agent_examples/
  run_example.py
  common/
  patterns/
    retrieval_first/
    authoring_first/
    hitl_gate/
```

## Быстрый запуск

## A) In-process pattern (без инфраструктуры)

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

или через общий раннер:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

## B) Transition patterns (API-driven до replatform)

Для `authoring_first` / `hitl_gate` пока нужен runtime:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

Для HITL async path:

```bash
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

## Dry-run

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

## Для тебя: как потестить быстро

1. Pattern tests для in-process retrieval:

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
```

2. Unit тесты общего раннера:

```bash
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
```

3. Контракт структуры examples:

```bash
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py
```

## Cleanup

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```
