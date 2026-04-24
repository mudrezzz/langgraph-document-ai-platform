# ADR-0045: Minimal domain_authoring service extraction

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После закрытия `Increment 27` authoring path уже поддерживал sync/async execution, HITL, artifact traceability и LLM fallback, но большая часть authoring domain logic оставалась внутри `AuthoringApplicationService`.

Для `Increment 28` нужен постепенный переход к отдельному `domain_authoring` пакету без ломки существующих API и без большого рефакторинга за один slice.

## Решение

1. Добавить пакет `backend/packages/domain_authoring`.
2. На первом slice вынести минимальные domain services:
   - `OutlinePlanner`;
   - `SectionReviewService`;
   - `DocumentAssembler`.
3. Сохранить `AuthoringApplicationService` как application/orchestration boundary:
   - retrieval task lifecycle;
   - async dispatch;
   - HITL state transitions;
   - artifact persistence;
   - task/artifact link.
4. Интегрировать новые domain services через dependency injection с дефолтными реализациями.
5. Не менять внешние API/contracts на этом slice.

## Последствия

Плюсы:

- начинается реальная декомпозиция authoring домена без регрессии публичных контрактов;
- reviewer/outline/assembly logic становится изолированной и напрямую тестируемой;
- следующие slices могут отдельно выносить outline planning, section workflows и assembly contracts.

Минусы:

- `AuthoringApplicationService` пока остается крупным orchestrator;
- writer/research/traceability/HITL logic еще не полностью вынесены в `domain_authoring`.
