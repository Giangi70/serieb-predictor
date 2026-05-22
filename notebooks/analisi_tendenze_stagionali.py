"""
Backtest del segnale combinato: filtro value betting + tendenze stagionali.

Metodologia:
- Per ogni stagione: prima metà → classifica squadre → seconda metà → backtest
- Confronta ROI del solo filtro base vs filtro base + tendenza stagionale

Esegui con:
    cd /home/egiabot/PROJECT/seriea-predictor
    PYTHONPATH=. python notebooks/analisi_tendenze_stagionali.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import DATA_PROCESSED
from src.analysis.team_tendencies import compute_tendencies, get_team_label, split_season

df = pd.read_csv(DATA_PROCESSED / "dataset.csv")
SEASONS = df["season"].unique()

# ─────────────────────────────────────────────────────────────────────────────
# 1. QUANTE SQUADRE VENGONO CLASSIFICATE PER STAGIONE?
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("1. CLASSIFICAZIONE SQUADRE (prima metà stagione)")
print("=" * 60)

for season in sorted(SEASONS):
    first, second = split_season(df, season)
    tend = compute_tendencies(first)
    classified = tend[tend["tendency"].notna()]
    counts = classified["tendency"].value_counts()
    print(f"\nStagione {season} | prima metà: {len(first)} partite")
    print(f"  Squadre classificate: {len(classified)}")
    for label, n in counts.items():
        print(f"    {label}: {n}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. LA TENDENZA SI MANTIENE NELLA SECONDA METÀ?
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. PERSISTENZA DELLA TENDENZA (prima → seconda metà)")
print("=" * 60)

persistence = {"high_draw": [], "high_win": [], "high_loss": []}

for season in sorted(SEASONS):
    first, second = split_season(df, season)
    tend_first = compute_tendencies(first)
    tend_second = compute_tendencies(second)

    for (team, venue), row in tend_first[tend_first["tendency"].notna()].iterrows():
        label_first = row["tendency"]
        label_second = get_team_label(tend_second, team, venue)
        if label_second is not None:
            persistence[label_first].append(label_first == label_second)

print("\nConferma tendenza nella seconda metà:")
for label, matches in persistence.items():
    if matches:
        rate = np.mean(matches)
        print(f"  {label}: {rate:.1%} ({sum(matches)}/{len(matches)} squadre)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. BACKTEST: FILTRO BASE vs FILTRO BASE + TENDENZA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. BACKTEST SECONDA METÀ STAGIONE")
print("=" * 60)

# Parametri filtro base (dal notebook precedente: miglior ROI su trasferta)
PROB_THRESH = 0.50
STD_QUANTILE = 0.33

all_base, all_combined = [], []

for season in sorted(SEASONS):
    first, second = split_season(df, season)
    tend = compute_tendencies(first)

    # Calcola soglia std sul dataset completo della stagione (non solo seconda metà)
    season_df = df[df["season"] == season]
    std_thresh = season_df["std_A"].quantile(STD_QUANTILE)

    for _, row in second.iterrows():
        # Filtro base: prob_A alta + std_A bassa
        base_ok = row["prob_A"] > PROB_THRESH and row["std_A"] < std_thresh
        if not base_ok:
            continue

        win = row["result"] == "A"
        quota = row.get("B365_A", np.nan)
        if pd.isna(quota):
            continue

        pnl = quota - 1 if win else -1
        all_base.append({"season": season, "win": win, "pnl": pnl})

        # Segnale aggiuntivo: la squadra in trasferta tende a vincere fuori casa?
        away_tendency = get_team_label(tend, row["away_team"], "away")
        if away_tendency == "high_win":
            all_combined.append({"season": season, "win": win, "pnl": pnl})

base_df = pd.DataFrame(all_base)
comb_df = pd.DataFrame(all_combined)

def summarize(label, data):
    if data.empty:
        print(f"  {label}: nessuna scommessa")
        return
    n = len(data)
    wins = data["win"].sum()
    total_pnl = data["pnl"].sum()
    roi = total_pnl / n
    print(f"  {label}: n={n} | win={wins/n:.1%} | ROI={roi:+.3f} | P&L={total_pnl:+.1f}€")

print(f"\nScommesse sulla trasferta (A) nella seconda metà stagione:")
summarize("Solo filtro base (prob>50%, std<Q33)", base_df)
summarize("Filtro base + high_win_away         ", comb_df)

# ─────────────────────────────────────────────────────────────────────────────
# 4. BACKTEST PER TUTTE LE TENDENZE E COMBINAZIONI
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. BACKTEST COMPLETO PER TENDENZA")
print("=" * 60)

results = []
for outcome, prob_col, std_col, quota_col, venue in [
    ("H", "prob_H", "std_H", "B365_H", "home"),
    ("A", "prob_A", "std_A", "B365_A", "away"),
    ("D", "prob_D", "std_D", "B365_D", None),
]:
    for tendency in ["high_win", "high_draw", "high_loss"]:
        bets = []
        for season in sorted(SEASONS):
            first, second = split_season(df, season)
            tend = compute_tendencies(first)
            std_thresh = df[df["season"] == season][std_col].quantile(STD_QUANTILE)

            for _, row in second.iterrows():
                if row[prob_col] <= PROB_THRESH or row[std_col] >= std_thresh:
                    continue
                quota = row.get(quota_col, np.nan)
                if pd.isna(quota):
                    continue

                # Controlla tendenza squadra rilevante
                if venue:
                    team = row["home_team"] if venue == "home" else row["away_team"]
                    t = get_team_label(tend, team, venue)
                else:
                    # Per il pareggio: almeno una delle due squadre tende al pareggio
                    th = get_team_label(tend, row["home_team"], "home")
                    ta = get_team_label(tend, row["away_team"], "away")
                    t = "high_draw" if (th == "high_draw" or ta == "high_draw") else None

                if t != tendency:
                    continue

                win = row["result"] == outcome
                bets.append(quota - 1 if win else -1)

        if len(bets) >= 10:
            roi = sum(bets) / len(bets)
            results.append({
                "esito": outcome, "tendenza": tendency,
                "n": len(bets), "win_rate": f"{sum(b>0 for b in bets)/len(bets):.1%}",
                "ROI": f"{roi:+.3f}", "P&L": f"{sum(bets):+.1f}€",
            })

if results:
    res_df = pd.DataFrame(results).sort_values("ROI", ascending=False)
    print(res_df.to_string(index=False))
else:
    print("Nessun segmento con abbastanza dati.")
