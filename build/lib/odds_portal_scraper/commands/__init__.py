"""CLI-facing command helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable, Optional

from ..browser import launch_browser
from ..scraping import historic_scraper, next_matches_scraper

Callback = Callable[[dict, str], Awaitable[None]]


async def _run_with_browser(command):
    browser = await launch_browser()
    try:
        return await command(browser)
    finally:
        await browser.close()


async def historic_odds(
    league_name: str,
    start_year: int,
    end_year: int,
    odds_format: str,
    on_result: Callback,
    *,
    start_page: int = 1,
    activate_all_bookies: bool = True,
    skip_existing_dir: Path | None = None,
) -> None:
    async def _command(browser):
        await historic_scraper(
            browser,
            league_name,
            start_year,
            end_year,
            odds_format,
            on_result,
            start_page=start_page,
            activate_all_bookies=activate_all_bookies,
            skip_existing_dir=skip_existing_dir,
        )

    await _run_with_browser(_command)


async def next_matches(
    league_name: str,
    odds_format: str,
    on_result: Callback,
    limit: Optional[int] = None,
    *,
    activate_all_bookies: bool = True,
    skip_existing_dir: Path | None = None,
) -> None:
    async def _command(browser):
        await next_matches_scraper(
            browser,
            league_name,
            odds_format,
            on_result,
            limit,
            activate_all_bookies=activate_all_bookies,
            skip_existing_dir=skip_existing_dir,
        )

    await _run_with_browser(_command)


__all__ = ["historic_odds", "next_matches"]
