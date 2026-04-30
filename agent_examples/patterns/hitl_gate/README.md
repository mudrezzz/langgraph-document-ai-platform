# Pattern Example: HITL Gate

Что показывает:

- как Python-агент работает с `start_async` и `hitl/submit`;
- как выглядит цикл `needs_changes -> approve`.

Основной код:

- `agent.py` - агент и polling loop
- `config.py` - конфиг HITL запуска
- `prompts.py` - стартовый prompt

Запуск из корня репозитория:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```
