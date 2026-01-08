"""Yield match data for every link discovered on the current list page."""

from __future__ import annotations

import random
from pathlib import Path
from typing import AsyncGenerator, Dict, Iterable

from playwright.async_api import Page

from ...logger import logger
from ..shared.set_odds_format import set_odds_format
from .collect_match_links import collect_match_items
from .scrape_match import scrape_match


def _resolve_throttle_delay(throttle) -> int:
    if throttle is None:
        return 0
    if isinstance(throttle, (int, float)):
        return max(0, int(throttle))
    min_delay = max(0, int(throttle.get("min", 0)))
    max_delay = max(min_delay, int(throttle.get("max", min_delay)))
    if min_delay == max_delay:
        return min_delay
    return random.randint(min_delay, max_delay)


async def _wait_for_throttle(page: Page, throttle) -> None:
    delay = _resolve_throttle_delay(throttle)
    if delay > 0:
        await page.wait_for_timeout(delay)


async def collect_match_data(
    page: Page,
    *,
    league_name: str,
    odds_format: str,
    limit: int | None = None,
    throttle=None,
    match_retry: Dict | None = None,
    activate_all_bookies: bool = True,
    skip_existing_dir: Path | None = None,
    over_under_range: tuple[float, float] | None = None,
) -> AsyncGenerator[Dict, None]:
    await set_odds_format(page, odds_format)
    items = await collect_match_items(page, limit, league_name=league_name)
    should_throttle = False

    for item in items:
        link = item["link"]
        if should_throttle:
            await _wait_for_throttle(page, throttle)
        should_throttle = True
        try:
            result = await scrape_match(
                page,
                link,
                league_name,
                {
                    "retry": match_retry,
                    "all_bookies": activate_all_bookies,
                    "skip_existing_dir": skip_existing_dir,
                    "over_under_range": over_under_range,
                    "section": item.get("section"),
                },
            )
            if result is None:
                continue
            yield result
        except Exception as exc:
            logger.exception("Error scraping %s, skipping match. Reason: %s", link, exc)


__all__ = ["collect_match_data"]
