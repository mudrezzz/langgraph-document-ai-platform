# ADR-0025: Multi-step authoring workflow и section-level traceability

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 19` authoring уже умел генерировать "живой" draft через OpenRouter, но процесс оставался single-pass.

Не хватало:

- явного шага research перед writer;
- reviewer этапа с формализованным статусом/рекомендацией;
- прозрачного read-model по шагам выполнения;
- traceability на уровне секций итогового артефакта.

## Решение

1. Расширить `AuthoringApplicationService` до multi-step pipeline:
   - `research -> writer -> reviewer -> assembly`.
2. Добавить `workflow_mode` в API контракт `POST /api/v1/tasks/authoring/start`:
   - `single_pass` (обратная совместимость);
   - `multi_step` (новый режим по умолчанию).
3. Сохранять шаги выполнения в task details и artifact metadata:
   - `steps_summary`;
   - `current_step`, `review_status`, `final_recommendation`.
4. Расширить traceability-контракт артефакта:
   - `traceability.sections[]` с `section_id`, `title`, `review_status`, `source_refs`.
5. Сохранить существующую LLM политику:
   - writer шаг может использовать LLM (`draft_strategy=llm|auto`);
   - при ошибке gateway разрешен fallback в deterministic режим (если strict выключен).

## Последствия

Плюсы:

- авторинг стал более объяснимым и проверяемым (видно шаги и reviewer verdict);
- расширился API read-model для ручного smoke и аудит-трассировки;
- section-level traceability делает artifact более пригодным для проверки источников.

Минусы:

- pipeline остается синхронным (без очередей и async retries);
- reviewer пока rule-based, без HITL/revision-loop;
- section mapping пока эвристический.
