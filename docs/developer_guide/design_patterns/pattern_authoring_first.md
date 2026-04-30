# Pattern: Authoring-First Agent

Когда применять:

- нужно генерировать финальный артефакт (`report`, `brief`, `decision memo`);
- важны structured traceability и управляемый multi-step pipeline;
- есть правила формата/качества финального текста.

## Скелет

`retrieval -> draft -> reviewer (internal) -> assembly -> artifact`

## Runnable пример

```bash
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

## Extension points

1. Настроить `workflow_mode` (`single_pass|multi_step`).
2. Добавить/изменить шаблон artifact section structure.
3. Подключить LLM-провайдер через env contract при необходимости.

## Анти-паттерны

1. Генерировать artifact без source traceability.
2. Смешивать orchestration c transport-слоем API endpoint.
3. Ломать backward compatibility authoring payload contracts.
