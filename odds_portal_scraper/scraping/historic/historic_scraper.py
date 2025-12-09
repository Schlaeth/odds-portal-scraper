"""Historic odds scraper orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from ...logger import logger
from ...utils.leagues import get_historic_urls
from ..match import collect_match_data
from .season_navigator import discover_season_pages


async def historic_scraper(
    browser,
    league_name: str,
    start_year: int,
    end_year: int,
    odds_format: str,
    on_result: Callable[[dict, str], Awaitable[None]],
    *,
    start_page: int = 1,
    activate_all_bookies: bool = True,
    skip_existing_dir: Path | None = None,
    over_under_range: tuple[float, float] | None = None,
) -> None:
    season_urls = get_historic_urls(league_name, start_year, end_year)

    for season_url in season_urls:
        page = None
        try:
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1_800, "height": 2_500})

            page_urls = await discover_season_pages(page, season_url, start_page=start_page)
            for page_url in page_urls:
                logger.info("Starting scrape for: %s", page_url)
                await page.goto(page_url, wait_until="domcontentloaded")
                async for result in collect_match_data(
                    page,
                    league_name=league_name,
                    odds_format=odds_format,
                    activate_all_bookies=activate_all_bookies,
                    skip_existing_dir=skip_existing_dir,
                    over_under_range=over_under_range,
                ):
                    await on_result(result["data"], result["fileName"])
        except Exception as exc:
            logger.error("Error during historic scraping: %s", exc)
            raise
        finally:
            if page and not page.is_closed():
                await page.close()


__all__ = ["historic_scraper"]
