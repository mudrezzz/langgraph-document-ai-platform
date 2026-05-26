# Documentation Backlog (Framework)

Дата старта: 2026-04-30  
Last Update: 2026-05-26  
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
| DOC-004 | P0 | Onboarding | Подготовить quickstart-профили: local dev / stage-like / prod-like | Расширенный onboarding guide | Done | 2026-04-30 | `quickstart.md` переработан в HOW TO entrypoint по целям разработчика (расширение, быстрый старт нового agent flow, release path), runtime-профили вынесены в `env_profile_snippets.md`. |
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
| DOC-017 | P2 | Examples Catalog | Каталог reusable примеров для integrators (retrieval-first, authoring-first, MCP-first) | Examples cookbook | Done | 2026-04-30 | Добавлен `docs/developer_guide/examples_catalog.md` с retrieval-first/authoring-first/MCP-first/canonical сценариями. |
| DOC-018 | P2 | Architecture Decision Navigation | Добавить “ADR reading map” для внешних разработчиков | ADR navigation guide | Done | 2026-04-30 | Добавлен `docs/developer_guide/adr_reading_map.md` с role-based fast path и topic map по ADR. |
| DOC-019 | P2 | Maintainer Playbook | Описать process для релизов docs, triage docs issues, review rules | Maintainer docs playbook | Done | 2026-04-30 | Добавлен `docs/developer_guide/maintainer_playbook.md` с intake/triage/review/release cadence и DoD для docs PR. |
| DOC-020 | P0 | License | Определить и зафиксировать OSS-лицензию + rationale | LICENSE + short rationale doc | Done | 2026-04-30 | Добавлены `LICENSE` (Apache-2.0) и `docs/oss_license_rationale.md`. |
| DOC-021 | P1 | Onboarding Ergonomics | Добавить profile-ready env snippets/templates (dev/stage/prod) для быстрого старта без ручного поиска переменных | Env snippets guide/template | Done | 2026-04-30 | Добавлен `docs/developer_guide/env_profile_snippets.md` с copy-paste профилями `dev/stage/prod` и рекомендуемыми smoke-командами. |
| DOC-022 | P0 | Repository Front Door | Переписать главный README как GitHub entrypoint (value proposition + CTA + быстрые маршруты) | Marketing-oriented root README | Done | 2026-04-30 | Полностью переработан `README.md`: короткий product pitch, сценарии использования, 5-minute quickstart и маршруты в `docs/developer_guide/*`; payload contracts перенесены в `api_reference.md`. |
| DOC-023 | P0 | Agent Builder Onboarding | Добавить в корневой README быстрый HOW TO для сценария “создать нового агента/agent flow” + extension map | README quickstart extension block | Done | 2026-04-30 | В `README.md` добавлены разделы `Quickstart: Build A New Agent Flow` и `Extension Map` с прямыми маршрутами на `framework_concepts`, `extension_handbook`, `extension_recipes`, `api_reference`, `mcp_reference`, `persistence_reference`. |
| DOC-024 | P0 | README Conversion | Добавить в README copy-paste starters (retrieval-first/authoring-first) и короткий architecture story для non-technical visitors | README starter commands + value framing block | Done | 2026-04-30 | В `README.md` добавлены `Copy-Paste Starters` и `30-Second Architecture Story` с value claims (speed/risk/ownership) и прямыми командами старта. |
| DOC-025 | P0 | Example Gallery | Добавить runnable библиотеку простых кейсов framework для быстрого вдохновения и старта | `backend/examples` quickstart launcher + examples guide | Done | 2026-04-30 | Добавлены `backend/examples/quickstart_agents.py` и `backend/examples/README.md` с runnable кейсами `retrieval_faq_assistant`, `authoring_policy_brief`, `hitl_review_loop`, поддержкой `--list`, `dry-run` и `--execute`. |
| DOC-026 | P0 | Pattern Library | Добавить библиотеку design patterns с привязкой к runnable примерам и тестами | `docs/developer_guide/design_patterns/*` + unit/docs contracts | Done | 2026-04-30 | Добавлены `design_patterns/README.md` и pattern-guides (`retrieval-first`, `authoring-first`, `hitl-gate`), обновлены `README.md`/`developer_guide/README.md`, добавлен unit test `test_example_quickstart_agents.py` и расширены docs contracts. |
| DOC-027 | P0 | Productized Agent Examples | Пересобрать examples как отдельный product-like каталог Python-агентов без необходимости читать framework internals | `agent_examples/*` (single-folder entrypoint, pattern code, tests) | Done | 2026-04-30 | Добавлен новый каталог `agent_examples/` с единым раннером `run_example.py`, общей runtime/client обвязкой, тремя pattern-папками (`retrieval_first`, `authoring_first`, `hitl_gate`) и локальными тестами. |
| DOC-028 | P0 | Example UX Integration | Встроить новый `agent_examples` в основной onboarding и README-позиционирование проекта | README + developer guide route updates + contracts | Done | 2026-04-30 | Обновлены `README.md`, `docs/developer_guide/README.md`, `quickstart.md`, `examples_catalog.md`, `design_patterns/*`; добавлены contract/unit tests для структуры и dry-run запуска `agent_examples`. |
| DOC-029 | P0 | Agent Examples Replatform Plan | Зафиксировать детальный план перехода demo-агентов к in-process framework usage (вместо transport-first примеров) | Program roadmap doc + docs route integration | Done | 2026-04-30 | Добавлен `docs/developer_guide/agent_examples_demo_program.md`; обновлены `developer_guide/README.md`, `design_patterns/README.md`, docs contracts. |
| DOC-030 | P0 | Retrieval Pattern Rebuild | Пересобрать `retrieval_first` как library-style in-process агент (`main.py + workflow.py + tools.py`) | Reworked retrieval pattern folder + tests + expected output | Done | 2026-04-30 | `retrieval_first` переведен на прямой `build_retrieval_workflow(...).invoke(...)`; добавлены `main.py`, `workflow.py`, `tools.py`, `expected_output`, pattern tests и обновлен `run_example.py` на in-process execution model для retrieval. |
| DOC-031 | P0 | Authoring Pattern Rebuild | Пересобрать `authoring_first` как in-process агент с явной artifact assembly моделью | Reworked authoring pattern folder + tests + expected output | Planned | 2026-04-30 | Фокус на понятный composition code и traceability proof в одном примере. |
| DOC-032 | P0 | HITL Pattern Rebuild | Пересобрать `hitl_gate` как in-process pattern с reviewer loop contract | Reworked hitl pattern folder + tests + expected output | Planned | 2026-04-30 | Показывать `needs_changes -> approve` без transport-first зависимости как primary path. |
| DOC-033 | P0 | Examples Test Harness | Добавить unified fast/full test lanes для `agent_examples` (structure/unit/smoke) | Test matrix doc + CI-ready command set | Planned | 2026-04-30 | Требуется для защиты от деградации примеров и рассинхрона с документацией. |
| DOC-034 | P1 | Async Batch Pattern | Добавить отдельный in-process demo pattern для batch/long-running сценариев | `patterns/async_batch/*` + docs/tests | Planned | 2026-04-30 | После стабилизации трех базовых P0 patterns. |
| DOC-035 | P1 | MCP Facade Pattern | Добавить отдельный demo pattern `agent as MCP tools` поверх core agent logic | `patterns/mcp_tool_facade/*` + docs/tests | Planned | 2026-04-30 | Должен показать разделение core logic и MCP transport adapter. |
| DOC-036 | P0 | OSS Program Planning | Зафиксировать единую программу доработок contributor funnel с итерациями и слайсами | `docs/developer_guide/oss_contributor_funnel_program.md` + sync links | Planned | 2026-05-26 | Базовый план для Increment 33; включает ограничения по stable contracts и Definition of Done на 30 дней. |
| DOC-037 | P0 | Packaging Integrity | Синхронизировать package license/readme metadata с OSS policy репозитория | `backend/packages/pyproject.toml` + `backend/packages/README.md` | Done | 2026-05-26 | Закрыты Slice 33.1.1 и 33.1.2: package license metadata выровнен (`Apache-2.0`), добавлен package-level README под `readme = \"README.md\"`. |
| DOC-038 | P0 | README No-Infra Entry | Добавить no-infra first-success path и expected output в root README | `README.md` update (2-minute demo + output proof) | Planned | 2026-05-26 | Быстрый запуск без FastAPI/PostgreSQL/Celery/Redis/MCP должен идти до production path. |
| DOC-039 | P0 | First-Time Contributor Path | Добавить first-time contributor section и вычистить ссылки в contribution flow | `CONTRIBUTING.md` update | Planned | 2026-05-26 | Явный безопасный путь первого PR в зонах docs/examples/packaging. |
| DOC-040 | P1 | Community Templates | Ввести issue forms и PR template для структурированного intake | `.github/ISSUE_TEMPLATE/*` + `.github/pull_request_template.md` | Planned | 2026-05-26 | Bug/docs/feature/question шаблоны + contract impact checklist в PR template. |
| DOC-041 | P1 | Public Backlog Funnel | Подготовить стартовый public issue backlog и label taxonomy | 15-20 issue drafts + label matrix + triage policy note | Planned | 2026-05-26 | Минимум 8 actionable `good first issue` с четкими acceptance criteria. |
| DOC-042 | P2 | README Front Door v2 | Перестроить README под open-source front door и добавить comparison table | `README.md` restructure + use-case matrix | Planned | 2026-05-26 | `Who for`/`When not to use`/`No-infra demo`/`Docs map` как основной маршрут. |
| DOC-043 | P2 | Discoverability | Синхронизировать GitHub topics и позиционирование capabilities | Repository topics + docs notes | Planned | 2026-05-26 | Topics до 20, только под реальные возможности репозитория. |
| DOC-044 | P2 | Contributor Motivation & Feedback Loop | Добавить мотивационный и feedback контур для внешних контрибьюторов | README/CONTRIBUTING messaging + `FEEDBACK.md` + project update template | Planned | 2026-05-26 | Включает блок про добровольную поддержку токенами без нарушения governance (no pay-to-prioritize). |

