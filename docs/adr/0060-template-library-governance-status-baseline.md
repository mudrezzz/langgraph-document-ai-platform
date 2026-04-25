# ADR-0060: Template library governance status baseline

- Статус: Accepted
- Дата: 2026-04-25

## Контекст

После ADR-0057..0059 template library уже стала persisted service boundary с HTTP API и MCP tools. Но все версии шаблонов оставались равноправными: authoring по умолчанию мог взять последнюю сохраненную version, даже если это был черновик. Для production authoring этого недостаточно.

Нужен минимальный governance layer, не превращающийся в большой template management subsystem: distinction между draft и published versions, плюс понятное правило резолвинга шаблона по умолчанию.

## Решение

1. Ввести минимальный lifecycle статусов reusable template version:
   - `draft`;
   - `published`.
2. Добавить `status` в persisted template record, API response и MCP response.
3. Добавить отдельную операцию публикации версии:
   - HTTP: `POST /api/v1/templates/{template_id}/publish`;
   - MCP tool: `publish_template`.
4. Оставить `upsert` совместимым:
   - по умолчанию version создается как `draft`;
   - при явном `status=published` upsert завершаетcя publish шагом.
5. Изменить default authoring-resolution:
   - если `task_context.template_version` не передан, authoring берет только `published` template;
   - если version передана явно, разрешено читать конкретную version независимо от статуса;
   - inline `template_payload` по-прежнему имеет наивысший приоритет.

## Последствия

Плюсы:

- authoring по умолчанию перестает случайно использовать незапубликованные drafts;
- шаблоны получают минимальный production-compatible governance layer без тяжелого approval workflow;
- HTTP API, MCP и authoring path используют один и тот же status-aware persistence boundary.

Минусы:

- baseline lifecycle затем расширен до `draft|published|deprecated|archived` и explicit status transitions в ADR-0063;
- detail publish policy для active published-version уточнен в ADR-0062;
- approval workflow и RBAC по-прежнему остаются вне текущего scope.
