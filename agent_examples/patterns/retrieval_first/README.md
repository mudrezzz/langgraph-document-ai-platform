# Pattern Example: Retrieval First

Что показывает:

- как выглядит минимальный Python-агент поверх framework API;
- как получить evidence pack за один вызов `agent.run(...)`.

Основной код:

- `agent.py` - агент
- `config.py` - конфиг кейса
- `prompts.py` - стартовый prompt

Запуск из корня репозитория:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first
```
