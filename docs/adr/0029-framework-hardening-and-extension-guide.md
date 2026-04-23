# ADR-0029: Framework hardening и extension guide

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

После `Increment 23` framework layer уже содержит основные contracts и runtime primitives:

- agents/tools/workflows/rag/stores/db/models/hitl/mcp;
- LangGraph-backed `BaseWorkflow`;
- Postgres persistence adapters;
- FastAPI/MCP service boundaries;
- async authoring и iterative HITL.

Следующие инкременты будут расширять ingestion, retrieval и authoring домены. Без явного extension guide и contract tests новые доменные реализации могут начать обходить framework boundaries и закреплять временные shortcuts.

## Решение

1. Зафиксировать отдельный документ `docs/framework_extension_guide.md`.
2. Добавить root backlog `BACKLOG.md` как рабочий план завершения backend/framework части.
3. Усилить unit coverage для базовых framework contracts:
   - agents;
   - tools;
   - MCP service metadata;
   - repository factory/unit of work;
   - base stores.
4. Считать release go/no-go scripts обязательным acceptance demo harness для следующих инкрементов.

## Последствия

Плюсы:

- новые workflows/tools/MCP services получают единый путь добавления;
- framework layer становится проверяемым contract surface, а не только набором skeleton-классов;
- demo сценарии закреплены как regression harness для ручной проверки.

Минусы:

- увеличивается объем документации, которую нужно обновлять при каждом инкременте;
- часть tests фиксирует текущий минимальный behavior skeleton и потребует осознанного обновления при развитии framework.
