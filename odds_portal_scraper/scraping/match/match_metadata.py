"""Extract metadata for a single match page."""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from playwright.async_api import Page

GAME_TIME_SELECTOR = '[data-testid="game-time-item"] p'
GAME_TIME_FALLBACK_SELECTOR = '.text-xs.text-gray-dark'
GAME_PARTICIPANTS_SELECTOR = '[data-testid="game-participants"] p.truncate'
GAME_TITLE_SELECTOR = 'h1'
GAME_TITLE_SEPARATOR = ' - '
LONG_TIMEOUT_MS = 5_000
SHORT_TIMEOUT_MS = 3_000


async def extract_match_metadata(page: Page) -> dict:
    fallback_date = datetime.now()
    day, date, time = await _read_date_time(page, fallback_date)
    home, away = await _read_participants(page)
    day_clean = _clean_token(day)
    time_clean = _clean_token(time)
    normalised_date = _normalise_date(date)
    return {
        "day": day_clean,
        "date": normalised_date,
        "time": time_clean,
        "homeTeam": home,
        "awayTeam": away,
    }


async def _read_date_time(page: Page, fallback: datetime) -> Tuple[str, str, str]:
    fallback_values = [
        "Today",
        fallback.strftime("%Y-%m-%d"),
        fallback.strftime("%H:%M"),
    ]

    try:
        await page.wait_for_selector(GAME_TIME_SELECTOR, timeout=LONG_TIMEOUT_MS)
        contents: List[str] = await page.locator(GAME_TIME_SELECTOR).all_text_contents()
        if len(contents) >= 3:
            return tuple(contents[:3])  # type: ignore[return-value]
    except Exception:
        pass

    try:
        await page.wait_for_selector(GAME_TIME_FALLBACK_SELECTOR, timeout=SHORT_TIMEOUT_MS)
        contents = await page.locator(GAME_TIME_FALLBACK_SELECTOR).all_text_contents()
        if len(contents) >= 3:
            return tuple(contents[:3])  # type: ignore[return-value]
    except Exception:
        pass

    return tuple(fallback_values)  # type: ignore[return-value]


async def _read_participants(page: Page) -> Tuple[str, str]:
    try:
        await page.wait_for_selector(GAME_PARTICIPANTS_SELECTOR, timeout=LONG_TIMEOUT_MS)
        teams = await page.locator(GAME_PARTICIPANTS_SELECTOR).all_text_contents()
        if len(teams) >= 2:
            return teams[0], teams[1]
    except Exception:
        pass

    try:
        await page.wait_for_selector(f"{GAME_TITLE_SELECTOR} span", timeout=SHORT_TIMEOUT_MS)
        title = await page.locator(GAME_TITLE_SELECTOR).text_content()
        if title and GAME_TITLE_SEPARATOR in title:
            tokens = [token.strip() for token in title.split(GAME_TITLE_SEPARATOR) if token.strip()]
            if len(tokens) >= 2:
                return tokens[0], tokens[1]
    except Exception:
        pass

    derived = _parse_participants_from_url(page.url)
    if derived:
        return derived

    raise RuntimeError("Unable to determine match participants from page content.")


def _parse_participants_from_url(url: str) -> Tuple[str, str] | None:
    if not url:
        return None

    slug = url.split('#', 1)[0].split('?', 1)[0].rstrip('/').split('/')[-1]
    tokens = [token for token in slug.split('-') if token]
    if len(tokens) < 2:
        return None

    return _format_team(tokens[0]), _format_team(tokens[1])


def _format_team(name: str) -> str:
    clean = name.lower()
    return clean.capitalize()


def _clean_token(value: str) -> str:
    return value.strip().rstrip(",")


def _normalise_date(value: str) -> str:
    clean = _clean_token(value)
    if not clean:
        return clean
    known_formats = ("%d %b %Y", "%d %B %Y", "%Y-%m-%d")
    for fmt in known_formats:
        try:
            parsed = datetime.strptime(clean, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean


__all__ = ["extract_match_metadata"]
