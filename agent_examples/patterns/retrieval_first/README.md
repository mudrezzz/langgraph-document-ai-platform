# Pattern Example: Retrieval First (In-Process)

Что показывает:

- как собрать агента как Python-композицию поверх framework contracts;
- как запустить retrieval workflow напрямую (`invoke`), без HTTP transport.

## Структура pattern

- `agent.py` - orchestration уровня агента
- `workflow.py` - in-process вызов retrieval workflow
- `tools.py` - базовые retrieval filters для старта
- `config.py` - конфигурация demo-кейса
- `main.py` - запуск одной командой
- `tests/` - unit + smoke проверки
- `expected_output/` - пример ожидаемого результата

## Быстрый запуск

Из корня репозитория:

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

Альтернатива через общий раннер:

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

## Что модифицировать первым делом

1. `prompts.py` - изменить бизнес-вопрос.
2. `tools.py` - изменить `document_types`/filters.
3. `config.py` - переключить dataset/requester.

## Тесты

```bash
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py
```
