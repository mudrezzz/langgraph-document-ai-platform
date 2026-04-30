# ADR-0092: External developer documentation surface

- Статус: Accepted
- Дата: 2026-04-29

## Контекст

Backend/framework foundation достиг production-ready стадии (Increment 32), но вход для внешнего разработчика был размазан между `README.md`, runbook-ами и ADR.

Для интеграции reusable библиотеки и ручной проверки demo (включая binary parsers PDF/PPTX) нужен единый, короткий и операционно-практичный documentation surface.

## Решение

1. Добавлен единый внешний docs entrypoint:
   - `docs/developer_guide/README.md`.
2. Документация разделена на 4 практических слоя:
   - `quickstart.md` (bootstrap + первый smoke);
   - `manual_demo_checks.md` (ручной proof PDF/PPTX + multifile demo report);
   - `extension_recipes.md` (workflow/tool/MCP/persistence extension path);
   - `operations_and_release.md` (release-gate и full pytest gate).
3. В `README.md` добавлен явный раздел навигации на новый developer guide.
4. Добавлен docs-contract test, который проверяет наличие ключевых секций и критичных ссылок.

## Последствия

Плюсы:

- внешний разработчик получает предсказуемый onboarding path без чтения всего архива ADR;
- ручная валидация binary parsing path (PDF/PPTX) становится воспроизводимой;
- снижается риск рассинхронизации между scripts, runbook и внешней документацией.

Минусы:

- добавляется новый documentation surface, который нужно поддерживать синхронно с runtime контрактами;
- часть информации дублируется с `README.md` и runbook-ами, что требует contract-тестов на актуальность.
