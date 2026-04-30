# Design Patterns Library

Дата обновления: 2026-04-30  
Статус: Active

Эта библиотека нужна, когда разработчик спрашивает:

- "какой шаблон выбрать под мой сценарий?"
- "какой минимальный рабочий скелет взять?"
- "как не сломать контракты framework при расширении?"

План replatform демо-агентов в in-process стиль:

- `docs/developer_guide/agent_examples_demo_program.md`

## Как пользоваться

1. Выбери pattern по задаче.
2. Запусти связанный runnable пример из `agent_examples/run_example.py`.
3. Повтори структуру extension points для своего кейса.
4. Проверь изменения через smoke/tests и обнови docs backlog.

## Каталог patterns

1. Retrieval-First Agent  
   Когда: нужен быстрый Q&A/evidence path по документам.  
   Док: `docs/developer_guide/design_patterns/pattern_retrieval_first.md`  
   Пример: `agent_examples/patterns/retrieval_first/main.py` (in-process).

2. Authoring-First Agent  
   Когда: нужен управляемый процесс генерации итогового артефакта.  
   Док: `docs/developer_guide/design_patterns/pattern_authoring_first.md`  
   Пример: `agent_examples/run_example.py --pattern authoring_first`

3. HITL Gate Pattern  
   Когда: нужен reviewer loop и безопасный approve/rework path.  
   Док: `docs/developer_guide/design_patterns/pattern_hitl_gate.md`  
   Пример: `agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve`

Примечание по текущему статусу:

- `retrieval_first` уже переведен в in-process pattern.
- `authoring_first` и `hitl_gate` пока остаются API-driven в рамках переходного этапа.

## Проверка

Быстрый test path:

```bash
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py
.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py
```
