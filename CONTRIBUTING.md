# Contributing Guide

Спасибо за вклад в `langgraph-document-ai-platform`.

## 1. Scope

Репозиторий развивается как framework-first платформа:

- typed contracts (`schemas`)
- workflow/runtime (`framework`, `application`)
- adapters (`infra`)
- service boundaries (`apps/api`, `apps/mcp_*`)

Приоритет изменений: reproducibility, backward-compatible contracts, observability.

## 2. Contribution flow

1. Откройте issue с кратким proposal (problem -> scope -> expected behavior).
2. Подготовьте изменение в отдельной ветке.
3. Обновите документацию и `docs/DOCS_BACKLOG.md` вместе с кодом.
4. Прогоните минимальные проверки (см. ниже).
5. Откройте PR с кратким changelog и рисками.

## 3. Required checks

Минимально перед PR:

1. `bash backend/scripts/postgres_migrate.sh`
2. `bash backend/scripts/smoke_retrieval_api.sh`
3. `bash backend/scripts/smoke_release_gate.sh --gate-profile stage`
4. `pytest backend/tests -q` (или targeted subset + объяснение в PR)

Если изменения касаются MCP/authoring/indexing, добавьте соответствующие smoke.

## 4. Contract safety rules

- Не меняйте public contracts без обновления:
  - `docs/developer_guide/public_contract_surface.md`
  - `docs/developer_guide/api_reference.md` и/или `mcp_reference.md`
- Для schema changes используйте additive migrations.
- Не ломайте latest/history semantics для canonical/versioned stores.

## 5. Commit and PR style

- Commit message: коротко и предметно (`docs: ...`, `feat: ...`, `fix: ...`).
- В PR обязательно:
  - что изменилось;
  - как проверяли;
  - какие риски/ограничения остались.

## 6. Communication

- Уважайте review feedback.
- Для спорных архитектурных решений добавляйте/обновляйте ADR.

## 7. Code of Conduct

Этот проект придерживается правил из `CODE_OF_CONDUCT.md`.
