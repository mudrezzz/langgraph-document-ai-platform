# ADR-0040: WorkflowFactory with DI-friendly builders

- Status: Accepted
- Date: 2026-04-24

## Context

The primary `WorkflowFactory` registered only the class type and created the workflow via an empty constructor. This was sufficient for the contract skeleton, but broke the reusable framework boundary: production workflows require injected retrievers, stores, gateways, event sinks, policies and runtime context.

Also, duplicate registration silently erased the previous workflow, and missing lookup was thrown with the usual `KeyError`, which is not suitable for bootstrap diagnostics.

## Solution

1. `WorkflowFactory` supports two registration methods:
- `register("key", WorkflowClass)` for backward compatibility;
- `register_builder("key", builder, metadata={...})` for DI-friendly assembly.
2. `build("key", **dependencies)` passes dependencies to the registered builder.
3. Registration is stored as `WorkflowRegistration`:
   - `key`;
   - `builder`;
   - `metadata`.
4. Duplicate registration is disabled by default and raises `WorkflowRegistrationError`.
5. Conscious replacement requires `replace=True`.
6. Missing lookup raises `WorkflowNotRegisteredError`.
7. Factory exposes:
   - `has(key)`;
   - `list_workflows()`;
   - `metadata(key)`.

## Consequences

Pros:

- workflow bootstrap can remain in the domain/application layer without a service locator;
- framework contract now supports dependencies without changing application services;
- capability metadata can be used in future MCP/discovery layers;
- registry errors have become explicit and testable.

Cons:

- the factory does not yet validate the runtime Protocol result of the builder, so as not to require eager instantiation;
- metadata schema remains a free `dict` until a common capability registry appears.
