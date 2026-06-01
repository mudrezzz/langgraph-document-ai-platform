# Security Policy

## 1. Supported scope

This document covers the backend/framework layer and service boundaries:

- `backend/apps/api`
- `backend/apps/mcp_*`
- `backend/packages/framework`
- `backend/packages/application`
- `backend/packages/infra`

## 2. Reporting vulnerabilities

Please do not publish details of the vulnerability in an open issue until it is fixed.

When reporting, specify:

1. Description of the vulnerability and impact.
2. Component/file/endpoint/tool.
3. Reproduction steps.
4. Possible mitigation/workaround.

## 3. Disclosure flow

1. Maintainers confirm receipt of the report.
2. Maintainers triage severity and scope.
3. A fix is prepared together with tests/documentation updates.
4. After the release of the correction, a disclosure summary is published.

## 4. Security boundaries and limitations

- RBAC boundary is activated only when `APP_AUTH_ENABLED=true`.
- Without auth enabled, API/MCP sensitive operations do not have role enforcement.
- Secrets must be provided via env/secret-store and never committed to the repository.

## 5. Recommended hardening baseline

1. `APP_RUNTIME_PROFILE=prod`
2. `APP_AUTH_ENABLED=true`
3. separate roles for `template_admin`, `reviewer`, `repository_writer`, `artifact_writer`, `config_admin`
4. regular run `smoke_release_gate` and review observability/SLA breaches
