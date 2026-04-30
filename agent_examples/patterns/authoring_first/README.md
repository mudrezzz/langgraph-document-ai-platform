# Pattern Example: Authoring First

Что показывает:

- как написать Python-агента, который строит итоговый артефакт;
- как получить artifact и traceability в наглядном виде.

Основной код:

- `agent.py` - агент
- `config.py` - конфиг workflow/draft
- `prompts.py` - стартовый prompt

Запуск из корня репозитория:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```
