"""League URL helpers."""

from __future__ import annotations

from typing import Dict, List

from ..constants import LEAGUES_URLS_MAP

__all__ = ["get_historic_urls", "get_url_from", "get_years_in_range"]


def _get_league(league_name: str) -> Dict[str, object]:
    league = LEAGUES_URLS_MAP.get(league_name)
    if not league:
        raise ValueError(f"League '{league_name}' is not referenced")
    return league


def get_historic_urls(league_name: str, start_year: int | str, end_year: int | str) -> List[str]:
    """Build all season URLs for the provided year span."""

    league = _get_league(league_name)
    start = int(start_year)
    end = int(end_year)

    if start > end:
        raise ValueError("start_year must be <= end_year")

    urls: List[str] = []
    for year in range(start, end + 1):
        if league["fixed_structure"]:
            season_path = f"{league['url']}-{year}/results/"
        else:
            season_path = f"{league['url']}-{year}-{year + 1}/results/"
        urls.append(season_path)

    return urls


def get_url_from(league_name: str) -> str:
    """Return the base URL for the given league."""

    league = _get_league(league_name)
    return str(league["url"])


def get_years_in_range(start_year: int, end_year: int) -> List[int]:
    return list(range(start_year, end_year + 1))
