# ADR-0017: Выделенный Storage для LangGraph Checkpoint Runtime

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

В `Increment 11` production checkpointer был подключен к runtime, но его данные хранились в общей таблице `app.checkpoints` вместе с task payload (`run_id=<task_id>`).

Такой подход создавал риски:

- конкуренция за одну таблицу между API lifecycle payload и runtime checkpointing;
- усложнение операционных запросов и диагностики;
- отсутствие явной схемы для cleanup/retention политики.

## Решение

1. Вынести LangGraph checkpoint storage в отдельные таблицы:
   - `app.langgraph_checkpoints`;
   - `app.langgraph_checkpoint_blobs`;
   - `app.langgraph_checkpoint_writes`.
2. Добавить миграцию `0004_langgraph_checkpoint_storage.sql`.
3. Перевести `PostgresLangGraphCheckpointer` на работу с новыми таблицами.
4. Сохранить существующий `app.checkpoints` для task payload (совместимость API lifecycle не ломается).
5. Реализовать cleanup hooks в checkpointer:
   - `prune(strategy="keep_latest" | "delete")`;
   - `delete_thread`, `copy_thread`.

## Последствия

Плюсы:

- runtime checkpointing изолирован от task payload storage;
- проще операционный аудит состояния checkpointer;
- есть базовая политика очистки старых checkpoint-версий.

Минусы:

- добавлены дополнительные таблицы и миграция;
- `prune` пока вызывается только вручную (нет автоматического scheduler-процесса).
