from __future__ import annotations

import logging
from typing import Any

from app.config.settings import Settings

_RESERVED_LOG_KEYS = {
    "token",
    "password",
    "private_key",
    "secret",
    "authorization",
    "api_key",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in _RESERVED_LOG_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return type(value)(_redact(item) for item in value)
    return value


class ContextLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds safe structured context to every record."""

    def process(self, msg: Any, kwargs: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        context = dict(self.extra)
        context.update(kwargs.pop("extra", {}) or {})
        return msg, {**kwargs, "extra": _redact(context)}


def configure_logging(settings: Settings) -> None:
    """Configure consistent console logging for local and container execution."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )


def get_logger(name: str, **context: Any) -> ContextLoggerAdapter:
    return ContextLoggerAdapter(logging.getLogger(name), _redact(context))
