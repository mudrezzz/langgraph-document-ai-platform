from __future__ import annotations

import re
from typing import Any

from framework.mcp.interfaces import IMcpService
from framework.security import ActorContext, AuthenticationRequiredError, AuthorizationError, RoleBasedAccessPolicy, parse_roles


_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_ALLOWED_OPERATION_SCOPES = {"read", "write", "action"}


class BaseFastMcpService(IMcpService):
    """Базовая реализация MCP-сервиса на FastMCP (скелет)."""

    def __init__(self, service_name: str, version: str = "0.1.0", *, service_scope: str | None = None) -> None:
        self._service_name = service_name
        self._version = version
        self._service_scope = service_scope or service_name.removesuffix("-mcp")
        self._tool_names: list[str] = []
        self._operation_scopes: dict[str, str] = {}
        self._tool_required_roles: dict[str, tuple[str, ...]] = {}
        self._access_policy = RoleBasedAccessPolicy(enabled=_env_flag("APP_AUTH_ENABLED", default=False))

    def register_tools(self) -> None:
        # Реальная регистрация будет добавлена после подключения FastMCP.
        return None

    def metadata(self) -> dict[str, Any]:
        return {
            "service_name": self._service_name,
            "version": self._version,
            "transport": "fastmcp",
            "service_scope": self._service_scope,
            "policy_version": "mcp-policy-v1",
            "tool_names": list(self._tool_names),
            "operation_scopes": dict(self._operation_scopes),
            "auth_policy": self._access_policy.policy_name,
            "tool_required_roles": {tool_name: list(roles) for tool_name, roles in self._tool_required_roles.items()},
            "input_validation": "pydantic_model_validate",
            "output_validation": "pydantic_response_model",
            "error_mapping": "value_error",
            "audit_payload_fields": ["service_name", "service_version", "tool_name", "operation_scope"],
        }

    def _register_toolset(
        self,
        tools: dict[str, Any],
        *,
        operation_scopes: dict[str, str] | None = None,
        required_roles: dict[str, tuple[str, ...] | list[str]] | None = None,
    ) -> dict[str, Any]:
        scopes = operation_scopes or {}
        role_policy = required_roles or {}
        unknown_scope_keys = set(scopes) - set(tools)
        if unknown_scope_keys:
            raise ValueError(f"Operation scopes reference unknown tools: {sorted(unknown_scope_keys)}")
        unknown_role_keys = set(role_policy) - set(tools)
        if unknown_role_keys:
            raise ValueError(f"Required roles reference unknown tools: {sorted(unknown_role_keys)}")

        for tool_name in tools:
            if not _TOOL_NAME_RE.match(tool_name):
                raise ValueError(f"Invalid MCP tool name: {tool_name}")

        resolved_scopes: dict[str, str] = {}
        resolved_roles: dict[str, tuple[str, ...]] = {}
        for tool_name in sorted(tools):
            scope = scopes.get(tool_name) or self._infer_operation_scope(tool_name)
            if scope not in _ALLOWED_OPERATION_SCOPES:
                raise ValueError(f"Invalid MCP operation scope '{scope}' for tool {tool_name}")
            resolved_scopes[tool_name] = scope
            roles = parse_roles(role_policy.get(tool_name, ()))
            resolved_roles[tool_name] = roles

        self._tool_names = sorted(tools)
        self._operation_scopes = resolved_scopes
        self._tool_required_roles = resolved_roles
        return tools

    def _operation_error(self, exc: Exception) -> ValueError:
        return ValueError(str(exc))

    def _authorize_tool(self, tool_name: str, *, actor: str | None = None, roles: list[str] | tuple[str, ...] | None = None) -> ActorContext:
        actor_context = ActorContext(
            actor_id=(actor or "").strip() or None,
            roles=parse_roles(roles),
            auth_source="mcp_payload" if actor or roles else "anonymous",
        )
        try:
            self._access_policy.require_any_role(
                actor_context,
                self._tool_required_roles.get(tool_name, ()),
                resource=f"{self._service_name}:{tool_name}",
            )
        except (AuthenticationRequiredError, AuthorizationError) as exc:
            raise self._operation_error(exc) from exc
        return actor_context

    @staticmethod
    def _infer_operation_scope(tool_name: str) -> str:
        if tool_name.startswith(("get_", "list_", "lookup_", "search_", "find_", "compare_")):
            return "read"
        if tool_name.startswith(("upsert_", "write_", "publish_", "set_", "submit_")):
            return "write"
        return "action"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = __import__("os").getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
