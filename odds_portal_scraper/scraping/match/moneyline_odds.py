"""Scrape three-way moneyline odds."""

from __future__ import annotations

from typing import Dict, List

from playwright.async_api import Page

from ...logger import logger
from ..shared.activate_all_bookies_filter import activate_all_bookies_filter
from ..shared.dispatch_click import dispatch_click

MONEYLINE_BUTTON_SELECTOR = 'div.flex-center.bg-gray-medium'
ROW_SELECTOR = 'div[data-testid="over-under-expanded-row"]'
PERIOD_INDEX = {
    "fullTime": 0,
    "firstHalf": 1,
    "secondHalf": 2,
}


async def extract_moneyline_odds(page: Page, period: str, activate_all: bool = True) -> List[Dict[str, str | None]]:
    logger.info("scrapping odds for three way market (%s)", period)
    await page.wait_for_selector(MONEYLINE_BUTTON_SELECTOR)
    buttons = await page.locator(MONEYLINE_BUTTON_SELECTOR).element_handles()
    index = PERIOD_INDEX.get(period)
    if index is None or index >= len(buttons):
        raise ValueError(f"Unknown odd type: {period}")

    await dispatch_click(buttons[index])
    if activate_all:
        await activate_all_bookies_filter(page)
    await page.wait_for_selector('div[data-testid="odd-container"] p.odds-text')

    rows = await page.query_selector_all(ROW_SELECTOR)
    results: List[Dict[str, str | None]] = []
    for row in rows:
        if row is None:
            continue
        bookie = await row.query_selector('p[data-testid="outrights-expanded-bookmaker-name"]')
        bookmaker_name = (await bookie.text_content()).strip() if bookie else None

        odds_containers = await row.query_selector_all('div[data-testid="odd-container"]')
        odds_values: List[str | None] = []
        for container in odds_containers:
            if container is None:
                continue
            link = await container.query_selector('a.odds-link')
            paragraph = await container.query_selector('p.odds-text')
            text = None
            if link:
                text = (await link.text_content())
            elif paragraph:
                text = (await paragraph.text_content())
            odds_values.append(text.strip() if text else None)

        while len(odds_values) < 3:
            odds_values.append(None)

        results.append(
            {
                "bookMakerName": bookmaker_name,
                "hw": odds_values[0],
                "d": odds_values[1],
                "aw": odds_values[2],
            }
        )
    return results


__all__ = ["extract_moneyline_odds"]
