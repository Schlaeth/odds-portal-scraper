"""Date/time helpers."""

from __future__ import annotations

from datetime import datetime

__all__ = ["current_timestamp"]


def current_timestamp() -> str:
    """Return the current datetime as YYYY-MM-DD HH:MM:SS."""

    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")
