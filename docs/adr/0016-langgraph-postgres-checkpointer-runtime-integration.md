# ADR-0016: Интеграция LangGraph PostgreSQL Checkpointer в Runtime

- Статус: Superseded by ADR-0017
- Дата: 2026-04-20

## Контекст

После `Increment 10` lifecycle задач, история и аудит статусов уже были персистентны, но сам `LangGraph` runtime не использовал production checkpointer API.

Фактически checkpoint payload сохранялся вручную через `TaskApplicationService`, что не покрывало нативный контракт `StateGraph.compile(checkpointer=...)` и требования к устойчивому runtime state.

## Решение

1. Добавить `PostgresLangGraphCheckpointer` (реализация `BaseCheckpointSaver`) в `infra.postgres.checkpoint_store`.
2. Использовать таблицу `app.checkpoints` как storage:
   - task payload остаётся в формате `run_id=<task_id>`;
   - LangGraph checkpoint namespace хранится в том же storage с префиксом `run_id=lg_thread:*`.
3. Расширить `LangGraphPostgresCheckpointStore` фабрикой `build_langgraph_checkpointer()`:
   - PostgreSQL saver при наличии DSN;
   - `InMemorySaver` в fallback режиме.
4. Подключить checkpointer в `BaseWorkflow`:
   - `builder.compile(checkpointer=...)`;
   - `graph.invoke(..., config={"configurable": {"thread_id": ...}})`.
5. Принять `task_context.task_id` как canonical source `thread_id`:
   - в `RetrievalApplicationService.start/resume` гарантировать наличие `task_id` в `task_context`;
   - при включенном checkpointer отсутствие `task_id` трактовать как ошибку конфигурации runtime.

## Последствия

Плюсы:

- LangGraph runtime использует нативный checkpoint lifecycle в PostgreSQL;
- `prod` контур работает без fallback и с единым persisted thread state;
- smoke/e2e сценарии подтверждают корректность `start/resume` и запись checkpoint namespace.

Минусы:

- на момент принятия решения checkpoint namespace и task payload разделялись только префиксом `run_id`;
- в `Increment 12` storage checkpointer вынесен в отдельные таблицы (см. ADR-0017).
