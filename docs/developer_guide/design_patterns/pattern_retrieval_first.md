# Pattern: Retrieval-First Agent

Когда применять:

- нужен быстрый путь "вопрос -> доказательная выборка";
- итоговый output - evidence pack, а не длинный authored artifact;
- важна объяснимость источников и traceability к knowledge blocks.

## Скелет

`build workflow -> invoke(state) -> evidence pack`

## Runnable пример

```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

или

```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```

## Extension points

1. Сменить retrieval query через `prompts.py` или `main.py --query`.
2. Подключить свой case dataset через `main.py --dataset-id`.
3. Изменить фильтры в `agent_examples/patterns/retrieval_first/tools.py`.

## Анти-паттерны

1. Делать heavy authoring в retrieval path.
2. Обходить typed contracts из `schemas`.
3. Игнорировать task events и observability после расширения.
