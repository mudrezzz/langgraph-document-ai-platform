# Agent Examples (Python)

Дата обновления: 2026-04-30

Это отдельная витрина примеров агентов на базе фреймворка.

Цель:

- открыть одну папку;
- увидеть понятный Python-код агентов с комментариями;
- запустить за пару команд;
- взять шаблон и быстро сделать своего агента.

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

1. Поднять инфраструктуру:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

2. Запустить пример retrieval агента:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

3. Запустить пример authoring агента:

```bash
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

4. Запустить пример HITL агента:

```bash
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

## Dry-run (без вызова API)

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

## Для тебя: как потестить быстро

1. Контракт структуры примеров:

```bash
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py
```

2. Unit тесты раннера:

```bash
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
```

3. Smoke dry-run всех patterns:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
.venv/bin/python agent_examples/run_example.py --pattern authoring_first --dry-run
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --dry-run
```

## Cleanup

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```
