# Odds Portal Scraper (Python)

Python rewrite of the Odds Portal CLI: scrape historical or upcoming soccer odds from [oddsportal.com](https://www.oddsportal.com) and export them either locally or to Amazon S3. The tool now ships as a Typer CLI powered by Playwright's async API.

## Features

- Scrape historic season ranges or the next scheduled matches for a supported league.
- Change odds representation (EU, UK, US, HK, MA, IN) on the fly before scraping.
- Export JSON payloads directly to disk or upload them to S3.
- Randomised Playwright fingerprints + retries that mimic the original Node.js behaviour.
- Rich-powered tables for listing leagues / formats and structured logging.
- NBA season pages are supported via the `nba-1` league key (over/under totals rely on discovery; soccer defaults like 1.5/2.5/3.5 are skipped).

## Requirements

- Python 3.10+
- Node-free environment (Playwright Python package downloads its own browser build).
- AWS credentials configured in your shell when using the S3 exporter.
- Optional proxy configuration through `ODDS_PORTAL_PROXY_URL`.

After installing dependencies you must download the Playwright browser once:

```bash
playwright install chromium
```

## Installation

Clone the repo and install the package:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install --upgrade pip
pip install -e .[dev]
playwright install chromium
```

This exposes an `odds-portal` console script.

## Usage

```
odds-portal [COMMAND] [OPTIONS]
```

| Command          | Description                                   |
| ---------------- | --------------------------------------------- |
| `historic`       | Scrape odds for historic seasons              |
| `next-matches`   | Scrape upcoming matches                       |
| `soccer-leagues` | Print the supported league keys and URLs      |
| `odds-format`    | Print the supported odds format keys/descriptions |
| `basketball-season` | Export Basketball Reference season tables to XLSX (single season or range) |

Both scraping commands require one export target: `--local <dir>` or `--s3 <bucket>`.
When exporting locally the scraper now skips already existing JSON files by default; pass `--no-skip-existing` to overwrite.
League keys follow the pattern `<slug>-<division>` (for example `premier-league-1`, `bundesliga-2`).
Use `--no-all-bookies` if you want to skip clicking the “All” bookies filter (scraping is faster but returns only the default subset shown by OddsPortal).
Use `--start-page <number>` with the `historic` command to resume scraping from a specific paginated results page.

### Historic example

```bash
odds-portal historic premier-league-1 2020 2023 \
  --odds-format eu \
  --local ./output
```

### Next matches example

```bash
odds-portal next-matches bundesliga-1 \
  --odds-format eu \
  --s3 my-odds-dump \
  --limit 5 \
  --no-all-bookies
```

### Listing helpers

```bash
odds-portal soccer-leagues
odds-portal odds-format
```

### Basketball Reference season export

```bash
odds-portal basketball-season 2024 --league NBA --output ./nba-2024.xlsx
```

Exports all tables from the season page (new sheets per table).

#### Export mehrerer Basketball-Saisons

```bash
odds-portal basketball-season --league NBA --start-year 2000 --end-year 2024 --output-dir ./nba-seasons
```

Schreibt pro Saison eine XLSX mit Namen `nba-<year>.xlsx` in das Zielverzeichnis.

## Configuration

| Variable               | Purpose                                        |
| ---------------------- | ---------------------------------------------- |
| `ODDS_PORTAL_PROXY_URL`| Optional HTTP proxy passed to Playwright       |
| `AWS_ACCESS_KEY_ID`    | AWS credential for the S3 exporter             |
| `AWS_SECRET_ACCESS_KEY`| Pair to the access key above                   |
| `LOG_LEVEL`            | Set when invoking the CLI via `--log-level`    |

## Data output

Each match produces a JSON file named `<date>--<home>-<away>.json` (with `date` in `YYYY-MM-DD` format) containing metadata, three-way moneyline odds (full/first/second half) and over/under 1.5/2.5/3.5 markets. Example fields:

```json
{
  "scrapedAt": "2024-05-04 08:33:12",
  "leagueName": "premier-league-1",
  "day": "Saturday",
  "date": "2024-05-04",
  "homeTeam": "Arsenal",
  "awayTeam": "Chelsea",
  "mlFullTime": [ { "bookMakerName": "Bet365", "hw": "1.92", "d": "3.40", "aw": "4.00" } ],
  "underOver25": [ { "bookmakerName": "Bet365", "oddsOver": "1.91", "oddsUnder": "1.99" } ],
  "overUnderMarkets": [
    { "total": "2.5", "bookmakerName": "Bet365", "oddsOver": "1.91", "oddsUnder": "1.99" },
    { "total": "215.5", "bookmakerName": "Bet365", "oddsOver": "1.85", "oddsUnder": "1.95" }
  ]
}
```

## Development

- Lint/format with your preferred tooling (the project relies on standard library modules only).
- Run tests with `pytest` (Playwright/browser interactions are mocked in the suite):

```bash
pytest
```

## License

Distributed under the ISC license (same as the upstream project).
