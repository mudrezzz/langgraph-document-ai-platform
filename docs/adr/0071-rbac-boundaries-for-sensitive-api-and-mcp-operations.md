# ADR 0071: RBAC Boundaries For Sensitive API And MCP Operations

Дата: 2026-04-27
Статус: Accepted

## Контекст

К началу Increment 30 платформа уже имела production-like service boundaries:

- FastAPI endpoints для template governance и authoring HITL;
- FastMCP services для repository, artifact writer, template library, review approval и configuration library;
- unified MCP metadata/policy baseline через `BaseFastMcpService`.

Но эти boundaries были operationally открыты: `operation_scope` уже классифицировал tool как `read|write|action`, однако runtime enforcement отсутствовал. Это означало, что sensitive операции (`publish_template`, `set_template_status`, `submit_hitl_review`, `upsert_config`, `write_artifact`, `upsert_document`) не имели общей минимальной authorization boundary.

Для текущей стадии не нужен полноценный IAM/SSO слой, но нужен production-compatible baseline, который:

- отделяет read paths от write/approval-sensitive paths;
- работает одинаково для API и MCP;
- не ломает текущие контракты и smoke paths при выключенном auth;
- дает понятный upgrade path к будущему auth/audit envelope.

## Решение

Вводится минимальный shared RBAC baseline:

1. Добавлен framework-level security helper `framework.security.rbac`.
2. Введены:
   - `ActorContext`;
   - `RoleBasedAccessPolicy`;
   - ошибки `AuthenticationRequiredError` и `AuthorizationError`;
   - helper `parse_roles(...)`.
3. RBAC enforcement включается env-флагом `APP_AUTH_ENABLED=true|false`.
4. При `APP_AUTH_ENABLED=false` policy не блокирует текущие flows и сохраняет backward compatibility.
5. API boundary использует стандартные headers:
   - `X-Actor-Id`;
   - `X-Actor-Roles`.
6. MCP boundary использует actor context в typed payload fields:
   - `actor`;
   - `roles`.
7. `BaseFastMcpService` расширен auth-aware metadata и enforcement helper:
   - `auth_policy`;
   - `tool_required_roles`;
   - `_authorize_tool(...)`.
8. Enforcement добавлен только на sensitive operations, read operations остаются открытыми.

## Матрица ролей

Минимальный baseline в этом срезе:

- `template_admin`:
  - API: `PUT /api/v1/templates/{template_id}`;
  - API: `POST /api/v1/templates/{template_id}/publish`;
  - API: `POST /api/v1/templates/{template_id}/status`;
  - MCP: `upsert_template`, `publish_template`, `set_template_status`.
- `reviewer`:
  - API: `POST /api/v1/tasks/{task_id}/hitl/submit`;
  - MCP: `submit_hitl_review`.
- `config_admin`:
  - MCP: `upsert_config`.
- `artifact_writer`:
  - MCP: `write_artifact`.
- `repository_writer`:
  - MCP: `upsert_document`.
- admin override:
  - `admin` или `platform_admin` bypass-ят role-specific checks.

## Последствия

Плюсы:

- sensitive operations теперь имеют минимальную, но реальную protection boundary;
- API и MCP используют один и тот же framework-level policy primitive;
- metadata FastMCP теперь отражает не только scope, но и required roles;
- future auth/audit hardening можно строить поверх уже нормализованного actor context.

Минусы:

- это не полноценный identity layer: нет tokens, SSO, tenant boundaries и signed claims;
- actor context в MCP payload остается trust-based до появления внешнего auth proxy;
- часть write endpoints API пока еще intentionally не закрыта этим срезом, если они не относятся к template governance/HITL boundary.

## Почему не полноценный IAM сейчас

Полноценная auth platform добавила бы много инфраструктурной сложности и отвлекла бы от цели Increment 30: довести reusable service boundary до production-like baseline. Для текущего этапа важнее зафиксировать:

- где enforcement должен жить;
- как нормализуется actor context;
- какие операции считаются sensitive.

Это дает безопасный минимальный operational envelope без premature enterprise integration.

## Что дальше

Следующие security slices могут расширить baseline до:

- signed auth headers / API gateway integration;
- audit records с actor identity и authorization decision;
- per-endpoint rate limits;
- service-to-service auth для worker/MCP runtime;
- richer role sets и tenant/project-scoped permissions.
