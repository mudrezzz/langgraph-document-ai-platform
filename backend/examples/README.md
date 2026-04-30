# Framework Examples Catalog

Дата обновления: 2026-04-30  
Статус: Active quickstart gallery

Этот каталог показывает минимальные runnable кейсы, чтобы разработчик мог за 5-15 минут увидеть:

- как быстро поднять полезный agent flow;
- как выглядят working path и ожидаемый результат;
- как перейти от примера к расширению под свой use case.

## Быстрый старт (Linux)

1. Поднять PostgreSQL и применить миграции:

```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
```

2. Посмотреть список примеров:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --list
```

3. Запустить любой пример:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example retrieval_faq_assistant --execute
```

## Примеры

1. `retrieval_faq_assistant`  
   Pattern: `Retrieval-First Agent`  
   Что показывает: быстрый retrieval path с evidence pack.

2. `authoring_policy_brief`  
   Pattern: `Authoring-First Agent`  
   Что показывает: authoring flow с multi-step режимом и traceability.

3. `hitl_review_loop`  
   Pattern: `HITL Gate Pattern`  
   Что показывает: async authoring + итеративный review (`needs_changes -> approve`).  
   Перед запуском нужно поднять async plane:

```bash
bash backend/scripts/async_up.sh
```

## Режим dry-run (без запуска)

Чтобы проверить итоговую команду без выполнения:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example authoring_policy_brief
```

`dry-run` полезен, когда нужно:

- посмотреть параметры запуска;
- добавить свои args через `--extra-arg`;
- встроить запуск в CI/локальный script.

Пример:

```bash
.venv/bin/python backend/examples/quickstart_agents.py \
  --example retrieval_faq_assistant \
  --extra-arg --port \
  --extra-arg 8210
```

## Как протестировать примеры (для тебя)

1. Быстрые unit-тесты каталога примеров:

```bash
.venv/bin/pytest -q backend/tests/unit/test_example_quickstart_agents.py
```

2. Контрактные docs-тесты (проверяют ссылки на examples/patterns):

```bash
.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py
```

3. Реальный smoke path одного примера:

```bash
.venv/bin/python backend/examples/quickstart_agents.py --example retrieval_faq_assistant --execute
```

## Cleanup

После прогона:

```bash
bash backend/scripts/async_down.sh
bash backend/scripts/postgres_down.sh --remove-volumes
```
