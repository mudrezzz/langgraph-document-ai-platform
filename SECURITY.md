# Security Policy

## 1. Supported scope

Этот документ покрывает backend/framework слой и сервисные границы:

- `backend/apps/api`
- `backend/apps/mcp_*`
- `backend/packages/framework`
- `backend/packages/application`
- `backend/packages/infra`

## 2. Reporting vulnerabilities

Пожалуйста, не публикуйте детали уязвимости в открытом issue до исправления.

При report укажите:

1. Описание уязвимости и impact.
2. Компонент/файл/endpoint/tool.
3. Шаги воспроизведения.
4. Возможный mitigation/workaround.

## 3. Disclosure flow

1. Maintainers подтверждают получение report.
2. Выполняется triage severity и scope.
3. Готовится fix + тест/документация.
4. После выпуска исправления публикуется disclosure summary.

## 4. Security boundaries and limitations

- RBAC boundary активируется только при `APP_AUTH_ENABLED=true`.
- Без включенного auth API/MCP sensitive operations не имеют role enforcement.
- Secrets должны передаваться через env/secret-store и не коммититься в репозиторий.

## 5. Recommended hardening baseline

1. `APP_RUNTIME_PROFILE=prod`
2. `APP_AUTH_ENABLED=true`
3. отдельные роли для `template_admin`, `reviewer`, `repository_writer`, `artifact_writer`, `config_admin`
4. регулярный прогон `smoke_release_gate` и review observability/SLA breaches
