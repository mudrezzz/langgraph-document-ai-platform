# ADR-0014: Task Events API и стабилизация demo/smoke runbook

- Статус: Accepted
- Дата: 2026-04-19

## Контекст

После внедрения `task_events` в БД (`app.task_events`) аудит переходов статусов был доступен только на уровне SQL. Для операционной диагностики нужен стандартный API-контур с пагинацией и фильтрами.

Дополнительно Linux demo-скрипт имел нестабильный парсинг JSON результата smoke-прогона, что мешало ручной валидации reference-case на сервере.

## Решение

1. Добавить endpoint `GET /api/v1/tasks/events`:
   - фильтры: `task_id`, `task_type`, `from`, `to`;
   - курсорная пагинация: `cursor`, `next_cursor`, `has_more`;
   - сортировка: `created_at DESC, event_id DESC`.
2. Расширить application/registry контракт:
   - отдельная page-модель для task events;
   - cursor encode/decode для audit-событий.
3. Обновить smoke/demo:
   - smoke возвращает `events_returned` и `events_has_running_to_completed`;
   - Linux demo использует безопасный парсинг JSON через переменную окружения.
4. Обновить тесты:
   - unit/integration/e2e на новый endpoint и курсоры task events.

## Последствия

Плюсы:

- аудит lifecycle теперь доступен через публичный API;
- оператор может диагностировать transition flow без прямого доступа к SQL;
- ручной demo/smoke цикл на Linux стал стабильнее и информативнее.

Минусы:

- увеличился объем контрактов API и тестов поддержки;
- для полного observability все еще нужны агрегированные метрики поверх raw task events.
