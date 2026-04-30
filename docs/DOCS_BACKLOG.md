# Documentation Backlog (Framework)

Дата старта: 2026-04-30  
Last Update: 2026-04-30  
Статус: Active (living document)

## Назначение

Этот backlog — единый источник правды по задачам на developer-документацию framework-слоя.

## Правило актуальности (обязательно)

1. Любая правка документации должна сопровождаться обновлением этого файла.
2. Любое изменение документационного scope (новый guide, новый reference, новый policy) должно быть отражено как новая задача.
3. При закрытии задачи обязательно обновлять:
   - `Status`
   - `Last Update`
   - краткий `Notes` (что именно закрыто).
4. Pull request по docs считается неполным, если `docs/DOCS_BACKLOG.md` не обновлен.

## Статусы

- `Planned`
- `In Progress`
- `Blocked`
- `Done`

## Бэклог

| ID | Priority | Workstream | Task | Deliverable | Status | Last Update | Notes |
|---|---|---|---|---|---|---|---|
| DOC-001 | P0 | Information Architecture | Сделать единый docs entrypoint для ролей Integrator/Contributor/Maintainer | Новый индекс структуры и маршрутов чтения | Done | 2026-04-30 | Обновлен `docs/developer_guide/README.md`: добавлен role-based entrypoint и маршруты чтения для Integrator/Contributor/Maintainer. |
| DOC-002 | P0 | Public Contracts | Зафиксировать Public Contract Surface v1 (stable/experimental) | Документ с границами стабильности | Done | 2026-04-30 | Добавлен `docs/developer_guide/public_contract_surface.md` с stable/experimental/internal матрицей по API, MCP, схемам и runtime config. |
| DOC-003 | P0 | Framework Concepts | Описать framework layers и execution model (LangGraph runtime, async plane, HITL, quality gates) | Concept guide | Planned | 2026-04-30 |  |
| DOC-004 | P0 | Onboarding | Подготовить quickstart-профили: local dev / stage-like / prod-like | Расширенный onboarding guide | Planned | 2026-04-30 |  |
| DOC-005 | P0 | End-to-End | Добавить canonical walkthrough: documents -> indexing -> retrieval -> authoring -> HITL -> artifact | Сквозной practical guide | Planned | 2026-04-30 |  |
| DOC-006 | P0 | API Reference | Сформировать человеко-читаемый reference по FastAPI endpoints + payload contracts | API reference guide | Planned | 2026-04-30 |  |
| DOC-007 | P0 | MCP Reference | Сформировать reference по MCP services/tools/scopes/roles/errors | MCP reference guide | Planned | 2026-04-30 |  |
| DOC-008 | P0 | Env & Config | Сформировать единый каталог env-переменных и runtime effects | Configuration reference | Planned | 2026-04-30 |  |
| DOC-009 | P0 | Ops & Release | Упаковать smoke/release gate процесс как один reproducible flow | Operations + release playbook sync | Planned | 2026-04-30 |  |
| DOC-010 | P0 | Extension Path | Детализировать extension handbooks: workflow/tool/MCP/persistence/domain | Extension documentation set | Planned | 2026-04-30 |  |
| DOC-011 | P1 | Persistence & Data | Описать БД-модель: migrations, latest/history policy, version lookup, rollback expectations | Persistence reference | Planned | 2026-04-30 |  |
| DOC-012 | P1 | Observability | Описать task events/observability/HITL observability и SLA интерпретацию | Observability handbook | Planned | 2026-04-30 |  |
| DOC-013 | P1 | Governance | Подготовить OSS governance docs: CONTRIBUTING, CODE_OF_CONDUCT, SUPPORT | Governance package | Planned | 2026-04-30 |  |
| DOC-014 | P1 | Security | Подготовить SECURITY policy (vuln reporting, disclosure flow, RBAC limitations) | SECURITY.md | Planned | 2026-04-30 |  |
| DOC-015 | P1 | Versioning | Зафиксировать документационную/контрактную versioning policy и deprecation policy | Versioning policy doc | Planned | 2026-04-30 |  |
| DOC-016 | P1 | QA for Docs | Ввести docs contract checks для новых разделов и обязательных ссылок | Unit tests for docs contracts | Planned | 2026-04-30 |  |
| DOC-017 | P2 | Examples Catalog | Каталог reusable примеров для integrators (retrieval-first, authoring-first, MCP-first) | Examples cookbook | Planned | 2026-04-30 |  |
| DOC-018 | P2 | Architecture Decision Navigation | Добавить “ADR reading map” для внешних разработчиков | ADR navigation guide | Planned | 2026-04-30 |  |
| DOC-019 | P2 | Maintainer Playbook | Описать process для релизов docs, triage docs issues, review rules | Maintainer docs playbook | Planned | 2026-04-30 |  |
| DOC-020 | P0 | License | Определить и зафиксировать OSS-лицензию + rationale | LICENSE + short rationale doc | Planned | 2026-04-30 | Кандидат по умолчанию: Apache-2.0 |

## Журнал изменений backlog

- 2026-04-30: Закрыты DOC-001 и DOC-002; добавлен role-based docs entrypoint и `public_contract_surface.md` (v1).
- 2026-04-30: Инициализирован baseline backlog для полного цикла framework documentation и OSS readiness.
