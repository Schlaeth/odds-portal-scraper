"""Switch odds format on the odds portal page."""

from __future__ import annotations

from typing import Optional

from playwright.async_api import Locator, Page

from ...constants import ODDS_FORMAT_MAP
from ...logger import logger
from .dispatch_click import dispatch_click

BUTTON_SELECTORS = (
    "button",
    "div.group > button.gap-2",
    "button[class*='gap']",
)


async def _locate_odds_button(page: Page) -> Optional[Locator]:
    for selector in BUTTON_SELECTORS:
        try:
            locator = page.locator(selector)
            await locator.first.wait_for(timeout=3_000)
            return locator.first
        except Exception:
            continue
    return None


async def set_odds_format(page: Page, format_key: str) -> None:
    chosen = ODDS_FORMAT_MAP.get(format_key.lower())
    if not chosen:
        raise ValueError(f"format '{format_key}' is not supported")

    await page.set_viewport_size({"width": 1800, "height": 2500})
    logger.info("setting odds format to '%s'", chosen)

    try:
        odds_button = await _locate_odds_button(page)
        if odds_button is None:
            raise RuntimeError("Could not find odds format button")

        await dispatch_click(odds_button)
        await page.wait_for_selector('div.group > div.dropdown-content', timeout=3_000)
        dropdown_option = page.locator('div.group > div.dropdown-content > ul > li > a').filter(has_text=chosen).first
        await dropdown_option.wait_for(timeout=3_000)
        await dispatch_click(dropdown_option)
        logger.info("Odds format changed")
    except Exception as exc:
        logger.warning("Odds format not changed (maybe already set): %s", exc)


__all__ = ["set_odds_format"]
