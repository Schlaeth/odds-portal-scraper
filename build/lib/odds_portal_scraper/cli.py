"""Typer CLI for the Python odds portal scraper."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Tuple, Literal

import typer
from rich.console import Console
from rich.table import Table

from .basketball import (
    export_basketball_schedule,
    export_basketball_schedule_range,
    export_basketball_season,
    export_basketball_season_range,
)
from .commands import historic_odds, next_matches
from .constants import LEAGUES_URLS_MAP, ODDS_FORMAT_MAP
from .exporters import CallbackType, export_to_dir, export_to_s3
from .logger import configure_logger

app = typer.Typer(help="Scrape soccer odds from oddsportal.com")
console = Console()


def _resolve_exporter(
    s3_bucket: Optional[str],
    local_dir: Optional[Path],
    *,
    skip_existing: bool = False,
) -> Tuple[CallbackType, Optional[Path]]:
    if s3_bucket and local_dir:
        raise typer.BadParameter("Cannot use both --s3 and --local options. Choose one.")
    if s3_bucket:
        return export_to_s3(s3_bucket), None
    if local_dir:
        skip_dir: Optional[Path] = local_dir if skip_existing else None
        return export_to_dir(local_dir, skip_existing=skip_existing), skip_dir
    raise typer.BadParameter("One of --s3 or --local must be provided")


def _run_async(coro):
    return asyncio.run(coro)


@app.callback()
def main(log_level: Optional[str] = typer.Option(None, help="Configure log verbosity")):
    if log_level:
        configure_logger(log_level)


@app.command()
def historic(
    league_name: str = typer.Argument(..., help="League identifier (see soccer-leagues command)"),
    start_year: int = typer.Argument(..., help="Season start year"),
    end_year: int = typer.Argument(..., help="Season end year"),
    odds_format: str = typer.Option(..., "--odds-format", "-o", help="Desired odds format"),
    start_page: int = typer.Option(
        1,
        "--start-page",
        "-s",
        help="Start scraping at this page number (skips earlier paginated pages)",
    ),
    s3: Optional[str] = typer.Option(None, help="S3 bucket to upload JSON files"),
    local: Optional[Path] = typer.Option(None, help="Local directory to save JSON files"),
    all_bookies: bool = typer.Option(
        True,
        "--all-bookies/--no-all-bookies",
        help="Toggle the \"All\" bookies filter before scraping each market",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--no-skip-existing",
        help="When exporting locally, skip matches whose JSON file already exists",
    ),
):
    if start_year > end_year:
        raise typer.BadParameter("start_year must be less than or equal to end_year")
    if start_page < 1:
        raise typer.BadParameter("start_page must be greater than or equal to 1")
    exporter, skip_dir = _resolve_exporter(s3, local, skip_existing=skip_existing)
    _run_async(
        historic_odds(
            league_name,
            start_year,
            end_year,
            odds_format,
            exporter,
            start_page=start_page,
            activate_all_bookies=all_bookies,
            skip_existing_dir=skip_dir,
        )
    )


@app.command(name="next-matches")
def next_matches_cmd(
    league_name: str = typer.Argument(..., help="League identifier (see soccer-leagues command)"),
    odds_format: str = typer.Option(..., "--odds-format", "-o", help="Desired odds format"),
    s3: Optional[str] = typer.Option(None, help="S3 bucket to upload JSON files"),
    local: Optional[Path] = typer.Option(None, help="Local directory to save JSON files"),
    limit: Optional[int] = typer.Option(None, help="Limit number of matches to scrape"),
    all_bookies: bool = typer.Option(
        True,
        "--all-bookies/--no-all-bookies",
        help="Toggle the \"All\" bookies filter before scraping each market",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--no-skip-existing",
        help="When exporting locally, skip matches whose JSON file already exists",
    ),
):
    exporter, skip_dir = _resolve_exporter(s3, local, skip_existing=skip_existing)
    _run_async(
        next_matches(
            league_name,
            odds_format,
            exporter,
            limit,
            activate_all_bookies=all_bookies,
            skip_existing_dir=skip_dir,
        )
    )


@app.command(name="soccer-leagues")
def soccer_leagues():
    table = Table(title="Available leagues")
    table.add_column("Key")
    table.add_column("URL")
    for name, info in LEAGUES_URLS_MAP.items():
        table.add_row(name, info["url"])
    console.print(table)


@app.command(name="odds-format")
def odds_format_cmd():
    table = Table(title="Available odds formats")
    table.add_column("Key")
    table.add_column("Description")
    for key, description in ODDS_FORMAT_MAP.items():
        table.add_row(key, description)
    console.print(table)


@app.command(name="basketball-season")
def basketball_season(
    season_year: Optional[int] = typer.Argument(
        None, help="Season end year (e.g., 2024 for 2023-24). Optional when using --start-year/--end-year."
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output Excel file path for single season"),
    league: str = typer.Option("NBA", "--league", "-l", help="Basketball Reference league prefix, e.g. NBA"),
    start_year: Optional[int] = typer.Option(None, "--start-year", "-s", help="Range start season year"),
    end_year: Optional[int] = typer.Option(None, "--end-year", "-e", help="Range end season year"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-d", help="Directory for multi-season export"),
    include_schedule: bool = typer.Option(
        False,
        "--include-schedule/--no-include-schedule",
        help="Also export the schedule/results table",
    ),
    schedule_output: Optional[Path] = typer.Option(
        None, "--schedule-output", "-c", help="Path for schedule export when exporting a single season"
    ),
    schedule_dir: Optional[Path] = typer.Option(
        None, "--schedule-dir", "-C", help="Directory for schedule exports when exporting a range"
    ),
    schedule_format: Literal["csv", "xlsx"] = typer.Option(
        "xlsx",
        "--schedule-format",
        "-f",
        case_sensitive=False,
        help="Schedule export format (csv or xlsx with monthly sheets)",
    ),
):
    """Download Basketball Reference season tables and export to XLSX."""
    range_mode = start_year is not None or end_year is not None

    if range_mode:
        if season_year is not None or output is not None:
            raise typer.BadParameter("Use either single-season (year + --output) or range mode (--start-year/--end-year + --output-dir)")
        if start_year is None or end_year is None:
            raise typer.BadParameter("Both --start-year and --end-year are required for range export")
        if start_year > end_year:
            raise typer.BadParameter("start_year must be less than or equal to end_year")
        if output_dir is None:
            raise typer.BadParameter("--output-dir is required for range export")
        export_basketball_season_range(
            league,
            start_year,
            end_year,
            output_dir,
            include_schedule=include_schedule,
            schedule_dir=schedule_dir,
            schedule_format=schedule_format,
        )
        return

    if season_year is None or output is None:
        raise typer.BadParameter("Provide a season year and --output for single-season export, or use range mode options")

    export_basketball_season(
        league,
        season_year,
        output,
        include_schedule=include_schedule,
        schedule_output_path=schedule_output,
        schedule_format=schedule_format,
    )


@app.command(name="basketball-schedule")
def basketball_schedule(
    season_year: int = typer.Argument(..., help="Season end year (e.g., 2026 for 2025-26)"),
    *,
    output: Path = typer.Option(..., "--output", "-o", help="Output path for schedule export"),
    league: str = typer.Option("NBA", "--league", "-l", help="Basketball Reference league prefix, e.g. NBA"),
    schedule_format: Literal["csv", "xlsx"] = typer.Option(
        "csv",
        "--schedule-format",
        "-f",
        case_sensitive=False,
        help="Schedule export format: csv (full table) or xlsx (monthly sheets)",
    ),
):
    """Export only the schedule/results table for a season."""
    export_basketball_schedule(league, season_year, output, schedule_format=schedule_format)


@app.command(name="basketball-schedule-range")
def basketball_schedule_range(
    start_year: int = typer.Argument(..., help="Range start season year"),
    end_year: int = typer.Argument(..., help="Range end season year"),
    *,
    output_dir: Path = typer.Option(..., "--output-dir", "-d", help="Directory for schedule exports"),
    league: str = typer.Option("NBA", "--league", "-l", help="Basketball Reference league prefix, e.g. NBA"),
    schedule_format: Literal["csv", "xlsx"] = typer.Option(
        "csv",
        "--schedule-format",
        "-f",
        case_sensitive=False,
        help="Schedule export format: csv or xlsx",
    ),
):
    """Export schedules for a range of seasons (month-split when xlsx)."""
    export_basketball_schedule_range(
        league, start_year, end_year, output_dir, schedule_format=schedule_format
    )


__all__ = ["app"]
