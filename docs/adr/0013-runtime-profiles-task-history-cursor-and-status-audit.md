# ADR-0013: Runtime Profiles, Cursor Task History и аудит переходов статусов

- Статус: Accepted
- Дата: 2026-04-19

## Контекст

После `Increment 8` история задач уже хранилась в PostgreSQL (`app.tasks`), но оставались архитектурные пробелы:

- fallback persistence мог использоваться даже в production-контуре;
- `GET /api/v1/tasks` поддерживал только `limit/offset` без фильтров и курсоров;
- не было отдельного audit trail переходов статусов задач.

Для эксплуатации на Ubuntu-сервере нужен более строгий runtime-контур и удобная постраничная навигация по истории без `offset`-дрейфа.

## Решение

1. Ввести runtime profiles через `APP_RUNTIME_PROFILE`:
   - допустимые значения: `dev`, `stage`, `prod`;
   - fallback persistence разрешен только в `dev/stage`;
   - в `prod` отсутствие `APP_DB_DSN` приводит к ошибке и блокирует in-memory fallback.
2. Обновить контракт `GET /api/v1/tasks`:
   - фильтры `status`, `task_type`, `from`, `to`;
   - курсорная пагинация `cursor -> next_cursor` + флаг `has_more`;
   - сортировка: `updated_at DESC, task_id DESC`.
3. Добавить аудит переходов статуса:
   - SQL миграция `0003_task_events.sql`;
   - таблица `app.task_events`;
   - события пишутся при создании задачи и при каждой смене `status`.
4. Обновить smoke/tests:
   - unit/integration/e2e покрытие нового контракта;
   - smoke-скрипты переведены на фильтруемый history-запрос.

## Последствия

Плюсы:

- production-контур стал строже: без БД не запускается critical persistence;
- история задач масштабируется через cursor-пагинацию и меньше подвержена проблемам `offset`;
- появился audit trail жизненного цикла задач на уровне статусов.

Минусы:

- контракт `/api/v1/tasks` изменился (offset-пагинация больше не основной путь);
- audit-события пока сохраняются, но отдельный публичный endpoint чтения событий еще нужен в следующем инкременте.
