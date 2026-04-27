from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class AuthenticationRequiredError(PermissionError):
    """Raised when a protected operation has no actor context."""


class AuthorizationError(PermissionError):
    """Raised when actor roles do not satisfy the access policy."""


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Normalized actor identity used across API and MCP boundaries."""

    actor_id: str | None = None
    roles: tuple[str, ...] = ()
    auth_source: str = "anonymous"

    @property
    def is_authenticated(self) -> bool:
        return bool(self.actor_id)


def parse_roles(raw_roles: str | Iterable[str] | None) -> tuple[str, ...]:
    """Normalizes role input from headers or MCP payloads."""

    if raw_roles is None:
        return ()
    if isinstance(raw_roles, str):
        items = raw_roles.split(",")
    else:
        items = list(raw_roles)

    normalized: list[str] = []
    for item in items:
        role = str(item).strip().lower()
        if role and role not in normalized:
            normalized.append(role)
    return tuple(normalized)


class RoleBasedAccessPolicy:
    """Minimal RBAC policy with optional enforcement for service boundaries."""

    def __init__(self, *, enabled: bool = False, admin_roles: Iterable[str] = ("admin", "platform_admin")) -> None:
        self._enabled = enabled
        self._admin_roles = frozenset(parse_roles(admin_roles))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def policy_name(self) -> str:
        return "rbac-v1" if self._enabled else "disabled"

    def require_any_role(
        self,
        actor: ActorContext,
        required_roles: Iterable[str],
        *,
        resource: str,
    ) -> None:
        normalized_required = frozenset(parse_roles(required_roles))
        if not self._enabled or not normalized_required:
            return
        if not actor.is_authenticated:
            raise AuthenticationRequiredError(f"Authentication required for {resource}")

        actor_roles = frozenset(actor.roles)
        if actor_roles & self._admin_roles:
            return
        if actor_roles & normalized_required:
            return

        required_label = ", ".join(sorted(normalized_required))
        raise AuthorizationError(
            f"Actor {actor.actor_id} lacks required role for {resource}: {required_label}"
        )
