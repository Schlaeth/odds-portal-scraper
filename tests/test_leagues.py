from odds_portal_scraper.utils.leagues import get_historic_urls, get_url_from, get_years_in_range
import pytest


def test_get_historic_urls_variable_structure_single_season():
    urls = get_historic_urls("premier-league-1", 2020, 2021)
    assert urls == [
        "https://www.oddsportal.com/soccer/england/premier-league-2020-2021/results/",
    ]


def test_get_historic_urls_variable_structure_multiple_seasons():
    urls = get_historic_urls("premier-league-1", 2020, 2022)
    assert urls == [
        "https://www.oddsportal.com/soccer/england/premier-league-2020-2021/results/",
        "https://www.oddsportal.com/soccer/england/premier-league-2021-2022/results/",
    ]


def test_get_historic_urls_fixed_structure():
    urls = get_historic_urls("mls-1", 2020, 2021)
    assert urls == [
        "https://www.oddsportal.com/football/usa/mls-2020/results/",
        "https://www.oddsportal.com/football/usa/mls-2021/results/",
    ]


def test_get_historic_urls_split_year_invalid_range():
    with pytest.raises(ValueError):
        get_historic_urls("premier-league-1", 2020, 2020)


def test_get_url_from_unknown_league():
    with pytest.raises(ValueError):
        get_url_from("unknown")


def test_get_years_in_range():
    assert get_years_in_range(2020, 2023) == [2020, 2021, 2022, 2023]
