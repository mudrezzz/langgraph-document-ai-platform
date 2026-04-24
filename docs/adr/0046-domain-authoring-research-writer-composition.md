# ADR-0046: Domain authoring research and writer composition extraction

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0045 reviewer/outline/assembly logic уже была вынесена в `domain_authoring`, но `AuthoringApplicationService` все еще содержал:

- построение research summary из evidence;
- deterministic writer draft composition;
- LLM prompt composition.

Это оставляло application layer перегруженным доменным форматированием текста и затрудняло дальнейшее выделение section-oriented authoring workflows.

## Решение

1. Добавить в `domain_authoring` еще два stateless сервиса:
   - `ResearchSummaryBuilder`;
   - `WriterDraftService`.
2. Оставить в `AuthoringApplicationService` только orchestration writer stage:
   - выбор `draft_strategy`;
   - вызов внешнего `IChatModelGateway`;
   - fallback policy и metadata результата.
3. Передать новые domain services в application layer через dependency injection с дефолтными реализациями.
4. Не менять внешние authoring/HITL API и artifact contracts.

## Последствия

Плюсы:

- research/writer text composition теперь тестируется отдельно от orchestration и LLM gateway;
- граница между domain formatting и application orchestration стала явнее;
- следующий slice может выносить section packets/workflows без смешивания с prompt/draft formatting.

Минусы:

- решение все еще не выделяет полноценный section authoring workflow;
- application layer пока сохраняет lifecycle orchestration и HITL rewrite policy.
