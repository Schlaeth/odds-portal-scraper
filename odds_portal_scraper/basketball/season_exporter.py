"""Export Basketball Reference league season tables to Excel."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pandas as pd
import requests

from ..logger import logger


def _fetch_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


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


def export_basketball_season(league: str, season_year: int, output_path: Path) -> Path:
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
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info("Wrote sheet %s with %s rows", sheet_name, len(df))

    logger.info("Exported season workbook to %s", output_path)
    return output_path


__all__ = ["export_basketball_season"]
