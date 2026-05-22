"""Recupera le quote in tempo reale via The Odds API — Serie B."""
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import ODDS_API_KEY, ODDS_API_URL


def get_upcoming_odds() -> list[dict]:
    """Recupera le quote delle prossime partite di Serie A.

    Returns:
        Lista di partite, ognuna con:
        - home_team, away_team, commence_time
        - odds: {"B365H": float, "B365D": float, "B365A": float, ...}

    Raises:
        ValueError: Se la API key non è configurata.
        requests.HTTPError: Se la chiamata API fallisce.
    """
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY non configurata nel file .env")

    resp = requests.get(
        ODDS_API_URL,
        params={
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for event in data:
        match = {
            "home_team": event["home_team"],
            "away_team": event["away_team"],
            "commence_time": event["commence_time"],
            "odds": {},
        }

        # Mappa i bookmaker dell'API ai prefissi usati nel modello
        bk_map = {
            "bet365":      "B365",
            "williamhill": "WH",
            "pinnacle":    "PS",
            "interwetten": "IW",
        }

        for bookmaker in event.get("bookmakers", []):
            key = bookmaker["key"]
            prefix = bk_map.get(key)
            if not prefix:
                continue
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                home = event["home_team"]
                away = event["away_team"]
                if home in outcomes and away in outcomes and "Draw" in outcomes:
                    match["odds"][f"{prefix}H"] = outcomes[home]
                    match["odds"][f"{prefix}D"] = outcomes["Draw"]
                    match["odds"][f"{prefix}A"] = outcomes[away]

        if match["odds"]:
            matches.append(match)

    return matches


def get_mock_odds() -> list[dict]:
    """Dati di esempio per testare l'UI senza API key."""
    return [
        {
            "home_team": "Inter",
            "away_team": "Milan",
            "commence_time": "2026-05-10T19:45:00Z",
            "odds": {
                "B365H": 2.10, "B365D": 3.40, "B365A": 3.20,
                "WHH":   2.05, "WHD":   3.30, "WHA":   3.25,
                "PSH":   2.15, "PSD":   3.45, "PSA":   3.15,
            },
        },
        {
            "home_team": "Juventus",
            "away_team": "Napoli",
            "commence_time": "2026-05-11T20:45:00Z",
            "odds": {
                "B365H": 1.85, "B365D": 3.60, "B365A": 4.20,
                "WHH":   1.80, "WHD":   3.50, "WHA":   4.30,
                "PSH":   1.88, "PSD":   3.65, "PSA":   4.10,
            },
        },
    ]
