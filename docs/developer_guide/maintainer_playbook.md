# Maintainer Playbook (Docs)

Дата обновления: 2026-05-27  
Статус: Active (Increment 33 triage baseline)

Документ описывает process для поддержки документации как живой contract surface.

## 1. Maintainer responsibilities

1. Держать docs синхронизированными с кодом.
2. Защищать стабильные контракты (`public_contract_surface`).
3. Обеспечивать предсказуемый review/merge process.

## 2. Intake and triage

Для каждого docs issue определить:

1. Type:
   - `contract_update`
   - `new_guide`
   - `bugfix/clarification`
2. Priority:
   - `P0`: влияет на стабильный contract/release path
   - `P1`: влияет на onboarding/operations
   - `P2`: улучшение навигации/примеров
3. Scope:
   - какие документы затрагиваются
   - нужен ли backlog item

## 3. Change workflow

1. Сделать изменение в docs.
2. Обновить `docs/DOCS_BACKLOG.md`:
   - `Status`
   - `Last Update`
   - `Notes`
3. Если change влияет на stable contracts:
   - обновить `public_contract_surface.md`
   - обновить `api_reference.md` и/или `mcp_reference.md`
4. Прогнать docs checks:
   - `.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py`
5. Коммит/PR с кратким changelog.

## 4. Docs review rules

Review не пропускается, если:

1. Есть docs правки, но не обновлен `docs/DOCS_BACKLOG.md`.
2. Изменился публичный API/MCP behavior, но не обновлены reference docs.
3. Добавлен новый guide без связи с role-based entrypoint (`docs/developer_guide/README.md`).

Review checklist:

1. Фактическая корректность по коду/скриптам.
2. Нет выдуманных возможностей.
3. Ясно указаны stability boundaries.
4. Есть migration note для breaking/deprecation changes.

## 5. Release docs cadence

На каждый backend/framework increment:

1. Обновить ключевые docs (README/architecture/developer_guide при необходимости).
2. Синхронизировать backlog.
3. Зафиксировать changelog в PR description.

Периодически (например, раз в 2-4 недели):

1. Проверять консистентность cross-links.
2. Проверять актуальность run-команд из `backend/scripts/README.md`.
3. Пересматривать P1/P2 backlog при появлении нового scope.

## 6. Escalation policy

Эскалировать на архитектурный review, если:

- предлагается breaking change stable contract surface;
- требуется смена license/governance/security policy;
- есть конфликт между ADR и текущей документацией.

## 7. Definition of done for docs PR

PR считается готовым, если:

1. Документация обновлена по факту изменений.
2. `docs/DOCS_BACKLOG.md` синхронизирован.
3. Docs tests проходят.
4. Есть понятный summary изменений.

## 8. Label taxonomy baseline

Maintainer baseline labels для intake/triage:

- `good first issue`
- `help wanted`
- `docs`
- `examples`
- `ci`
- `packaging`
- `bug`
- `enhancement`
- `question`
- `discussion`
- `needs maintainer review`
- `blocked`
- `security`
- `community`

Правило: каждый новый issue получает как минимум один label типа (`bug`/`enhancement`/`docs`/`question`) и при необходимости один workflow label (`needs maintainer review`/`blocked`).

## 9. Triage SLA and status policy

Best-effort SLA:

1. Новый issue: первая реакция/разметка в течение 72 часов.
2. Новый PR: первичная реакция в течение 5 рабочих дней.
3. Security issue: не обсуждать детали публично, перенаправлять в процесс из `SECURITY.md`.

Triage status baseline:

- `actionable`
- `needs info`
- `duplicate`
- `not planned`
- `maintainer review`

Минимум для каждого нового issue:

1. label;
2. triage status;
3. короткий maintainer-комментарий с next step.

Issue closure baseline:

1. `duplicate` -> закрыть с ссылкой на source issue.
2. `needs info` без ответа 14-21 дней -> закрыть с комментарием о возможности переоткрытия с данными.
3. out-of-scope/support-only запросы -> закрыть с явной причиной и ссылкой на релевантный docs path.
