"""Scrape a single match page and return its odds payload."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from playwright.async_api import Page

from ...constants import BASE_URL
from ...logger import logger
from ...utils.date_time import current_timestamp
from ..shared.action_runner import create_action_runner
from ..shared.goto_with_retry import goto_with_retry
from ..shared.humanizer import create_humanizer, merge_humanize_config
from .match_metadata import extract_match_metadata
from .moneyline_odds import extract_moneyline_odds
from .over_under_odds import extract_over_under_odds

MATCH_RETRY_DEFAULT = {
    "status_codes": (430,),
    "max_attempts": 4,
    "wait_ms": 20_000,
}

ACTION_DELAY_DEFAULT_MS = 1_000
ACTION_RETRY_DEFAULT = {
    "max_attempts": 5,
    "delay_ms": 1_000,
}


def _merge_retry(defaults: Dict, overrides: Optional[Dict]) -> Dict:
    if not overrides:
        return defaults
    merged = defaults.copy()
    merged.update(overrides)
    return merged


async def scrape_match(
    page: Page,
    link: str,
    league_name: str,
    options: Optional[Dict] = None,
) -> Optional[Dict[str, object]]:
    """Navigate to the given relative link and return scraped data plus filename."""

    opts = options or {}
    retry = _merge_retry(MATCH_RETRY_DEFAULT, opts.get("retry"))
    action_delay_ms = int(opts.get("action_delay_ms", ACTION_DELAY_DEFAULT_MS))
    action_retry = _merge_retry(ACTION_RETRY_DEFAULT, opts.get("action_retry"))
    humanize_config = merge_humanize_config(opts.get("humanize"))
    humanizer = create_humanizer(page, humanize_config)
    run_action = create_action_runner(page, action_delay_ms, action_retry, humanizer)
    activate_all_bookies = bool(opts.get("all_bookies", True))
    skip_existing_dir = opts.get("skip_existing_dir")
    skip_existing_path = Path(skip_existing_dir) if skip_existing_dir else None

    url = f"{BASE_URL}{link}"

    try:
        await goto_with_retry(page, url, retry=retry)
        metadata = await run_action("match metadata", lambda: extract_match_metadata(page))
        iso_date = metadata.get("date") or "unknown-date"
        file_name = f"{iso_date}--{metadata['homeTeam']}-{metadata['awayTeam']}.json"
        if skip_existing_path:
            destination = skip_existing_path / file_name
            if destination.exists():
                logger.info("Skipping existing file %s before odds collection", destination)
                return None

        ml_full = await run_action(
            "moneyline odds (full time)",
            lambda: extract_moneyline_odds(page, "fullTime", activate_all_bookies),
        )
        ml_first = await run_action(
            "moneyline odds (first half)",
            lambda: extract_moneyline_odds(page, "firstHalf", activate_all_bookies),
        )
        ml_second = await run_action(
            "moneyline odds (second half)",
            lambda: extract_moneyline_odds(page, "secondHalf", activate_all_bookies),
        )
        ou_25 = await run_action(
            "over/under odds (2.5)", lambda: extract_over_under_odds(page, "2.5", activate_all_bookies)
        )
        ou_15 = await run_action(
            "over/under odds (1.5)", lambda: extract_over_under_odds(page, "1.5", activate_all_bookies)
        )
        ou_35 = await run_action(
            "over/under odds (3.5)", lambda: extract_over_under_odds(page, "3.5", activate_all_bookies)
        )

        scraped_at = current_timestamp()
        data = {
            "scrapedAt": scraped_at,
            "leagueName": league_name,
            **metadata,
            "mlFirstHalf": ml_first,
            "mlSecondHalf": ml_second,
            "mlFullTime": ml_full,
            "underOver25": ou_25,
            "underOver15": ou_15,
            "underOver35": ou_35,
        }
        return {"data": data, "fileName": file_name}
    except Exception as exc:
        logger.error("extracting data for %s: %s", url, exc)
        raise

__all__ = ["scrape_match"]
