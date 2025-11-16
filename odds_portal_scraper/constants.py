"""Static constants shared across the scraper."""

BASE_URL = "https://www.oddsportal.com"

LEAGUE_DEFINITIONS = (
    ("premier-league", 1, "soccer/england/premier-league", False),
    ("ligue", 1, "soccer/france/ligue-1", False),
    ("ligue", 2, "football/france/ligue-2", False),
    ("bundesliga", 1, "soccer/germany/bundesliga", False),
    ("bundesliga", 2, "football/germany/2-bundesliga", False),
    ("championship", 2, "football/england/championship", False),
    ("liga", 1, "football/spain/laliga", False),
    ("liga", 2, "football/spain/laliga2", False),
    ("serie", 1, "football/italy/serie-a", False),
    ("serie", 2, "football/italy/serie-b", False),
    ("mls", 1, "football/usa/mls", True),
    ("brazil-serie", 1, "football/brazil/serie-a", False),
    ("liga-mx", 1, "football/mexico/liga-mx", False),
    ("liga-portugal", 1, "football/portugal/liga-portugal", False),
    ("eredivisie", 1, "football/netherlands/eredivisie", False),
    ("belgian", 1, "football/belgium/jupiler-pro-league", False),
    ("argentina", 1, "football/argentina/liga-profesional", False),
    ("super-lig", 1, "football/turkey/super-lig", False),
    ("champions-league", 1, "football/europe/champions-league", False),
    ("europa-league", 1, "football/europe/europa-league", False),
    ("allsvenskan", 1, "football/sweden/allsvenskan", True),
)

LEAGUES_URLS_MAP = {
    f"{slug}-{division}": {"url": f"{BASE_URL}/{path}", "fixed_structure": fixed}
    for slug, division, path, fixed in LEAGUE_DEFINITIONS
}

ODDS_FORMAT_MAP = {
    "eu": "Decimal Odds (1.50)",
    "us": "Money Line Odds (-200)",
    "uk": "Fractional Odds (1/2)",
    "hk": "Hong Kong Odds (0.50)",
    "ma": "Malay Odds (0.50)",
    "in": "Indonesian Odds (-2.00)",
}

__all__ = ["BASE_URL", "LEAGUE_DEFINITIONS", "LEAGUES_URLS_MAP", "ODDS_FORMAT_MAP"]
