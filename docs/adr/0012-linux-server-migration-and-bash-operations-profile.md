# ADR-0012: Миграция на Linux сервер и Bash operations profile

- Статус: Accepted
- Дата: 2026-04-19

## Контекст

Локальная разработка на Windows оказалась тяжелой для Docker-нагрузки. Для дальнейших итераций проект переносится на Linux-сервер (Ubuntu 24), где нужно иметь штатный операционный контур без зависимости от PowerShell.

## Решение

1. Зафиксировать Linux-скрипты в `backend/scripts`:
   - `apply_migrations.sh`;
   - `postgres_up.sh`, `postgres_migrate.sh`, `postgres_down.sh`;
   - `smoke_retrieval_api.sh`;
   - `demo_saa_release_readiness_case.sh`.
2. Добавить отдельную документацию по скриптам:
   - `backend/scripts/README.md`.
3. Зафиксировать handoff-документ для старта нового чата уже на сервере:
   - `docs/handoff/2026-04-19_ubuntu24_server_handoff.md`.
4. Размещать дальнейшие инкременты в GitHub-репозитории:
   - `https://github.com/mudrezzz/langgraph-document-ai-platform`.

## Последствия

Плюсы:

- операционный контур больше не привязан к Windows/Powershell;
- запуск PostgreSQL, миграций и smoke становится одинаковым для серверной среды;
- ускоряется переход к реальному server deployment циклу.

Минусы:

- нужно сопровождать два набора скриптов (`.ps1` и `.sh`) в переходный период;
- часть сценариев теперь должна регулярно проверяться и на Linux, и на Windows.
