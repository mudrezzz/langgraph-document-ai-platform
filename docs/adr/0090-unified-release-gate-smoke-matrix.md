# ADR-0090: Unified release-gate smoke matrix

- Статус: Accepted
- Дата: 2026-04-29

## Контекст

После ADR-0088/0089 у платформы уже есть execution, quality, token и SLA метрики, но до этого они проверялись разрозненно через отдельные smoke scripts и ручные curl.

Для Increment 32 нужен единый gate-proof контракт:

- machine-readable pass/fail verdict;
- единая точка проверки retrieval/authoring/HITL/observability;
- configurable thresholds без изменения кода.

## Решение

1. Добавлен unified script `backend/scripts/smoke_release_gate.py` (+ `.sh/.ps1` wrappers).
2. Smoke поднимает API и выполняет последовательность:
   - optional knowledge indexing;
   - retrieval task + `events/summary`;
   - authoring task с HITL loop;
   - `tasks/observability/summary` и `hitl/observability/summary`.
3. Script строит checks matrix и печатает JSON:
   - `gate_status=pass|fail`;
   - `checks[]` со структурой `name/passed/expected/actual`;
   - `artifacts` со входными payloads для диагностики.
4. Пороговые проверки параметризуются через env/CLI:
   - `APP_RELEASE_GATE_MIN_EVENTS_TOTAL`;
   - `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS`;
   - `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES`;
   - `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES`;
   - `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS`.

## Последствия

Плюсы:

- release gate становится repeatable и CI-friendly;
- ручной stage/prod rehearsal получает детерминированный verdict;
- диагностика проблем упрощается за счет единого JSON proof payload.

Минусы:

- smoke по-прежнему интеграционный и зависит от runtime окружения (DB/env/gateways);
- при дальнейшем росте matrix может потребоваться разбиение на несколько профилей gate (fast/full/llm).
