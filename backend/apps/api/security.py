from __future__ import annotations

import os
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from framework.security import ActorContext, AuthenticationRequiredError, AuthorizationError, RoleBasedAccessPolicy, parse_roles


def get_actor_context(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_actor_roles: Annotated[str | None, Header(alias="X-Actor-Roles")] = None,
) -> ActorContext:
    """Builds actor identity from standard API headers."""

    return ActorContext(
        actor_id=(x_actor_id or "").strip() or None,
        roles=parse_roles(x_actor_roles),
        auth_source="api_headers" if x_actor_id or x_actor_roles else "anonymous",
    )


def get_access_policy() -> RoleBasedAccessPolicy:
    return RoleBasedAccessPolicy(enabled=_env_flag("APP_AUTH_ENABLED", default=False))


def require_api_roles(*required_roles: str) -> Callable[[ActorContext, RoleBasedAccessPolicy], ActorContext]:
    def dependency(
        actor: ActorContext = Depends(get_actor_context),
        policy: RoleBasedAccessPolicy = Depends(get_access_policy),
    ) -> ActorContext:
        try:
            policy.require_any_role(actor, required_roles, resource=f"api:{'/'.join(required_roles)}")
        except AuthenticationRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except AuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return actor

    return dependency


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
