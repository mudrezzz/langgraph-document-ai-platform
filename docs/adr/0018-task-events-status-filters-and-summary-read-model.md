# ADR-0018: Расширенные Фильтры Task Events и Summary Read-Model

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 12` API уже отдавал сырой audit stream переходов статусов через `GET /api/v1/tasks/events`, но для эксплуатационного анализа не хватало:

- фильтрации по направлению перехода (`from_status`, `to_status`);
- компактной агрегированной сводки без клиентского пост-агрегирования.

Для ручной диагностики на Ubuntu-сервере важно быстро отвечать на вопросы вида:

- сколько было переходов `running -> completed`;
- сколько задач попало в данный тип переходов за выбранный интервал.

## Решение

1. Расширить `GET /api/v1/tasks/events` фильтрами:
   - `from_status`;
   - `to_status`.
2. Добавить новый endpoint `GET /api/v1/tasks/events/summary`:
   - поддерживает фильтры `task_id`, `task_type`, `from_status`, `to_status`, `from`, `to`;
   - возвращает `total_events`, `unique_tasks` и агрегаты переходов `from_status -> to_status`.
3. Добавить индексы для статусов в `task_events`:
   - миграция `0005_task_events_status_filter_indexes.sql`.
4. Обновить smoke/demo scripts:
   - smoke JSON включает поля `events_summary_total`, `events_summary_unique_tasks`, `events_summary_has_running_to_completed`.

## Последствия

Плюсы:

- API аудит-слоя стал пригоден для операционной аналитики без тяжелой постобработки;
- smoke/runbook покрывают не только raw events, но и агрегированные проверки.

Минусы:

- summary endpoint пока строит агрегаты on-the-fly (нет materialized таблиц/дашбордов);
- для больших объемов потребуется отдельный read-model и периодические precompute job.
