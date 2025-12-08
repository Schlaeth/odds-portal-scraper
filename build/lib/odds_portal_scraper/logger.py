"""Logging helpers for the scraper."""

from __future__ import annotations

import logging
from typing import Optional

try:
    from rich.logging import RichHandler
except ImportError:  # pragma: no cover - rich is part of main deps but guard anyway
    RichHandler = None  # type: ignore

_LOGGER_NAME = "odds_portal_scraper"


def _build_handler() -> logging.Handler:
    if RichHandler is None:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        return handler

    return RichHandler(show_path=False, rich_tracebacks=True)


def configure_logger(level: Optional[str] = None) -> logging.Logger:
    """Configure and return the shared logger instance."""

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        # Reconfigure level only when requested.
        if level:
            logger.setLevel(level.upper())
        return logger

    resolved_level = (level or "INFO").upper()
    logger.setLevel(resolved_level)
    handler = _build_handler()
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    if not isinstance(handler, RichHandler):
        handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logger()

__all__ = ["logger", "configure_logger"]
