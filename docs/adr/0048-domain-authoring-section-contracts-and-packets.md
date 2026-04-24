# ADR-0048: Domain authoring section contracts and packets baseline

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После ADR-0047 domain layer уже покрывал outline/review/assembly/research/writer composition, но authoring pipeline по-прежнему оперировал только общим draft и traceability секциями. В `Increment 28` следующий логичный шаг — ввести typed section-oriented contracts, не переводя весь pipeline на section-by-section execution за один раз.

## Решение

1. Добавить новые typed schemas:
   - `SectionContract`;
   - `SectionPacket`.
2. Добавить `SectionContractBuilder` в `domain_authoring`.
3. На текущем slice строить release-readiness section contracts из evidence/review context и сохранять их в:
   - `AuthoringTaskState.section_contracts`;
   - artifact metadata.
4. Не менять публичные API и не вводить отдельный section workflow пока что.

## Последствия

Плюсы:

- появляется typed boundary для следующего шага к section-by-section authoring;
- section intent и preferred source refs становятся наблюдаемыми в state и artifact metadata;
- переход к outline approval/section workflows можно делать постепенно, без сноса текущего pipeline.

Минусы:

- pipeline пока все еще пишет единый draft, а не отдельные section drafts;
- `SectionPacket` пока зафиксирован как baseline contract и еще не используется отдельным workflow runner.
