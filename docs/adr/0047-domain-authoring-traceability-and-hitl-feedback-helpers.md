# ADR-0047: Domain authoring traceability and HITL feedback helper extraction

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0046 в `AuthoringApplicationService` оставались небольшие, но все еще доменные stateless helpers:

- преобразование section traceability в `SourceRef` и обратно;
- обновление `review_status` по секциям;
- форматирование human feedback для HITL rewrite.

Хотя эти методы не управляли lifecycle use case, они продолжали удерживать domain formatting/mapping logic в application layer.

## Решение

1. Перенести source-ref/traceability mapping в `OutlinePlanner`.
2. Использовать `SectionReviewService` как место для массового обновления section review status.
3. Добавить в `WriterDraftService` метод `apply_human_feedback(...)` для deterministic formatting reviewer feedback.
4. Сохранить orchestration HITL iteration, task state transitions и artifact persistence в `AuthoringApplicationService`.

## Последствия

Плюсы:

- application layer еще ближе к чистой orchestration boundary;
- traceability и rewrite formatting тестируются как domain behavior;
- следующий slice можно направить на section packets/workflows, не возвращаясь к helper-логике.

Минусы:

- `AuthoringApplicationService` все еще управляет большим use-case lifecycle;
- полноценные section contracts и template compilation пока не выделены.
