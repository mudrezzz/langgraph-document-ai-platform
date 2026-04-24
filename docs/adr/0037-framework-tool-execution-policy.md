# ADR-0037: Framework tool execution policy

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

После `Increment 25` framework layer имел базовые contracts для agents/tools/workflows, но `ToolExecutor` оставался минимальным lookup-wrapper поверх `ToolRegistry`. Целевая архитектура требует, чтобы tools можно было безопасно использовать внутри agents/workflows/MCP с единым lifecycle:

- retry;
- timeout accounting;
- idempotency;
- audit;
- propagation task/node/correlation metadata.

Если оставить эти concerns в application/domain services, разные workflows начнут реализовывать retry/idempotency/audit по-разному.

## Решение

1. Расширить `ToolContext` полями:
   - `node_name`;
   - `correlation_id`;
   - `idempotency_key`.
2. Добавить `ToolExecutionPolicy`:
   - `max_attempts`;
   - `timeout_sec`;
   - `idempotency_enabled`;
   - `audit_enabled`.
3. Добавить audit contract:
   - `ToolExecutionRecord`;
   - `ToolExecutionAuditSink`;
   - `InMemoryToolExecutionAuditSink` для unit/dev сценариев.
4. Сохранить обратную совместимость:
   - `ToolExecutor(registry).execute(tool_name, command, context)` остается основным вызовом;
   - без explicit policy поведение остается одноразовым execution без обязательного audit sink.
5. Зафиксировать contract tests на retry/idempotency/audit behavior.

## Последствия

Плюсы:

- framework tools получили единый runtime behavior без изменения application services;
- будущие agents/workflows/MCP services смогут использовать один policy surface;
- idempotency и audit metadata теперь стандартизированы на уровне framework context.

Минусы:

- timeout пока является accounting/detection после sync tool call, а не preemptive cancellation;
- idempotency cache локален для экземпляра `ToolExecutor`; production persistence policy будет добавляться отдельным slice при unified execution plane.
