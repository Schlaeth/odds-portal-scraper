"""Export Basketball Reference league season tables to Excel."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Literal, Optional

import pandas as pd
import requests
from requests.exceptions import HTTPError, RequestException

from ..logger import logger

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.basketball-reference.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_html_with_playwright(url: str) -> str:
    """Fetch page HTML via headless Chromium to bypass simple blocks."""
    from playwright.sync_api import sync_playwright

    logger.info("Retrying with Playwright browser: %s", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="en-US",
            extra_http_headers={
                "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
                "Referer": DEFAULT_HEADERS["Referer"],
            },
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        content = page.content()
        context.close()
        browser.close()
        return content


def _fetch_html(url: str, *, use_browser_fallback: bool = True) -> str:
    """Fetch HTML with requests; optionally retry with Playwright on block."""
    try:
        response = requests.get(url, timeout=30, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        return response.text
    except HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if use_browser_fallback and status in {403, 429}:
            return _fetch_html_with_playwright(url)
        raise
    except RequestException:
        if use_browser_fallback:
            return _fetch_html_with_playwright(url)
        raise


def _extract_table_ids(html: str) -> List[str]:
    """Return table ids in document order (used as sheet names)."""
    ids = re.findall(r'<table[^>]+id="([^"]+)"', html, flags=re.IGNORECASE)
    # Preserve order and uniqueness
    seen = set()
    ordered: List[str] = []
    for table_id in ids:
        if table_id not in seen:
            ordered.append(table_id)
            seen.add(table_id)
    return ordered


def _export_schedule_csv(league: str, season_year: int, target: Path) -> Path:
    """Download season schedule/results page and export the schedule table as CSV."""
    url = f"https://www.basketball-reference.com/leagues/{league}_{season_year}_games.html"
    logger.info("Downloading Basketball Reference schedule: %s", url)

    html = _fetch_html(url)
    tables = pd.read_html(html, attrs={"id": "schedule"})
    if not tables:
        raise ValueError(f"No schedule table found for {url}")

    schedule = tables[0].copy()
    if "Date" in schedule.columns:
        # Format as ISO strings to avoid Excel rendering ##### in some locales/column widths.
        schedule["Date"] = pd.to_datetime(schedule["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    schedule.to_csv(target, index=False)
    logger.info("Exported schedule CSV to %s", target)
    return target


def _export_schedule_workbook(league: str, season_year: int, target: Path) -> Path:
    """Download schedule main page and split into monthly sheets."""
    url = f"https://www.basketball-reference.com/leagues/{league}_{season_year}_games.html"
    logger.info("Downloading Basketball Reference schedule (xlsx): %s", url)

    html = _fetch_html(url)
    tables = pd.read_html(html, attrs={"id": "schedule"})
    if not tables:
        raise ValueError(f"No schedule table found for {url}")

    schedule = tables[0].copy()
    if "Date" not in schedule.columns:
        raise ValueError("Schedule table missing Date column")
    schedule["Date"] = pd.to_datetime(schedule["Date"], errors="coerce")

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        months = schedule["Date"].dt.month_name()
        if months.isna().all():
            raise ValueError("No valid dates in schedule table")
        for month_name, frame in schedule.groupby(months):
            if pd.isna(month_name):
                continue
            sheet_name = str(month_name)[:31]
            frame_to_write = frame.copy()
            if "Date" in frame_to_write.columns and pd.api.types.is_datetime64_any_dtype(frame_to_write["Date"]):
                # Format as strings to avoid ##### display issues in Excel.
                frame_to_write["Date"] = frame_to_write["Date"].dt.strftime("%Y-%m-%d")
            frame_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info("Wrote %s schedule sheet to %s", sheet_name, target)

    logger.info("Exported schedule workbook to %s", target)
    return target


def export_basketball_season(
    league: str,
    season_year: int,
    output_path: Path,
    *,
    include_schedule: bool = False,
    schedule_output_path: Optional[Path] = None,
    schedule_format: Literal["csv", "xlsx"] = "xlsx",
) -> Path:
    """Download season page and export all detected tables to an Excel workbook."""
    url = f"https://www.basketball-reference.com/leagues/{league}_{season_year}.html"
    logger.info("Downloading Basketball Reference season page: %s", url)

    html = _fetch_html(url)
    tables = pd.read_html(html)

    if not tables:
        raise ValueError(f"No tables found for {url}")

    table_ids = _extract_table_ids(html)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for idx, df in enumerate(tables):
            default_name = f"table_{idx + 1}"
            table_id = table_ids[idx] if idx < len(table_ids) else default_name
            sheet_name = (table_id or default_name)[:31]  # Excel sheet name limit

            if isinstance(df.columns, pd.MultiIndex):
                # Flatten MultiIndex columns so Excel export works with index=False.
                df = df.copy()
                df.columns = [" ".join([str(part) for part in col if part]).strip() for col in df.columns]

            df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info("Wrote sheet %s with %s rows", sheet_name, len(df))

    logger.info("Exported season workbook to %s", output_path)

    if include_schedule:
        if schedule_format == "csv":
            schedule_path = schedule_output_path or output_path.with_name(f"{output_path.stem}-games.csv")
            _export_schedule_csv(league, season_year, schedule_path)
        else:
            schedule_path = schedule_output_path or output_path.with_name(f"{output_path.stem}-games.xlsx")
            _export_schedule_workbook(league, season_year, schedule_path)

    return output_path


def export_basketball_season_range(
    league: str,
    start_year: int,
    end_year: int,
    output_dir: Path,
    *,
    include_schedule: bool = False,
    schedule_dir: Optional[Path] = None,
    schedule_format: Literal["csv", "xlsx"] = "xlsx",
) -> list[Path]:
    """Download a range of seasons (inclusive) and save one workbook per season."""
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_schedule_dir = Path(schedule_dir) if schedule_dir else output_dir

    written: list[Path] = []
    for year in range(start_year, end_year + 1):
        target = output_dir / f"{league.lower()}-{year}.xlsx"
        schedule_target = (
            resolved_schedule_dir / f"{league.lower()}-{year}-games.{schedule_format}"
            if include_schedule
            else None
        )
        export_basketball_season(
            league,
            year,
            target,
            include_schedule=include_schedule,
            schedule_output_path=schedule_target,
            schedule_format=schedule_format,
        )
        written.append(target)
    return written


def export_basketball_schedule(
    league: str,
    season_year: int,
    output_path: Path,
    *,
    schedule_format: Literal["csv", "xlsx"] = "csv",
) -> Path:
    """Export only the schedule/results table for a season."""
    if schedule_format == "csv":
        return _export_schedule_csv(league, season_year, output_path)
    return _export_schedule_workbook(league, season_year, output_path)


__all__ = [
    "export_basketball_season",
    "export_basketball_season_range",
    "export_basketball_schedule",
]
