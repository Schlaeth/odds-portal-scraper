"""Discover pagination for a historic season page."""

from __future__ import annotations

from typing import List

from playwright.async_api import Page

from ...logger import logger


async def discover_season_pages(page: Page, season_url: str) -> List[str]:
    await page.goto(season_url, wait_until="domcontentloaded")
    page_numbers: List[str] = []
    try:
        await page.wait_for_selector("a.pagination-link", timeout=30_000)
        page_numbers = await page.locator("a.pagination-link").evaluate_all(
            "elements => elements.map(el => el.textContent && el.textContent.trim()).filter(Boolean).filter(text => text.toLowerCase() !== 'next')"
        )
    except Exception:
        logger.info("no pagination detected for %s", season_url)

    base_url = page.url().split('#')[0]
    if not page_numbers:
        return [base_url]

    unique_numbers = list(dict.fromkeys(page_numbers))
    return [f"{base_url}#/page/{number}" for number in unique_numbers]


__all__ = ["discover_season_pages"]
