# Contributing Guide

Спасибо за вклад в `langgraph-document-ai-platform`.

## 1. Scope

Репозиторий развивается как framework-first платформа:

- typed contracts (`schemas`)
- workflow/runtime (`framework`, `application`)
- adapters (`infra`)
- service boundaries (`apps/api`, `apps/mcp_*`)

Приоритет изменений: reproducibility, backward-compatible contracts, observability.

## 2. Why your contribution matters

Вклад в этот проект — это публично проверяемый engineering track:

- задачи и обсуждения прозрачны в issues/PR history;
- изменения проверяются через тесты/smoke и review;
- вклад виден по impact в onboarding/docs/examples/packaging/CI.

Где лучше начать:

- `good first issue` — узкие newcomer-friendly задачи;
- `help wanted` — задачи, где поддержка контрибьюторов особенно важна;
- `community` — улучшение contributor experience и процесса.

Для вайбкодеров:

- Это открытый OSS-проект, где можно начать с маленьких задач и быстро получить проверяемый результат.
- Рекомендуем progression path: `docs -> examples -> packaging -> CI -> deeper framework tasks`.
- Ключевое правило: быстрые итерации приветствуются, но качество фиксируется через checks + review.

## 3. Contribution flow

1. Откройте issue с кратким proposal (problem -> scope -> expected behavior).
2. Подготовьте изменение в отдельной ветке.
3. Обновите документацию и `docs/DOCS_BACKLOG.md` вместе с кодом.
4. Прогоните минимальные проверки (см. ниже).
5. Откройте PR с кратким changelog и рисками.

## 4. First-time contributors

Если это ваш первый вклад, начните с задач в безопасной зоне:

- docs (`README`, `developer_guide`, `DOCS_BACKLOG`);
- examples (`agent_examples` docs/tests);
- packaging metadata (`backend/packages/*`).

Рекомендуемый минимальный путь первого PR:

1. Возьмите issue с меткой `good first issue` или `docs`.
2. Уточните scope в issue-комментарии перед началом работы.
3. Держите изменения узкими: один PR = одна задача.
4. Если правите public contracts, заранее отметьте это в PR (`needs maintainer review`).
5. После 1-2 docs/examples PR переходите к `packaging` или `ci` задачам, где impact также легко проверить.

## 5. Required checks

Минимально перед PR:

1. `bash backend/scripts/postgres_migrate.sh`
2. `bash backend/scripts/smoke_retrieval_api.sh`
3. `bash backend/scripts/smoke_release_gate.sh --gate-profile stage`
4. `pytest backend/tests -q` (или targeted subset + объяснение в PR)

Если изменения касаются MCP/authoring/indexing, добавьте соответствующие smoke.

Для docs/examples/packaging-only PR (без runtime/API изменений) допустим облегченный набор:

1. `python -m pytest -q backend/tests/unit/test_developer_guide_contracts.py`
2. targeted tests только для затронутого примера/модуля (если применимо)
3. в PR явно указать, что full smoke не запускался, потому что contract/runtime не менялись

## 6. Contract safety rules

- Не меняйте public contracts без обновления:
  - `docs/developer_guide/public_contract_surface.md`
  - `docs/developer_guide/api_reference.md` и/или `docs/developer_guide/mcp_reference.md`
- Для schema changes используйте additive migrations.
- Не ломайте latest/history semantics для canonical/versioned stores.

## 7. Commit and PR style

- Commit message: коротко и предметно (`docs: ...`, `feat: ...`, `fix: ...`).
- В PR обязательно:
  - что изменилось;
  - как проверяли;
  - какие риски/ограничения остались.

## 8. Communication

- Уважайте review feedback.
- Для спорных архитектурных решений добавляйте/обновляйте ADR.

## 9. Code of Conduct

Этот проект придерживается правил из `CODE_OF_CONDUCT.md`.
