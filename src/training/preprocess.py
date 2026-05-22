"""Carica e prepara i dati storici per il training."""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import DATA_RAW, DATA_PROCESSED, SEASONS, BOOKMAKERS

# Colonne quote per ogni bookmaker: Home, Draw, Away
ODDS_COLS = {bk: [f"{bk}H", f"{bk}D", f"{bk}A"] for bk in BOOKMAKERS}


def load_raw() -> pd.DataFrame:
    """Carica e concatena tutti i CSV storici disponibili."""
    frames = []
    for season in SEASONS:
        path = DATA_RAW / f"serie_b_{season}.csv"
        if not path.exists():
            print(f"[WARN] {path.name} non trovato, skip")
            continue
        df = pd.read_csv(path, encoding="latin-1")
        df["season"] = season
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Costruisce le feature dal DataFrame grezzo.

    Feature:
    - Quote H/D/A di ogni bookmaker disponibile
    - Probabilità implicite normalizzate (rimuove il vig)
    - Media e deviazione standard delle quote tra bookmaker
    - Divergenza massima tra bookmaker (segnale di incertezza)

    Returns:
        DataFrame con colonne feature + target 'result' (H/D/A).
    """
    rows = []
    for _, row in df.iterrows():
        feat: dict = {}

        # Raccoglie le quote disponibili per questa partita
        odds_h, odds_d, odds_a = [], [], []
        for bk, cols in ODDS_COLS.items():
            h, d, a = row.get(cols[0]), row.get(cols[1]), row.get(cols[2])
            if pd.notna(h) and pd.notna(d) and pd.notna(a) and h > 1 and d > 1 and a > 1:
                feat[f"{bk}_H"] = h
                feat[f"{bk}_D"] = d
                feat[f"{bk}_A"] = a
                odds_h.append(h)
                odds_d.append(d)
                odds_a.append(a)

        if len(odds_h) < 2:  # serve almeno 2 bookmaker
            continue

        # Probabilità implicite medie (normalizzate per rimuovere il vig)
        def implied_prob(odds_list: list[float]) -> float:
            raw = np.mean([1 / o for o in odds_list])
            total = np.mean([1/h + 1/d + 1/a for h, d, a in zip(odds_h, odds_d, odds_a)])
            return raw / total

        feat["prob_H"] = implied_prob(odds_h)
        feat["prob_D"] = implied_prob(odds_d)
        feat["prob_A"] = implied_prob(odds_a)

        # Statistiche tra bookmaker
        feat["std_H"] = np.std(odds_h)
        feat["std_D"] = np.std(odds_d)
        feat["std_A"] = np.std(odds_a)
        feat["divergence"] = max(
            max(odds_h) - min(odds_h),
            max(odds_d) - min(odds_d),
            max(odds_a) - min(odds_a),
        )
        feat["n_bookmakers"] = len(odds_h)

        feat["result"] = row.get("FTR")  # H / D / A
        feat["season"] = row.get("season")
        feat["date"] = row.get("Date")
        feat["home_team"] = row.get("HomeTeam")
        feat["away_team"] = row.get("AwayTeam")
        rows.append(feat)

    result_df = pd.DataFrame(rows).dropna(subset=["result"])
    result_df = result_df[result_df["result"].isin(["H", "D", "A"])]
    return result_df.reset_index(drop=True)


def save_processed(df: pd.DataFrame) -> Path:
    """Salva il dataset processato in data/processed/."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "dataset.csv"
    df.to_csv(out, index=False)
    print(f"[OK] Dataset salvato: {out} ({len(df)} righe)")
    return out


def run() -> pd.DataFrame:
    """Pipeline completa: carica → trasforma → salva."""
    raw = load_raw()
    print(f"[INFO] Righe grezze: {len(raw)}")
    processed = build_features(raw)
    print(f"[INFO] Righe dopo preprocessing: {len(processed)}")
    print(f"[INFO] Distribuzione risultati:\n{processed['result'].value_counts()}")
    save_processed(processed)
    return processed


if __name__ == "__main__":
    run()
