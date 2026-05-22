"""
Analisi value betting su dati storici Serie A.

Obiettivo: trovare segmenti di partite dove il bookmaker è affidabile
e il valore atteso (EV) è positivo.

Esegui con:
    cd /home/egiabot/PROJECT/seriea-predictor
    PYTHONPATH=. python notebooks/analisi_value_betting.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import DATA_PROCESSED

df = pd.read_csv(DATA_PROCESSED / "dataset.csv")
print(f"Partite totali: {len(df)}")
print(f"Distribuzione risultati:\n{df['result'].value_counts()}\n")

# ─────────────────────────────────────────────────────────────────────────────
# 1. ACCURATEZZA BASELINE DEL BOOKMAKER
# Il bookmaker "azzecca" quando l'esito con prob implicita più alta è quello reale
# ─────────────────────────────────────────────────────────────────────────────
df["bk_prediction"] = df[["prob_H", "prob_D", "prob_A"]].idxmax(axis=1).str[-1]  # H, D, A
df["bk_correct"] = df["bk_prediction"] == df["result"]

print("=" * 60)
print("1. ACCURATEZZA BASELINE BOOKMAKER")
print("=" * 60)
print(f"Accuratezza globale: {df['bk_correct'].mean():.1%}")
print(f"  - Quando predice H: {df[df['bk_prediction']=='H']['bk_correct'].mean():.1%} ({(df['bk_prediction']=='H').sum()} partite)")
print(f"  - Quando predice D: {df[df['bk_prediction']=='D']['bk_correct'].mean():.1%} ({(df['bk_prediction']=='D').sum()} partite)")
print(f"  - Quando predice A: {df[df['bk_prediction']=='A']['bk_correct'].mean():.1%} ({(df['bk_prediction']=='A').sum()} partite)")

# ─────────────────────────────────────────────────────────────────────────────
# 2. CALIBRAZIONE PER FASCIA DI PROBABILITÀ
# Per ogni fascia di prob_H, quante volte vince davvero la casa?
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. CALIBRAZIONE BOOKMAKER (prob_H vs win rate reale)")
print("=" * 60)

bins = [0.0, 0.35, 0.45, 0.55, 0.65, 0.75, 1.0]
labels = ["<35%", "35-45%", "45-55%", "55-65%", "65-75%", ">75%"]
df["prob_H_bin"] = pd.cut(df["prob_H"], bins=bins, labels=labels)

cal = df.groupby("prob_H_bin", observed=True).agg(
    n=("result", "count"),
    win_rate=("result", lambda x: (x == "H").mean()),
    prob_H_mean=("prob_H", "mean"),
    quota_H_mean=("B365_H", "mean"),  # quota media Bet365 come proxy
).round(3)
cal["EV"] = (cal["win_rate"] * cal["quota_H_mean"] - 1).round(3)
cal["EV_positivo"] = cal["EV"] > 0
print(cal.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# 3. EFFETTO DELLA VARIANZA (std_H) SULL'AFFIDABILITÀ
# Le partite con std bassa sono più prevedibili?
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. AFFIDABILITÀ VS VARIANZA TRA BOOKMAKER (std_H)")
print("=" * 60)

std_bins = df["std_H"].quantile([0, 0.25, 0.5, 0.75, 1.0]).values
std_labels = ["Q1 (bassa)", "Q2", "Q3", "Q4 (alta)"]
df["std_H_bin"] = pd.cut(df["std_H"], bins=std_bins, labels=std_labels, include_lowest=True)

std_cal = df.groupby("std_H_bin", observed=True).agg(
    n=("result", "count"),
    bk_accuracy=("bk_correct", "mean"),
    std_H_mean=("std_H", "mean"),
).round(3)
print(std_cal.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# 4. SEGMENTI COMBINATI: prob alta + std bassa
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. SEGMENTI COMBINATI (prob alta + std bassa)")
print("=" * 60)

# Per ogni esito (H, D, A), calcola le metriche per il segmento "alta prob + bassa std"
for outcome, prob_col, std_col, quota_col in [
    ("H", "prob_H", "std_H", "B365_H"),
    ("A", "prob_A", "std_A", "B365_A"),
    ("D", "prob_D", "std_D", "B365_D"),
]:
    prob_thresh = 0.55
    std_thresh = df[std_col].quantile(0.5)  # metà inferiore della distribuzione

    mask = (df[prob_col] > prob_thresh) & (df[std_col] < std_thresh)
    seg = df[mask]

    if len(seg) < 10:
        continue

    win_rate = (seg["result"] == outcome).mean()
    quota_mean = seg[quota_col].mean()
    ev = win_rate * quota_mean - 1

    print(f"\nEsito {outcome} | prob>{prob_thresh:.0%} + std<{std_thresh:.3f}")
    print(f"  Partite nel segmento: {len(seg)}")
    print(f"  Win rate reale:       {win_rate:.1%}")
    print(f"  Prob implicita media: {seg[prob_col].mean():.1%}")
    print(f"  Quota media (B365):   {quota_mean:.2f}")
    print(f"  EV atteso:            {ev:+.3f}  {'✅ POSITIVO' if ev > 0 else '❌ negativo'}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. BACKTEST FLAT BETTING
# Simula: scommetti 1€ su ogni partita che soddisfa i criteri
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("5. BACKTEST FLAT BETTING (1€ per scommessa)")
print("=" * 60)

def backtest(df, outcome, prob_col, std_col, quota_col, prob_thresh, std_thresh):
    mask = (df[prob_col] > prob_thresh) & (df[std_col] < std_thresh)
    seg = df[mask].copy()
    seg["win"] = seg["result"] == outcome
    seg["pnl"] = seg.apply(lambda r: r[quota_col] - 1 if r["win"] else -1, axis=1)

    n = len(seg)
    wins = seg["win"].sum()
    total_pnl = seg["pnl"].sum()
    roi = total_pnl / n if n > 0 else 0

    return {"n": n, "wins": wins, "win_rate": wins/n if n > 0 else 0,
            "total_pnl": total_pnl, "roi": roi}

# Griglia di soglie
for prob_thresh in [0.50, 0.55, 0.60, 0.65]:
    for std_q in [0.25, 0.50]:
        for outcome, prob_col, std_col, quota_col in [
            ("H", "prob_H", "std_H", "B365_H"),
            ("A", "prob_A", "std_A", "B365_A"),
        ]:
            std_thresh = df[std_col].quantile(std_q)
            r = backtest(df, outcome, prob_col, std_col, quota_col, prob_thresh, std_thresh)
            if r["n"] >= 20:
                print(f"  {outcome} | prob>{prob_thresh:.0%} std<Q{int(std_q*100)} | "
                      f"n={r['n']:3d} | win={r['win_rate']:.1%} | "
                      f"ROI={r['roi']:+.3f} | P&L={r['total_pnl']:+.1f}€")

# ─────────────────────────────────────────────────────────────────────────────
# 6. MIGLIORI SEGMENTI (ROI > 0)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("6. RIEPILOGO: SEGMENTI CON ROI POSITIVO")
print("=" * 60)

results = []
for prob_thresh in np.arange(0.45, 0.80, 0.05):
    for std_q in [0.25, 0.33, 0.50, 0.75]:
        for outcome, prob_col, std_col, quota_col in [
            ("H", "prob_H", "std_H", "B365_H"),
            ("A", "prob_A", "std_A", "B365_A"),
            ("D", "prob_D", "std_D", "B365_D"),
        ]:
            std_thresh = df[std_col].quantile(std_q)
            r = backtest(df, outcome, prob_col, std_col, quota_col, prob_thresh, std_thresh)
            if r["n"] >= 15 and r["roi"] > 0:
                results.append({
                    "esito": outcome,
                    "prob_min": f"{prob_thresh:.0%}",
                    "std_max_quantile": f"Q{int(std_q*100)}",
                    "n": r["n"],
                    "win_rate": f"{r['win_rate']:.1%}",
                    "ROI": f"{r['roi']:+.3f}",
                    "P&L_totale": f"{r['total_pnl']:+.1f}€",
                })

if results:
    top = pd.DataFrame(results).sort_values("ROI", ascending=False).head(15)
    print(top.to_string(index=False))
else:
    print("Nessun segmento con ROI positivo trovato.")

# ─────────────────────────────────────────────────────────────────────────────
# 7. STABILITÀ ROI PER STAGIONE
# Verifica che il +10.2% del filtro base non sia concentrato in 1-2 stagioni
# Filtro: prob_A > 0.45 AND std_A < 0.0417
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("7. STABILITÀ ROI PER STAGIONE (filtro: prob_A>45% + std_A<0.0417)")
print("=" * 60)

PROB_MIN = 0.45
STD_MAX  = 0.0417

mask_vb = (df["prob_A"] > PROB_MIN) & (df["std_A"] < STD_MAX)
vb = df[mask_vb].copy()
vb["win"] = vb["result"] == "A"
vb["pnl"] = vb.apply(lambda r: r["B365_A"] - 1 if r["win"] else -1, axis=1)

season_stats = vb.groupby("season").agg(
    partite=("result", "count"),
    vinte=("win", "sum"),
    pnl=("pnl", "sum"),
).assign(
    win_rate=lambda x: x["vinte"] / x["partite"],
    roi=lambda x: x["pnl"] / x["partite"],
).round(3)

print(season_stats.to_string())
print(f"\nTotale: {len(vb)} partite | Win rate: {vb['win'].mean():.1%} | ROI: {vb['pnl'].sum()/len(vb):+.3f}")

# Segnala se il ROI è concentrato
roi_per_season = season_stats["roi"]
print(f"\nROI min stagione: {roi_per_season.min():+.3f}")
print(f"ROI max stagione: {roi_per_season.max():+.3f}")
n_positive = (roi_per_season > 0).sum()
print(f"Stagioni con ROI positivo: {n_positive}/{len(roi_per_season)}")
if n_positive <= 1:
    print("⚠️  ATTENZIONE: il ROI è concentrato in pochissime stagioni — segnale fragile")
elif n_positive >= len(roi_per_season) - 1:
    print("✅ ROI positivo in quasi tutte le stagioni — segnale robusto")
else:
    print("⚠️  ROI misto — usare con cautela")
