# Agents Guide

Kurzüberblick für Automations-/Agent-Workflows in diesem Projekt.

## Ziele
- Historische Fußball-Quoten von oddsportal.com scrapen und als JSON lokal oder nach S3 exportieren.
- Kommandozeilen-Interface: `odds-portal` (Typer, async Playwright).

## Kernbefehle
- `odds-portal historic <league> <start_year> <end_year> --odds-format <key> (--local DIR | --s3 BUCKET) [--start-page N] [--no-all-bookies] [--no-skip-existing]`
  - `--start-page` erlaubt das Ansetzen ab einer paginierten Ergebnisseite (z.B. 10).
- `odds-portal next-matches <league> --odds-format <key> (--local DIR | --s3 BUCKET) [--limit N] [--no-all-bookies] [--no-skip-existing]`
- Info-Commands: `odds-portal soccer-leagues`, `odds-portal odds-format`.

## Wichtige Flags
- `--odds-format`: Schlüssel gemäß `odds_portal_scraper/constants.py` (z.B. `eu`, `us`).
- `--all-bookies/--no-all-bookies`: Clicking des “All”-Filters steuern.
- `--skip-existing/--no-skip-existing`: Lokales Überschreiben verhindern oder erlauben.
- `--start-page`: Nur bei `historic`; überspringt frühere Paginierungsseiten.

## Voraussetzungen
- Python 3.10+, Playwright installiert (`playwright install chromium`).
- Optional Proxy: `ODDS_PORTAL_PROXY_URL`.
- Für S3-Exporte: gültige AWS-Creds im Umfeld.

## Tests
- `pytest` (Browser-Calls sind gemockt). Test-Runner ist nicht im Repo, ggf. zuerst `pip install -e .[dev]`.

## Logging/Fehler
- Detail-Logs via `--log-level INFO` oder `DEBUG`.
- Typischer Timeout: `Page.wait_for_selector` bei leeren/langsamen Seiten; ggf. mit `--start-page` weiter hinten ansetzen oder erneut versuchen.
