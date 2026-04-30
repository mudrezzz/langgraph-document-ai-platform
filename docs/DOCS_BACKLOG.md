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
| DOC-003 | P0 | Framework Concepts | Описать framework layers и execution model (LangGraph runtime, async plane, HITL, quality gates) | Concept guide | Done | 2026-04-30 | Добавлен `docs/developer_guide/framework_concepts.md` с layer map, runtime model, async plane, HITL и quality gates. |
| DOC-004 | P0 | Onboarding | Подготовить quickstart-профили: local dev / stage-like / prod-like | Расширенный onboarding guide | Done | 2026-04-30 | Обновлен `docs/developer_guide/quickstart.md`: добавлены три профиля запуска (`dev`, `stage-like`, `prod-like`) с командами и expected outputs. |
| DOC-005 | P0 | End-to-End | Добавить canonical walkthrough: documents -> indexing -> retrieval -> authoring -> HITL -> artifact | Сквозной practical guide | Done | 2026-04-30 | Добавлен `docs/developer_guide/canonical_e2e_walkthrough.md`; guide привязан в `developer_guide/README.md` для Integrator path. |
| DOC-006 | P0 | API Reference | Сформировать человеко-читаемый reference по FastAPI endpoints + payload contracts | API reference guide | Done | 2026-04-30 | Добавлен `docs/developer_guide/api_reference.md` (endpoint groups, payload contracts, auth headers, error mapping). |
| DOC-007 | P0 | MCP Reference | Сформировать reference по MCP services/tools/scopes/roles/errors | MCP reference guide | Done | 2026-04-30 | Добавлен `docs/developer_guide/mcp_reference.md` с service/tool matrix, scopes, required roles и error semantics. |
| DOC-008 | P0 | Env & Config | Сформировать единый каталог env-переменных и runtime effects | Configuration reference | Done | 2026-04-30 | Добавлен `docs/developer_guide/env_config_reference.md` с runtime env catalog и profile effects. |
| DOC-009 | P0 | Ops & Release | Упаковать smoke/release gate процесс как один reproducible flow | Operations + release playbook sync | Done | 2026-04-30 | Добавлен `docs/developer_guide/release_reproducible_flow.md`; обновлены `operations_and_release.md` и entrypoint-ссылки. |
| DOC-010 | P0 | Extension Path | Детализировать extension handbooks: workflow/tool/MCP/persistence/domain | Extension documentation set | Done | 2026-04-30 | Добавлен `docs/developer_guide/extension_handbook.md` с playbook-ами по workflow/tool/MCP/persistence/domain extension. |
| DOC-011 | P1 | Persistence & Data | Описать БД-модель: migrations, latest/history policy, version lookup, rollback expectations | Persistence reference | Done | 2026-04-30 | Добавлен `docs/developer_guide/persistence_reference.md` с data model map, migration policy, version lookup и rollback expectations. |
| DOC-012 | P1 | Observability | Описать task events/observability/HITL observability и SLA интерпретацию | Observability handbook | Done | 2026-04-30 | Добавлен `docs/developer_guide/observability_reference.md` с endpoint map, метриками и SLA interpretation rules. |
| DOC-013 | P1 | Governance | Подготовить OSS governance docs: CONTRIBUTING, CODE_OF_CONDUCT, SUPPORT | Governance package | Done | 2026-04-30 | Добавлены `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`. |
| DOC-014 | P1 | Security | Подготовить SECURITY policy (vuln reporting, disclosure flow, RBAC limitations) | SECURITY.md | Done | 2026-04-30 | Добавлен `SECURITY.md` с disclosure flow, scope и RBAC limitations. |
| DOC-015 | P1 | Versioning | Зафиксировать документационную/контрактную versioning policy и deprecation policy | Versioning policy doc | Done | 2026-04-30 | Добавлен `docs/developer_guide/versioning_policy.md` с правилами stable/experimental deprecation и contract versioning. |
| DOC-016 | P1 | QA for Docs | Ввести docs contract checks для новых разделов и обязательных ссылок | Unit tests for docs contracts | Done | 2026-04-30 | Обновлен `backend/tests/unit/test_developer_guide_contracts.py`: проверка новых обязательных guide-страниц и baseline checks для `docs/DOCS_BACKLOG.md`. |
| DOC-017 | P2 | Examples Catalog | Каталог reusable примеров для integrators (retrieval-first, authoring-first, MCP-first) | Examples cookbook | Planned | 2026-04-30 |  |
| DOC-018 | P2 | Architecture Decision Navigation | Добавить “ADR reading map” для внешних разработчиков | ADR navigation guide | Planned | 2026-04-30 |  |
| DOC-019 | P2 | Maintainer Playbook | Описать process для релизов docs, triage docs issues, review rules | Maintainer docs playbook | Planned | 2026-04-30 |  |
| DOC-020 | P0 | License | Определить и зафиксировать OSS-лицензию + rationale | LICENSE + short rationale doc | Done | 2026-04-30 | Добавлены `LICENSE` (Apache-2.0) и `docs/oss_license_rationale.md`. |
| DOC-021 | P1 | Onboarding Ergonomics | Добавить profile-ready env snippets/templates (dev/stage/prod) для быстрого старта без ручного поиска переменных | Env snippets guide/template | Done | 2026-04-30 | Добавлен `docs/developer_guide/env_profile_snippets.md` с copy-paste профилями `dev/stage/prod` и рекомендуемыми smoke-командами. |

## Журнал изменений backlog

- 2026-04-30: Закрыт DOC-021; добавлен env snippets guide для `dev/stage/prod`.
- 2026-04-30: Закрыты DOC-015 и DOC-016; добавлены versioning policy и docs contract checks.
- 2026-04-30: Закрыт DOC-020; зафиксирована лицензия Apache-2.0 и rationale.
- 2026-04-30: Закрыты DOC-013 и DOC-014; добавлены governance и security policy документы.
- 2026-04-30: Закрыт DOC-012; добавлен observability handbook.
- 2026-04-30: Закрыт DOC-011; добавлен persistence/data reference.
- 2026-04-30: Закрыт DOC-010; добавлен extension handbook по ключевым типам расширений.
- 2026-04-30: Закрыт DOC-009; добавлен reproducible release flow guide.
- 2026-04-30: Закрыты DOC-007 и DOC-008; добавлены `mcp_reference.md` и `env_config_reference.md`.
- 2026-04-30: Добавлен DOC-021 (profile-ready env snippets/templates) как новый onboarding scope.
- 2026-04-30: Закрыт DOC-006; добавлен API reference по FastAPI boundary.
- 2026-04-30: Закрыт DOC-005; добавлен сквозной practical walkthrough `documents -> indexing -> retrieval -> authoring -> HITL -> artifact`.
- 2026-04-30: Закрыт DOC-004; quickstart расширен профилями local dev / stage-like / prod-like.
- 2026-04-30: Закрыт DOC-003; добавлен `framework_concepts.md` и обновлен learning path в `developer_guide/README.md`.
- 2026-04-30: Закрыты DOC-001 и DOC-002; добавлен role-based docs entrypoint и `public_contract_surface.md` (v1).
- 2026-04-30: Инициализирован baseline backlog для полного цикла framework documentation и OSS readiness.
