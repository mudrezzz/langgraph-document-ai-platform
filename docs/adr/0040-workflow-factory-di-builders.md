# ADR-0040: WorkflowFactory с DI-friendly builders

- Статус: Accepted
- Дата: 2026-04-24

## Контекст

Первичная `WorkflowFactory` регистрировала только class type и создавала workflow через empty constructor. Это было достаточно для contract skeleton, но ломало reusable framework boundary: production workflows требуют injected retrievers, stores, gateways, event sinks, policies и runtime context.

Также duplicate registration молча перетирал предыдущий workflow, а missing lookup падал обычным `KeyError`, что плохо подходит для bootstrap диагностики.

## Решение

1. `WorkflowFactory` поддерживает два способа регистрации:
   - `register("key", WorkflowClass)` для обратной совместимости;
   - `register_builder("key", builder, metadata={...})` для DI-friendly assembly.
2. `build("key", **dependencies)` передает dependencies в зарегистрированный builder.
3. Registration хранится как `WorkflowRegistration`:
   - `key`;
   - `builder`;
   - `metadata`.
4. Duplicate registration запрещен по умолчанию и поднимает `WorkflowRegistrationError`.
5. Осознанная замена требует `replace=True`.
6. Missing lookup поднимает `WorkflowNotRegisteredError`.
7. Factory exposes:
   - `has(key)`;
   - `list_workflows()`;
   - `metadata(key)`.

## Последствия

Плюсы:

- workflow bootstrap может оставаться в domain/application layer без service locator;
- framework contract теперь поддерживает dependencies без изменения application services;
- capability metadata можно использовать в будущих MCP/discovery слоях;
- ошибки registry стали явными и тестируемыми.

Минусы:

- factory пока не валидирует runtime Protocol результат builder-а, чтобы не требовать eager instantiation;
- metadata schema остается свободным `dict`, пока не появился общий capability registry.
