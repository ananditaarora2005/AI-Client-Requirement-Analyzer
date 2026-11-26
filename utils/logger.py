"""Structured logging with automatic secret redaction."""

import logging
import re
from typing import Pattern


_SECRET_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{12,}", re.IGNORECASE),
)


class SecretRedactingFilter(logging.Filter):
    """Mask potential API tokens before log messages are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        for pattern in _SECRET_PATTERNS:
            message = pattern.sub("[REDACTED_SECRET]", message)
        record.msg = message
        record.args = ()
        return True


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a configured logger instance with secret redaction enabled."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger
