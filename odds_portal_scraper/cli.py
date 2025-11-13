"""Typer CLI for the Python odds portal scraper."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .commands import historic_odds, next_matches
from .constants import LEAGUES_URLS_MAP, ODDS_FORMAT_MAP
from .exporters import export_to_dir, export_to_s3
from .logger import configure_logger

app = typer.Typer(help="Scrape soccer odds from oddsportal.com")
console = Console()


def _resolve_exporter(s3_bucket: Optional[str], local_dir: Optional[Path]):
    if s3_bucket and local_dir:
        raise typer.BadParameter("Cannot use both --s3 and --local options. Choose one.")
    if s3_bucket:
        return export_to_s3(s3_bucket)
    if local_dir:
        return export_to_dir(local_dir)
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
    s3: Optional[str] = typer.Option(None, help="S3 bucket to upload JSON files"),
    local: Optional[Path] = typer.Option(None, help="Local directory to save JSON files"),
    all_bookies: bool = typer.Option(
        True,
        "--all-bookies/--no-all-bookies",
        help="Toggle the \"All\" bookies filter before scraping each market",
    ),
):
    if start_year > end_year:
        raise typer.BadParameter("start_year must be less than or equal to end_year")
    exporter = _resolve_exporter(s3, local)
    _run_async(
        historic_odds(
            league_name,
            start_year,
            end_year,
            odds_format,
            exporter,
            activate_all_bookies=all_bookies,
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
):
    exporter = _resolve_exporter(s3, local)
    _run_async(
        next_matches(
            league_name,
            odds_format,
            exporter,
            limit,
            activate_all_bookies=all_bookies,
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


__all__ = ["app"]
