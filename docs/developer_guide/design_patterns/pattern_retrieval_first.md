# Pattern: Retrieval-First Agent

Когда применять:

- нужен быстрый путь "вопрос -> доказательная выборка";
- итоговый output - evidence pack, а не длинный authored artifact;
- важна объяснимость источников и traceability к knowledge blocks.

## Скелет

`ingest/index -> retrieval/start -> evidence -> optional resume`

## Runnable пример

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example retrieval_faq_assistant --execute
```

## Extension points

1. Сменить retrieval query/profile через args и filters.
2. Подключить свой case dataset (`--extra-arg --case-dataset-id ...`).
3. Добавить post-processing для evidence в application layer.

## Анти-паттерны

1. Делать heavy authoring в retrieval path.
2. Обходить typed contracts из `schemas`.
3. Игнорировать task events и observability после расширения.
