"""Static constants shared across the scraper."""

BASE_URL = "https://www.oddsportal.com"

LEAGUES_URLS_MAP = {
    "premier-league": {"url": f"{BASE_URL}/soccer/england/premier-league", "fixed_structure": False},
    "ligue-1": {"url": f"{BASE_URL}/soccer/france/ligue-1", "fixed_structure": False},
    "bundesliga": {"url": f"{BASE_URL}/soccer/germany/bundesliga", "fixed_structure": False},
    "championship": {"url": f"{BASE_URL}/football/england/championship", "fixed_structure": False},
    "liga": {"url": f"{BASE_URL}/football/spain/laliga", "fixed_structure": False},
    "serie-a": {"url": f"{BASE_URL}/football/italy/serie-a", "fixed_structure": False},
    "mls": {"url": f"{BASE_URL}/football/usa/mls", "fixed_structure": True},
    "brazil-serie-a": {"url": f"{BASE_URL}/football/brazil/serie-a", "fixed_structure": False},
    "liga-mx": {"url": f"{BASE_URL}/football/mexico/liga-mx", "fixed_structure": False},
    "liga-portugal": {"url": f"{BASE_URL}/football/portugal/liga-portugal", "fixed_structure": False},
    "eredivisie": {"url": f"{BASE_URL}/football/netherlands/eredivisie", "fixed_structure": False},
    "belgian": {"url": f"{BASE_URL}/football/belgium/jupiler-pro-league", "fixed_structure": False},
    "ligue2": {"url": f"{BASE_URL}/football/france/ligue-2", "fixed_structure": False},
    "serie-b": {"url": f"{BASE_URL}/football/italy/serie-b", "fixed_structure": False},
    "liga2": {"url": f"{BASE_URL}/football/spain/laliga2", "fixed_structure": False},
    "bundesliga-2": {"url": f"{BASE_URL}/football/germany/2-bundesliga", "fixed_structure": False},
    "argentina": {"url": f"{BASE_URL}/football/argentina/liga-profesional", "fixed_structure": False},
    "champions-league": {"url": f"{BASE_URL}/football/europe/champions-league", "fixed_structure": False},
    "europa-league": {"url": f"{BASE_URL}/football/europe/europa-league", "fixed_structure": False},
    "allsvenskan": {"url": f"{BASE_URL}/football/sweden/allsvenskan", "fixed_structure": True},
}

ODDS_FORMAT_MAP = {
    "eu": "Decimal Odds (1.50)",
    "us": "Money Line Odds (-200)",
    "uk": "Fractional Odds (1/2)",
    "hk": "Hong Kong Odds (0.50)",
    "ma": "Malay Odds (0.50)",
    "in": "Indonesian Odds (-2.00)",
}

__all__ = ["BASE_URL", "LEAGUES_URLS_MAP", "ODDS_FORMAT_MAP"]
