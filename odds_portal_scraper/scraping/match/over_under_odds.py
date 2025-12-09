"""Scrape over/under odds for selected totals."""

from __future__ import annotations

import re
from typing import Dict, List

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ...logger import logger
from ..shared.activate_all_bookies_filter import activate_all_bookies_filter
from ..shared.dispatch_click import dispatch_click

MARKET_TABS_SELECTORS = (
    "button[role='tab']:has-text('Over/Under')",
    "a[role='tab']:has-text('Over/Under')",
    "div.hide-menu li >> :is(div,a,span):has-text('Over/Under')",
    "nav :is(div,a,span):has-text('Over/Under')",
    "text=Over/Under",
)
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


async def extract_over_under_odds(page: Page, total: str, activate_all: bool = True) -> List[Dict[str, str]]:
    wanted = MARKET_LABELS.get(total, f"Over/Under +{total}")

    logger.info("scrapping odd for under/over %s market", total)

    try:
        await _prepare_market(page, total, wanted, activate_all)
        await _ensure_odds_loaded(page, total, wanted, activate_all)
    except PlaywrightTimeoutError:
        logger.warning("Skipping %s market because the widget never became visible.", wanted)
        return []
    except RuntimeError as exc:
        logger.warning("Skipping %s market due to error: %s", wanted, exc)
        return []

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
        matches_total = False
        if total_text:
            matches_total = expected in total_text or str(total) in total_text
        if not matches_total and attribute not in {expected, str(total)}:
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


async def _prepare_market(page: Page, total: str, wanted_label: str, activate_all: bool) -> None:
    tab = await _find_over_under_tab(page)
    await dispatch_click(tab)
    logger.info("click successful, waiting for market options to load...")
    if activate_all:
        await activate_all_bookies_filter(page)
    await _select_market_option(page, total, wanted_label)
    logger.info("click successful, waiting for %s odds to load...", wanted_label)


async def _ensure_odds_loaded(page: Page, total: str, wanted_label: str, activate_all: bool) -> None:
    try:
        await page.wait_for_selector(WAIT_SELECTOR)
    except PlaywrightTimeoutError:
        logger.warning("timeout waiting for %s odds. Reloading page and retrying once.", wanted_label)
        await _reload_with_retry(page)
        await _prepare_market(page, total, wanted_label, activate_all)
        await page.wait_for_selector(WAIT_SELECTOR)


async def _reload_with_retry(page: Page) -> None:
    for attempt in range(1, RELOAD_RETRY["max_attempts"] + 1):
        try:
            response = await page.reload(wait_until="domcontentloaded")
            status = response.status if response else None
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


async def discover_over_under_totals(page: Page) -> List[str]:
    """Return all totals shown in the Over/Under selector boxes."""
    tab = await _find_over_under_tab(page)
    await dispatch_click(tab)
    try:
        await page.wait_for_selector(SPECIFIC_MARKET_SELECTOR, timeout=6_000)
    except PlaywrightTimeoutError:
        logger.warning("Over/Under options never became visible; skipping totals discovery.")
        return []
    options = await page.query_selector_all(SPECIFIC_MARKET_SELECTOR)
    totals: List[str] = []
    for option in options:
        text = await option.text_content()
        total = _extract_total_from_label(_clean(text))
        if total:
            totals.append(total)
    unique = list(dict.fromkeys(totals))
    if not unique:
        logger.warning("No over/under totals discovered on page")
    return unique


async def _find_over_under_tab(page: Page):
    candidates = []

    async def _expand_more_menu() -> None:
        """Some layouts hide tabs behind a 'More' toggle; try to reveal it."""
        more = page.locator("button:has-text('More'), a:has-text('More'), div:has-text('More')").first
        try:
            if await more.count() > 0:
                await more.scroll_into_view_if_needed()
                await dispatch_click(more)
                await page.wait_for_timeout(250)
        except Exception:
            pass

    await _expand_more_menu()

    for selector in MARKET_TABS_SELECTORS:
        locator = page.locator(selector).filter(has_text="Over/Under").first
        try:
            await locator.wait_for(state="attached", timeout=4_000)
            is_visible = False
            try:
                is_visible = await locator.is_visible()
            except Exception:
                pass
            if is_visible:
                return locator
            candidates.append(locator)
        except PlaywrightTimeoutError:
            continue

    # Nothing visible; try expanding the menu once more and return the first attached candidate.
    if candidates:
        await _expand_more_menu()
        fallback = candidates[0]
        try:
            await fallback.scroll_into_view_if_needed()
        except Exception:
            pass
        return fallback

    raise PlaywrightTimeoutError(f"Over/Under tab not visible with selectors {MARKET_TABS_SELECTORS}")


def _extract_total_from_label(label: str | None) -> str | None:
    if not label:
        return None
    match = re.search(r"\+?(-?\d+(?:\.\d+)?)", label)
    if match:
        return match.group(1)
    return None


def _clean(value: str | None) -> str:
    return (value or "").replace("\xa0", " ").strip()


__all__ = ["extract_over_under_odds", "discover_over_under_totals"]
