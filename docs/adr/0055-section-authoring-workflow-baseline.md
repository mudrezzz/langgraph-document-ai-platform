# ADR-0055: Section authoring workflow baseline

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0054 authoring уже имел typed `SectionContract`, `SectionPacket`, `SectionArtifact`, outline approval point и template-aware deterministic assembly. Но section generation по-прежнему исполнялась как прямой вызов `SectionAuthoringService`, без собственной workflow boundary, хотя в scope `Increment 28` изначально был заложен `SectionAuthoringWorkflow`.

## Решение

1. Добавить `domain_authoring.SectionAuthoringWorkflow` как baseline workflow поверх существующих `SectionAuthoringService` и `SectionReviewService`.
2. Использовать typed `SectionAuthoringState` и multi-node path:
   - `write_section`;
   - `review_section`;
   - `finalize_section`.
3. Для resume path поддержать baseline rewrite hook `rewrite_section`, который применяет section-level human feedback без отдельного reviewer/HITL subgraph.
4. Перевести `AuthoringApplicationService` на построение `section_artifacts` через workflow boundary, не меняя внешние authoring API.
5. Не вводить отдельный section persistence/read-model и не выносить section workflow в самостоятельный публичный endpoint на этом шаге.

## Последствия

Плюсы:

- section authoring теперь следует тем же framework workflow patterns, что и retrieval/indexing;
- появляется явная точка роста для section HITL, section review subgraph и selective rewrite;
- application service меньше зависит от прямого deterministic service call.

Минусы:

- workflow пока запускается по одной секции за раз и не имеет собственного persistence/read-model слоя;
- section review по-прежнему использует общий deterministic reviewer heuristic, без отдельной section-specific policy;
- resume path пока поддерживает только простой feedback append, а не полноценный rewrite planner.
