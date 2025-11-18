"""Discover pagination for a historic season page."""

from __future__ import annotations

import re
from typing import List

from playwright.async_api import Page

from ...logger import logger


async def discover_season_pages(page: Page, season_url: str) -> List[str]:
    await page.goto(season_url, wait_until="domcontentloaded")
    # Allow client-side router to render pagination controls.
    await page.wait_for_timeout(1_000)
    base_url = page.url.split('#')[0]

    selectors = [
        "a[href*='#/page/']",
        "a[href*='?page=']",
        "a.pagination-link",
    ]
    page_numbers: List[str] = []
    debug_samples: list[str] = []

    for selector in selectors:
        try:
            anchors = await page.locator(selector).evaluate_all(
                "elements => elements.map(el => ({ href: el.getAttribute('href') || '', text: (el.textContent || '').trim() }))"
            )
        except Exception:
            continue

        for anchor in anchors:
            href = anchor.get("href", "")
            text = anchor.get("text", "")

            if text.lower() == "next":
                continue

            if len(debug_samples) < 5:
                debug_samples.append(f"{selector} => href='{href}' text='{text}'")

            if match := re.search(r"(?:#/page/|\?page=)(\d+)", href, re.IGNORECASE):
                page_numbers.append(match.group(1))
                continue

            if text.isdigit():
                page_numbers.append(text)

    if not page_numbers:
        # Fallback: scan rendered HTML for page markers the selectors might have missed.
        html = await page.content()
        page_numbers.extend(re.findall(r"(?:#/page/|\?page=)(\d+)", html, re.IGNORECASE))

    if not page_numbers:
        if debug_samples:
            logger.info("no pagination detected for %s; sample anchors: %s", season_url, "; ".join(debug_samples))
        else:
            logger.info("no pagination detected for %s (no pagination anchor samples found)", season_url)
        return [base_url]

    unique_numbers = list(dict.fromkeys(page_numbers))
    return [f"{base_url}#/page/{number}" for number in unique_numbers]


__all__ = ["discover_season_pages"]
