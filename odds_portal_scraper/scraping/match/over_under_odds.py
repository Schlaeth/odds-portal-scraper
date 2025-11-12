"""Scrape over/under odds for selected totals."""

from __future__ import annotations

from typing import Dict, List

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ...logger import logger
from ..shared.activate_all_bookies_filter import activate_all_bookies_filter
from ..shared.dispatch_click import dispatch_click

MARKET_TABS_SELECTOR = "div.hide-menu li >> div:has-text('Over/Under')"
SPECIFIC_MARKET_SELECTOR = 'div[data-testid="over-under-collapsed-option-box"]'
ROW_SELECTOR = 'div[data-testid="over-under-expanded-row"]'
WAIT_SELECTOR = f"{ROW_SELECTOR} p.odds-text"

RELOAD_RETRY = {
    "status_codes": (430,),
    "max_attempts": 3,
    "wait_ms": 10_000,
}

MARKET_LABELS = {
    "1.5": "Over/Under +1.5",
    "2.5": "Over/Under +2.5",
    "3.5": "Over/Under +3.5",
}


async def extract_over_under_odds(page: Page, total: str) -> List[Dict[str, str]]:
    wanted = MARKET_LABELS.get(total)
    if not wanted:
        raise ValueError(f"Unsupported market total {total}")

    logger.info("scrapping odd for under/over %s market", total)

    await _prepare_market(page, total, wanted)
    await _ensure_odds_loaded(page, total, wanted)

    rows = await page.query_selector_all(ROW_SELECTOR)
    results: List[Dict[str, str]] = []

    for row in rows:
        if not row:
            continue

        total_el = await row.query_selector('div[data-testid="total-container"]')
        total_text = None
        if total_el:
            text = await total_el.text_content()
            total_text = _clean(text)

        attribute = None
        provider = await row.query_selector('[provider-name]')
        if provider:
            attribute = await provider.get_attribute('provider-name')

        expected = f"+{total}"
        if total_text not in (expected, f"{expected}") and (attribute != expected):
            continue

        bookmaker_name = await _read_cell_text(row, 'p[data-testid="outrights-expanded-bookmaker-name"]')
        odds_cells = await row.query_selector_all('div.odds-cell')
        if len(odds_cells) < 2:
            continue

        odds_over = await _read_odds_text(odds_cells[0])
        odds_under = await _read_odds_text(odds_cells[1])
        if bookmaker_name and odds_over and odds_under:
            results.append(
                {
                    "bookmakerName": bookmaker_name,
                    "oddsOver": odds_over,
                    "oddsUnder": odds_under,
                }
            )
    return results


async def _prepare_market(page: Page, total: str, wanted_label: str) -> None:
    tab = page.locator(MARKET_TABS_SELECTOR).first
    await dispatch_click(tab)
    logger.info("click successful, waiting for market options to load...")
    await activate_all_bookies_filter(page)
    await _select_market_option(page, total, wanted_label)
    logger.info("click successful, waiting for %s odds to load...", wanted_label)


async def _ensure_odds_loaded(page: Page, total: str, wanted_label: str) -> None:
    try:
        await page.wait_for_selector(WAIT_SELECTOR)
    except PlaywrightTimeoutError:
        logger.warning("timeout waiting for %s odds. Reloading page and retrying once.", wanted_label)
        await _reload_with_retry(page)
        await _prepare_market(page, total, wanted_label)
        await page.wait_for_selector(WAIT_SELECTOR)


async def _reload_with_retry(page: Page) -> None:
    for attempt in range(1, RELOAD_RETRY["max_attempts"] + 1):
        try:
            response = await page.reload(wait_until="domcontentloaded")
            status = response.status() if response else None
            if status and status in RELOAD_RETRY["status_codes"]:
                if attempt == RELOAD_RETRY["max_attempts"]:
                    raise RuntimeError(f"HTTP {status}")
                logger.warning(
                    "received status %s on reload (attempt %s/%s). Waiting %sms before retry.",
                    status,
                    attempt,
                    RELOAD_RETRY["max_attempts"],
                    RELOAD_RETRY["wait_ms"],
                )
            else:
                return
        except Exception as exc:
            if attempt == RELOAD_RETRY["max_attempts"]:
                raise RuntimeError(f"failed to reload page after {attempt} attempts: {exc}")
            logger.warning(
                "error while reloading page (attempt %s/%s): %s. Waiting %sms before retry.",
                attempt,
                RELOAD_RETRY["max_attempts"],
                exc,
                RELOAD_RETRY["wait_ms"],
            )
        await page.wait_for_timeout(RELOAD_RETRY["wait_ms"])


async def _select_market_option(page: Page, total: str, wanted_label: str) -> None:
    locator = page.locator(SPECIFIC_MARKET_SELECTOR, has_text=f"+{total}").first
    try:
        await locator.wait_for(state="visible", timeout=8_000)
    except PlaywrightTimeoutError:
        logger.warning("timeout waiting for %s option. Scrolling and retrying.", wanted_label)
        await _scroll_market_options(page)
        await locator.wait_for(state="visible")
    await dispatch_click(locator)


async def _scroll_market_options(page: Page) -> None:
    try:
        await page.evaluate("() => window.scrollBy(0, window.innerHeight || 600)")
    except Exception:
        pass
    await page.wait_for_timeout(500)


async def _read_cell_text(row, selector: str) -> str | None:
    element = await row.query_selector(selector)
    if not element:
        return None
    text = await element.text_content()
    return _clean(text)


async def _read_odds_text(container) -> str | None:
    link = await container.query_selector('a.odds-link')
    paragraph = await container.query_selector('p.odds-text')
    for target in (link, paragraph):
        if target:
            text = await target.text_content()
            cleaned = _clean(text)
            if cleaned:
                return cleaned
    return None


def _clean(value: str | None) -> str:
    return (value or "").replace("\xa0", " ").strip()


__all__ = ["extract_over_under_odds"]
