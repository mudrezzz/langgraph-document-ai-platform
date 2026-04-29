# ADR-0091: Final release decision contract

- Статус: Accepted
- Дата: 2026-04-29

## Контекст

После ADR-0090 появился unified release-gate smoke с machine-readable checks, но финальное решение о выпуске все еще собиралось вручную из нескольких шагов:

- запуск smoke gate;
- запуск полного pytest gate;
- ручная интерпретация результатов для handoff.

Нужен единый orchestrator, который формирует официальный release verdict.

## Решение

1. Добавлен финальный orchestrator:
   - `backend/scripts/release_decision_gate.py` + wrappers `.sh/.ps1`.
2. Orchestrator выполняет:
   - `smoke_release_gate` (profile-aware);
   - full pytest gate (по умолчанию);
   - сбор unified release decision payload.
3. Unified payload сохраняется в:
   - `backend/.release_gate/release_decision_<timestamp>.json`;
   - `backend/.release_gate/release_decision_<timestamp>.md`.
4. Contract payload:
   - `status: pass|fail`;
   - `decision_reason`;
   - `failed_checks[]` (из smoke gate);
   - `smoke_release_gate` summary;
   - `test_gate_summary`;
   - `profile`, `commit_sha`, `branch`, `timestamp_utc`.

## Последствия

Плюсы:

- появляется единый source-of-truth release verdict для stage/prod handoff;
- снижается риск человеческой ошибки в финальном gate;
- JSON/Markdown артефакты упрощают аудит и ретроспективу релизных решений.

Минусы:

- orchestrator остается интеграционно-зависимым от runtime окружения;
- при долгом full gate может понадобиться profile-specific split (fast/full) в будущем.
