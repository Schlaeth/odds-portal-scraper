"""Ensure the "All" filter is active before scraping odds."""

from __future__ import annotations

from playwright.async_api import Page

from ...logger import logger
from .dispatch_click import dispatch_click


async def activate_all_bookies_filter(page: Page) -> None:
    selector = 'div[data-testid="bookies-filter-nav"] [data-testid="all"]'
    try:
        button = page.locator(selector)
        await dispatch_click(button)
        logger.info("All bookies filter activated")
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("Unable to activate all bookies filter: %s", exc)


__all__ = ["activate_all_bookies_filter"]
