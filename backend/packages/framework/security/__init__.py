"""Shared security helpers for service boundaries."""

from framework.security.rbac import (
    ActorContext,
    AuthenticationRequiredError,
    AuthorizationError,
    RoleBasedAccessPolicy,
    parse_roles,
)

__all__ = [
    "ActorContext",
    "AuthenticationRequiredError",
    "AuthorizationError",
    "RoleBasedAccessPolicy",
    "parse_roles",
]
