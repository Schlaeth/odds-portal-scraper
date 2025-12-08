"""Helper to dispatch synthetic clicks via Playwright."""

from __future__ import annotations

from typing import Any, Optional

from playwright.async_api import ElementHandle, Locator

Target = ElementHandle | Locator | None


async def dispatch_click(target: Target, options: Optional[dict[str, Any]] = None) -> None:
    if target is None:
        return

    await target.evaluate(
        """
        (node, overrides) => {
            const defaults = { bubbles: true, cancelable: true, view: window };
            const event = new MouseEvent('click', { ...defaults, ...(overrides || {}) });
            node.dispatchEvent(event);
        }
        """,
        options or {},
    )


__all__ = ["dispatch_click"]
