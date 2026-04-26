# ADR-0068: Review/Approval MCP Boundary

- Статус: Accepted
- Дата: 2026-04-26

## Контекст

К началу Increment 30 у платформы уже есть:

- authoring/HITL API (`GET /api/v1/tasks/{task_id}/hitl`, `POST /api/v1/tasks/{task_id}/hitl/submit`);
- persistence/read-model слой reviewer действий (`app.hitl_actions`);
- reviewer aggregates endpoint `GET /api/v1/hitl/observability/summary`;
- MCP boundaries для retrieval, repository, artifact writer и template library.

Но reviewer/manual approval path по-прежнему был доступен только через HTTP API. Для production-like MCP surface нужен минимальный boundary, через который внешний агент или оператор может:

- посмотреть текущий HITL статус задачи;
- прочитать историю reviewer действий;
- отправить reviewer решение;
- получить агрегированную сводку reviewer нагрузки и решений.

При этом нельзя дублировать existing authoring/HITL архитектуру или вводить отдельный reviewer-specific runtime stack.

## Решение

1. Добавить отдельный FastMCP service `review-approval-mcp`.
2. Вынести typed MCP contracts в `schemas.mcp.review_approval`.
3. Дать сервису минимальный набор tools:
   - `get_hitl_status`;
   - `list_hitl_actions`;
   - `submit_hitl_review`;
   - `get_hitl_observability_summary`.
4. Реализовать boundary поверх existing application/read-model слоя:
   - `AuthoringApplicationService.hitl_status(...)`;
   - `AuthoringApplicationService.list_hitl_actions(...)`;
   - `AuthoringApplicationService.submit_hitl(...)`;
   - `AuthoringApplicationService.hitl_observability_summary(...)`.
5. Для submit path переиспользовать existing `AuthoringAsyncDispatcher`, чтобы MCP и HTTP path ставили continuation в один и тот же async plane.
6. Ошибки internal application layer маппить в MCP-friendly `ValueError`, не раскрывая internal state payload shape как публичный контракт.

## Последствия

Плюсы:

- MCP surface теперь покрывает не только retrieval/repository/artifact/template операции, но и reviewer/HITL decision path;
- reviewer tools используют тот же production-compatible orchestration и тот же persistence/read-model слой, что и HTTP boundary;
- не появляется новая параллельная review-specific архитектура.

Минусы:

- boundary пока не добавляет unified auth/RBAC/rate-limit политику для MCP сервисов;
- observability MCP tool повторно использует current read-model aggregates и пока не решает SLA buckets/day-week dashboards;
- manual approval path все еще зависит от existing authoring task semantics (`waiting_human`, iteration limits, idempotency rules).