## Журнал изменений backlog

- 2026-05-26: Закрыт DOC-037; завершены Slice 33.1.1 (license alignment) и Slice 33.1.2 (`backend/packages/README.md`).
- 2026-05-26: DOC-037 переведен в `In Progress`; закрыт Slice 33.1.1 (package license metadata -> Apache-2.0), открыт remaining scope по package README.
- 2026-05-26: Добавлены planned задачи DOC-036..DOC-044 для Increment 33 (OSS contributor funnel); создан программный документ `docs/developer_guide/oss_contributor_funnel_program.md`; `Last Update` обновлен.
- 2026-04-30: Закрыт DOC-030; `retrieval_first` переведен в in-process framework pattern с отдельным `main.py`, workflow/tools и локальными тестами.
- 2026-04-30: Добавлен и закрыт DOC-029 (детальный roadmap replatform demo-агентов в in-process стиль); добавлены planned задачи DOC-030..DOC-035.
- 2026-04-30: Закрыты DOC-027 и DOC-028; внедрен новый product-style каталог `agent_examples/` и интегрирован как основной entrypoint для python-примеров агентов.
- 2026-04-30: Закрыты DOC-025 и DOC-026; добавлены runnable examples gallery, design patterns library и тесты/контракты для новых entrypoints.
- 2026-04-30: Закрыт DOC-024; в README добавлены copy-paste starters и 30-second architecture story с value framing.
- 2026-04-30: Закрыт DOC-023; в корневой README добавлены быстрый путь для нового agent flow и карта типов расширений.
- 2026-04-30: Закрыт DOC-022; корневой `README.md` переписан в формат GitHub-витрины и синхронизирован с developer guide.
- 2026-04-30: Обновлен DOC-004 notes; `quickstart.md` переработан в навигационный HOW TO для разработчика.
- 2026-04-30: Закрыты DOC-017, DOC-018 и DOC-019; добавлены examples catalog, ADR reading map и maintainer docs playbook.
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
