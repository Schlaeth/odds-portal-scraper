"""Resolve all unique match links from a list page."""

from __future__ import annotations

from typing import List

from playwright.async_api import Page

from ...logger import logger

MATCH_ROW_SELECTOR = 'div[data-testid="game-row"]'


def _dedupe(seq):
    seen = set()
    result = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


async def collect_match_links(page: Page, limit: int | None = None) -> List[str]:
    logger.info("fetching match links")
    await page.wait_for_selector(MATCH_ROW_SELECTOR)
    links = await page.locator(f"{MATCH_ROW_SELECTOR} a").evaluate_all(
        "elements => elements.map(el => el.getAttribute('href')).filter(Boolean)"
    )
    unique_links = _dedupe(links)
    if isinstance(limit, int):
        return unique_links[:limit]
    return unique_links


__all__ = ["collect_match_links"]
