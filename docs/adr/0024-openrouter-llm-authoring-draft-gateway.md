# ADR-0024: OpenRouter LLM Gateway для authoring draft

- Статус: Accepted
- Дата: 2026-04-20

## Контекст

После `Increment 18` authoring flow работал только в deterministic режиме (`retrieval -> draft -> artifact`) и был полезен как технический контур, но демонстрационно выглядел слишком статично.

Нужно было:

- подключить реальную LLM без слома текущего API;
- сохранить предсказуемость regression-тестов;
- добавить управляемый fallback для `prod`-совместимого контура.

## Решение

1. Добавить OpenRouter chat gateway в infra layer:
   - `infra/openrouter/OpenRouterChatModelGateway`;
   - интеграция через существующий `IChatModelGateway` контракт.
2. Расширить authoring API контракт полем `draft_strategy`:
   - `auto` (использует LLM, если включена в env);
   - `deterministic` (принудительно без LLM);
   - `llm` (принудительно через LLM).
3. Ввести env-конфигурацию LLM runtime:
   - `APP_LLM_ENABLED`, `APP_LLM_PROVIDER`, `APP_LLM_STRICT`;
   - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_TIMEOUT_SEC`.
4. Добавить safe fallback:
   - при `APP_LLM_STRICT=false` и ошибке gateway draft строится deterministic логикой;
   - в metadata артефакта пишется `draft_generation_mode` и причина fallback.
5. Добавить отдельный внешний тест real LLM:
   - `backend/tests/integration/test_authoring_openrouter_external.py`;
   - запускается только при `RUN_EXTERNAL_LLM_TESTS=1`.

## Последствия

Плюсы:

- demo authoring стал "живым" благодаря реальной генерации текста;
- API сохранил обратную совместимость (default `draft_strategy=auto`);
- regression suite остается детерминированным (`draft_strategy=deterministic` в обычных integration/e2e тестах).

Минусы:

- добавлена зависимость от внешнего LLM-провайдера для external smoke;
- качество draft зависит от выбранной модели и стабильности сети;
- пока нет multi-step authoring цикла и reviewer-петли.
