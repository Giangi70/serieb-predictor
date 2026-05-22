"""Aggiorna automaticamente i risultati delle predizioni dai CSV storici."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import DATA_RAW, SEASONS
from src.db.storage import get_pending_predictions, set_result

# Mapping nomi squadra: come arrivano dall'API → come sono nei CSV
TEAM_NAME_MAP = {
    "AC Milan": "Milan",
    "Inter Milan": "Inter",
    "Hellas Verona": "Verona",
    "Atalanta BC": "Atalanta",
    "AS Roma": "Roma",
    "SSC Napoli": "Napoli",
    "SS Lazio": "Lazio",
}


def _normalize(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name).lower().strip()


def _load_csv_results() -> pd.DataFrame:
    """Carica tutti i CSV storici con date, squadre e risultato FTR."""
    frames = []
    for season in SEASONS:
        path = DATA_RAW / f"serie_a_{season}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, encoding="latin-1", usecols=["Date", "HomeTeam", "AwayTeam", "FTR"])
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).dropna(subset=["FTR"])


def auto_update_results() -> dict:
    """Cerca i risultati mancanti nei CSV e li aggiorna nel DB.

    Returns:
        dict con: updated (int), still_missing (int), details (list[str])
    """
    pending = get_pending_predictions()
    if not pending:
        return {"updated": 0, "still_missing": 0, "details": []}

    csv_df = _load_csv_results()
    if csv_df.empty:
        return {"updated": 0, "still_missing": len(pending), "details": ["CSV non trovati in data/raw/"]}

    updated, still_missing, details = 0, 0, []

    for pred in pending:
        home_norm = _normalize(pred["home_team"])
        away_norm = _normalize(pred["away_team"])

        mask = (
            csv_df["HomeTeam"].str.lower().str.strip() == home_norm
        ) & (
            csv_df["AwayTeam"].str.lower().str.strip() == away_norm
        )
        match = csv_df[mask]

        if match.empty:
            still_missing += 1
            details.append(f"⏳ Non ancora nei CSV: {pred['home_team']} vs {pred['away_team']}")
        else:
            result = match.iloc[-1]["FTR"]
            set_result(pred["id"], result)
            updated += 1
            details.append(f"✅ {pred['home_team']} vs {pred['away_team']} → {result}")

    return {"updated": updated, "still_missing": still_missing, "details": details}
