# Agent Examples Demo Program (In-Process)

Дата обновления: 2026-04-30  
Статус: In Progress (DOC-030 completed; DOC-031..DOC-035 pending)

## 1. Product Goal

Сделать `agent_examples/` отдельным продуктовым входом для внешнего разработчика.

Ключевой UX:

1. Открыть одну папку.
2. Прочитать Python-код агента без погружения во внутренности framework.
3. Запустить `main.py` одной командой.
4. Изменить несколько файлов (`prompts/config/tools`) и быстро получить своего агента.

## 2. Problem Statement

Текущие примеры в основном показывают API-driven интеграционный путь (`framework as service`).

Для сценария "создаю нового агента на framework" нужен другой формат:

- in-process composition поверх framework contracts;
- демонстрация кода `agent/workflow/tools` как библиотеки;
- минимальная зависимость от API-boundary/transport слоя.

## 3. Non-Negotiable Principles

1. Primary path = in-process framework usage, не HTTP-клиент.
2. Один pattern = одна самодостаточная подпапка с одинаковой структурой.
3. `python .../main.py` должен быть основным способом запуска.
4. Быстрый deterministic режим обязателен для onboarding.
5. Production-like режим должен быть опциональным, но документированным.
6. Каждый пример имеет локальные тесты и ожидаемый output proof.

## 4. Target Information Architecture

```text
agent_examples/
  README.md
  getting_started.md
  design_patterns/
    README.md
    retrieval_first.md
    authoring_first.md
    hitl_gate.md
    async_batch.md
    mcp_tool_facade.md
  patterns/
    retrieval_first/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
    authoring_first/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
    hitl_gate/
      README.md
      main.py
      agent.py
      workflow.py
      tools.py
      prompts.py
      config.py
      sample_input/
      expected_output/
      tests/
  shared/
    runtime_profiles.py
    fixtures.py
    assertions.py
    output_render.py
  tests/
    test_examples_contracts.py
```

## 5. Pattern Library Scope

## 5.1 P0 Patterns

1. Retrieval-First Agent
2. Authoring-First Agent
3. HITL Gate Pattern

## 5.2 P1 Patterns

1. Async Batch Pattern
2. MCP Tool Facade Pattern

## 6. Pattern Blueprint Contract

Каждый pattern обязан содержать:

1. `agent.py`: composition root и публичный run-путь.
2. `workflow.py`: orchestration steps/state transitions.
3. `tools.py`: локальные tools и typed I/O contracts.
4. `prompts.py`: prompt templates и минимальный explanation.
5. `config.py`: deterministic/prod-like profiles.
6. `main.py`: CLI запуск и печать результата.
7. `README.md`: use case, run steps, expected output, extension points.
8. `tests/`: unit + smoke для текущего pattern.
9. `expected_output/`: эталонный результат для быстрой ручной проверки.

## 7. Execution Modes

1. Quick deterministic mode:
   - запуск без внешних сервисов по умолчанию;
   - предсказуемый output для onboarding и CI.
2. Production-like mode:
   - включает инфраструктурные зависимости;
   - используется для parity-check и расширенной проверки.

## 8. Test Strategy

1. Pattern Unit Tests:
   - проверка логики workflow/tools/prompt shaping.
2. Pattern Smoke Tests:
   - запуск `main.py` end-to-end и проверка expected output.
3. Determinism Tests:
   - одинаковый вход => одинаковый output в quick mode.
4. Structure Contracts:
   - все pattern-папки содержат обязательные файлы.
5. Docs Contracts:
   - команды в `README` валидны и воспроизводимы.
6. CI lanes:
   - fast lane: unit + contracts;
   - full lane: smoke всех pattern demos.

## 9. Implementation Roadmap

## 9.1 P0 (must-have)

1. Replatform `retrieval_first` в in-process style.
2. Replatform `authoring_first` в in-process style.
3. Replatform `hitl_gate` в in-process style.
4. Унифицировать shared helpers для pattern folders.
5. Подключить examples contract tests и dry/smoke проверку в CI path.
6. Обновить root README + developer guide как primary entrypoint на `agent_examples/`.

## 9.2 P1 (next)

1. Добавить `async_batch` pattern demo.
2. Добавить `mcp_tool_facade` pattern demo.
3. Добавить шаблон `create-your-agent` (copy-and-modify starter kit).

## 10. Definition of Done (per pattern)

1. Один command-run из корня репозитория.
2. Наглядный, прокомментированный Python-код.
3. Нет необходимости читать framework internals для понимания flow.
4. Локальный smoke test проходит стабильно.
5. Есть expected output proof и инструкция проверки.
6. Обновлены docs routes и `docs/DOCS_BACKLOG.md`.

## 11. Risks and Mitigations

1. Риск: примеры снова станут API wrappers.
   - Mitigation: review checklist запрещает transport-only implementation как primary path.
2. Риск: сложный setup ухудшит onboarding.
   - Mitigation: обязательный deterministic mode.
3. Риск: примеры устареют относительно runtime.
   - Mitigation: structure + smoke tests в CI.
4. Риск: дублирование логики между patterns.
   - Mitigation: ограниченный `shared/` слой + strict template contract.

## 12. Governance and Ownership

1. Любой PR с изменением `agent_examples/*` обновляет:
   - `agent_examples/README.md`
   - соответствующий pattern `README.md`
   - `docs/DOCS_BACKLOG.md`
2. До слияния обязательны:
   - локальный fast lane;
   - проверка links/contracts;
   - проверка команд из docs.
