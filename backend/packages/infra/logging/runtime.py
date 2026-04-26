from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

_RUNTIME_LOGGER_PREFIX = "langgraph.runtime"
_CONFIGURED_LOGGERS: set[str] = set()


def configure_runtime_logging(*, service: str, component: str) -> logging.Logger:
    """Configures a single-line stdout logger for structured runtime events."""

    logger_name = _build_logger_name(service=service, component=component)
    logger = logging.getLogger(logger_name)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False

    if logger_name not in _CONFIGURED_LOGGERS:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.handlers.clear()
        logger.addHandler(handler)
        _CONFIGURED_LOGGERS.add(logger_name)

    return logger


def serialize_log_payload(
    event: str,
    *,
    level: str = "INFO",
    service: str,
    component: str,
    **fields: Any,
) -> str:
    """Builds a JSON log line from runtime context and event fields."""

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.lower(),
        "service": service,
        "component": component,
        "event": event,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def log_runtime_event(
    event: str,
    *,
    service: str,
    component: str,
    level: str = "INFO",
    logger: logging.Logger | None = None,
    **fields: Any,
) -> None:
    """Emits a structured JSON runtime event."""

    resolved_logger = logger or configure_runtime_logging(service=service, component=component)
    line = serialize_log_payload(
        event,
        level=level,
        service=service,
        component=component,
        **fields,
    )
    resolved_logger.log(_resolve_log_method(level), line)


def _build_logger_name(*, service: str, component: str) -> str:
    return f"{_RUNTIME_LOGGER_PREFIX}.{service}.{component}"


def _resolve_log_level() -> int:
    raw = os.getenv("APP_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    return getattr(logging, raw, logging.INFO)


def _resolve_log_method(level: str) -> int:
    normalized = level.strip().upper() or "INFO"
    return getattr(logging, normalized, logging.INFO)
