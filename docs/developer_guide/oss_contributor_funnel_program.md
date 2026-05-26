# OSS Contributor Funnel Program (Increment 33)

Дата: 2026-05-26  
Статус: Planned  
Scope: community/onboarding/documentation packaging без изменения backend public contracts.

## 1. Цель

Снизить порог входа для внешних пользователей и контрибьюторов, не ломая production-first позиционирование проекта.

Программа закрывает путь:

`value -> first demo -> question -> issue -> first PR -> return contributor`.

## 2. Границы и ограничения

1. Не менять stable API/MCP contracts без maintainer review и синхронизации:
   - `docs/developer_guide/public_contract_surface.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
2. Все docs-изменения синхронизировать через `docs/DOCS_BACKLOG.md`.
3. Production smoke/release path не удалять; только перестроить приоритеты onboarding entrypoints.
4. Коммуникация с контрибьюторами в рамках `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`.

## 3. Итерационный план и слайсы

## Iteration 33.1 (P0): Foundation Fixes

Срок: Day 1-5.

Slice 33.1.1: License/package consistency
- Обновить `backend/packages/pyproject.toml`: `license = { text = "Apache-2.0" }`.
- Проверить consistency claims в root `README.md`.
- Результат: нет расхождения между root license и package metadata.

Slice 33.1.2: Package README
- Добавить `backend/packages/README.md`.
- Включить блоки: `Install`, `Included`, `Not Included`, `Minimal example`.
- Результат: package metadata `readme = "README.md"` валиден и полезен для внешнего потребителя.

Slice 33.1.3: No-infra first success path
- Добавить в root README блок `2-Minute Demo: No Docker, No Postgres`.
- База: `agent_examples/run_example.py --pattern retrieval_first` (+ `--dry-run`).
- Результат: первый запуск без FastAPI/PostgreSQL/Celery/Redis/MCP.

Slice 33.1.4: Contribution entrypoint cleanup
- Исправить broken/ambiguous docs links в `CONTRIBUTING.md`.
- Добавить секцию `First-time contributors` с безопасной зоной задач (docs/examples/packaging).
- Результат: понятный безопасный путь первого PR без погружения во весь runtime.

## Iteration 33.2 (P1): Contributor Funnel

Срок: Day 6-14.

Slice 33.2.1: GitHub templates
- Добавить `.github/ISSUE_TEMPLATE/` (bug/documentation/feature/question).
- Добавить `.github/pull_request_template.md`.
- Результат: структурированные входы issue/PR.

Slice 33.2.2: Labels and triage baseline
- Дополнить labels до набора из ТЗ (`docs`, `examples`, `ci`, `packaging`, `community`, `needs maintainer review`, `blocked`, `security` и др.).
- Результат: каждый новый issue получает тип и triage-статус.

Slice 33.2.3: Initial public backlog
- Создать 15-20 issues; минимум 8 пометить `good first issue`.
- Для каждой задачи: `Context`, `Scope`, `Suggested files`, `Acceptance criteria`, `Notes for first-time contributors`.
- Результат: публичная очередь задач для внешнего вклада.

## Iteration 33.3 (P2): Public Front Door

Срок: Day 15-21.

Slice 33.3.1: README restructure
- Перестроить README по порядку: who-for, when-not-to-use, 2-minute demo, example output, architecture, production path, docs map, contributing, license.
- Результат: быстрый успех до глубокой production документации.

Slice 33.3.2: Positioning clarity
- Добавить comparison/use-case table (`Need / Use this project? / Why`).
- Результат: честная квалификация пользователей и меньше нецелевых запросов.

Slice 33.3.3: Repository discoverability
- Добавить GitHub topics по фактическим возможностям (<=20).
- Результат: улучшенная discoverability без misrepresentation.

## Iteration 33.4 (P2): Community Messaging + Feedback Loop

Срок: Day 22-30.

Slice 33.4.1: Contributor motivation copy
- Добавить в README/CONTRIBUTING блок `Why contribute`:
  - публичный OSS-трек как подтверждаемый инженерный вклад;
  - возможность заявить о себе через реальные merged changes.
- Результат: явная мотивация для first-time contributors.

Slice 33.4.2: Token support policy
- Добавить нейтральный блок о добровольной поддержке проекта "токенами" (если maintainer подтверждает канал).
- Зафиксировать ограничения: no pay-to-prioritize, no feature guarantees, no bypass security/governance.
- Результат: поддержка проекта без конфликта с roadmap governance.

Slice 33.4.3: Updates and feedback tracker
- Добавить шаблон `Project update` (раз в 2 недели).
- Добавить `FEEDBACK.md` с полями из ТЗ.
- Результат: системный сбор onboarding blockers и их перевод в backlog.

## 4. Definition of Done (30 days)

1. README показывает no-infra demo раньше production setup.
2. Package/license metadata согласованы.
3. Добавлены issue/PR templates.
4. Сформирован backlog 15+ публичных issues, 8+ `good first issue`.
5. `CONTRIBUTING.md` содержит first-time contributor path.
6. Добавлены GitHub topics.
7. Есть минимум 1 public update и 1 внешний technical post draft.
8. Запущен feedback tracker.

## 5. Mapping to Backlogs

- Implementation track: `BACKLOG.md` -> `Increment 33: OSS Contributor Funnel and Community Readiness`.
- Documentation track: `docs/DOCS_BACKLOG.md` -> `DOC-036..DOC-044`.
