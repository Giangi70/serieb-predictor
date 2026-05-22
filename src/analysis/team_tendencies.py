"""Calcola le tendenze stagionali delle squadre dalla prima metà della stagione.

Uso:
    tendencies = compute_tendencies(df_first_half)
    label = get_team_label(tendencies, "Inter", venue="home")
    # → "high_win" | "high_draw" | "high_loss" | None
"""
import pandas as pd

# Soglie per classificare una squadra come "tende a X"
# (calibrabili — basate su distribuzione attesa ~27% draw, ~45% win, ~28% loss)
THRESHOLDS = {
    "high_draw":  0.35,   # pareggia > 35% delle partite
    "high_win":   0.55,   # vince > 55% delle partite
    "high_loss":  0.45,   # perde > 45% delle partite
}


def compute_tendencies(df: pd.DataFrame) -> pd.DataFrame:
    """Calcola i tassi di vittoria/pareggio/sconfitta per ogni squadra e venue.

    Args:
        df: DataFrame con colonne home_team, away_team, result.
            Tipicamente la prima metà di una stagione.

    Returns:
        DataFrame indicizzato per (team, venue) con colonne:
        n, win_rate, draw_rate, loss_rate, tendency.
        venue è 'home' o 'away'.
    """
    records = []
    for _, row in df.iterrows():
        h, a, r = row["home_team"], row["away_team"], row["result"]
        records.append({"team": h, "venue": "home",
                        "win": r == "H", "draw": r == "D", "loss": r == "A"})
        records.append({"team": a, "venue": "away",
                        "win": r == "A", "draw": r == "D", "loss": r == "H"})

    stats = pd.DataFrame(records).groupby(["team", "venue"]).agg(
        n=("win", "count"),
        win_rate=("win", "mean"),
        draw_rate=("draw", "mean"),
        loss_rate=("loss", "mean"),
    ).round(3)

    def classify(row):
        if row["draw_rate"] >= THRESHOLDS["high_draw"]:
            return "high_draw"
        if row["win_rate"] >= THRESHOLDS["high_win"]:
            return "high_win"
        if row["loss_rate"] >= THRESHOLDS["high_loss"]:
            return "high_loss"
        return None

    stats["tendency"] = stats.apply(classify, axis=1)
    return stats


def get_team_label(tendencies: pd.DataFrame, team: str, venue: str) -> str | None:
    """Restituisce la tendenza di una squadra per un dato venue.

    Args:
        tendencies: Output di compute_tendencies().
        team: Nome squadra.
        venue: 'home' o 'away'.

    Returns:
        'high_draw' | 'high_win' | 'high_loss' | None
    """
    try:
        return tendencies.loc[(team, venue), "tendency"]
    except KeyError:
        return None


def split_season(df: pd.DataFrame, season: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide le partite di una stagione in prima e seconda metà per data.

    Returns:
        (first_half, second_half)
    """
    s = df[df["season"] == season].copy()
    s["date"] = pd.to_datetime(s["date"], dayfirst=True)
    s = s.sort_values("date")
    mid = len(s) // 2
    return s.iloc[:mid], s.iloc[mid:]
