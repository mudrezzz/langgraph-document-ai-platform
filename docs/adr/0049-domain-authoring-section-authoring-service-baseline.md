# ADR-0049: Domain authoring section authoring service baseline

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0048 система уже имела typed `SectionContract` и `SectionPacket`, но они оставались в основном схемами и metadata boundary. Для продолжения `Increment 28` нужен был минимальный исполнимый domain service, который реально потребляет section packet и возвращает section-level результат, не ломая текущий single-draft pipeline.

## Решение

1. Добавить `SectionArtifact` как typed section output.
2. Добавить `SectionAuthoringService` в `domain_authoring`.
3. На текущем slice строить deterministic `section_artifacts` и `SectionDigest` из `SectionPacket`:
   - без отдельного LangGraph workflow;
   - без смены публичных API;
   - без замены текущего финального assembled document.
4. Сохранять `section_artifacts` в `AuthoringTaskState` и artifact metadata.

## Последствия

Плюсы:

- section packet boundary теперь не только типизирован, но и исполняем;
- section digests становятся наблюдаемым артефактом в authoring state и metadata;
- следующий шаг к полноценному `SectionAuthoringWorkflow` становится заметно меньше.

Минусы:

- section artifacts пока не участвуют в deterministic final assembly как первичный источник;
- service пока deterministic и не содержит отдельного reviewer/consistency sub-workflow по секциям.
