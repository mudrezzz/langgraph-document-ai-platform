# ADR-0007: LangGraph runtime execution в BaseWorkflow

- Статус: Accepted
- Дата: 2026-04-17

## Контекст

Базовый workflow ранее был placeholder-реализацией без фактического graph runtime. Для соответствия архитектурному принципу "LangGraph как единый orchestration runtime" нужно перевести invoke/resume в runtime-модель графа.

## Решение

1. Расширить `BaseWorkflow`:
   - `compile()` строит LangGraph для invoke/resume путей;
   - `invoke()` и `resume()` выполняют compiled graph;
   - в fallback-режиме (если runtime недоступен) сохраняется совместимость.
2. Ввести явные extension points:
   - `execute(state)` — бизнес-логика invoke;
   - `execute_resume(state)` — бизнес-логика resume.
3. Перевести `RetrievalPackWorkflow` на `execute/execute_resume` вместо переопределения invoke/resume.

## Последствия

Плюсы:

- lifecycle workflow стал соответствовать LangGraph-first подходу;
- единая модель исполнения для новых workflow;
- проще расширять interrupt/resume и graph branches.

Минусы:

- требуется дополнительная интеграция checkpointer/persistence для production;
- увеличилась сложность базового слоя workflow по сравнению с placeholder.