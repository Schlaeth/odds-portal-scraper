"""Discover pagination for a historic season page."""

from __future__ import annotations

import re
from typing import List

from playwright.async_api import Page

from ...logger import logger


async def discover_season_pages(page: Page, season_url: str, *, start_page: int = 1) -> List[str]:
    if start_page < 1:
        raise ValueError("start_page must be greater than or equal to 1")

    await page.goto(season_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")
    # Allow client-side router to render pagination controls.
    await page.wait_for_timeout(2_000)
    base_url = page.url.split('#')[0]

    selectors = [
        "a[href*='#/page/']",
        "a[href*='?page=']",
        "a.pagination-link",
        "div.pagination a",
        "nav.pagination a",
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
        if start_page > 1:
            logger.info("start_page %s skips %s because no pagination was found", start_page, season_url)
            return []
        return [base_url]

    unique_numbers = list(dict.fromkeys(page_numbers))
    filtered = [number for number in unique_numbers if int(number) >= start_page]

    if not filtered:
        logger.info(
            "start_page %s filtered out all discovered pages for %s (pages found: %s)",
            start_page,
            season_url,
            ", ".join(unique_numbers),
        )
        return []

    return [f"{base_url}#/page/{number}" for number in filtered]


__all__ = ["discover_season_pages"]
