from typer.testing import CliRunner
import pytest

from odds_portal_scraper.cli import app

runner = CliRunner()


@pytest.mark.parametrize(
    "command",
    [
        [
            "historic",
            "premier-league-1",
            "2022",
            "2020",
            "--odds-format",
            "eu",
            "--local",
            "out",
            "--no-all-bookies",
        ],
        [
            "next-matches",
            "premier-league-1",
            "--odds-format",
            "eu",
            "--local",
            "out",
            "--s3",
            "bucket",
            "--all-bookies",
        ],
    ],
)
def test_cli_validation_errors(monkeypatch, command):
    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("odds_portal_scraper.cli.historic_odds", noop)
    monkeypatch.setattr("odds_portal_scraper.cli.next_matches", noop)

    result = runner.invoke(app, command)
    assert result.exit_code != 0
    assert "Cannot use both" in result.output or "start_year" in result.output


def test_cli_requires_output(monkeypatch):
    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("odds_portal_scraper.cli.historic_odds", noop)

    result = runner.invoke(
        app,
        [
            "historic",
            "premier-league-1",
            "2020",
            "2021",
            "--odds-format",
            "eu",
            "--no-all-bookies",
        ],
    )
    assert result.exit_code != 0
    assert "One of --s3 or --local" in result.output


def test_cli_requires_valid_start_page(monkeypatch):
    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("odds_portal_scraper.cli.historic_odds", noop)

    result = runner.invoke(
        app,
        [
            "historic",
            "premier-league-1",
            "2020",
            "2021",
            "--odds-format",
            "eu",
            "--start-page",
            "0",
            "--local",
            "out",
        ],
    )
    assert result.exit_code != 0
    assert "start_page" in result.output


def test_soccer_leagues_lists_known_entries():
    result = runner.invoke(app, ["soccer-leagues"])
    assert result.exit_code == 0
    assert "premier-league-1" in result.output
    assert "bundesliga-1" in result.output
