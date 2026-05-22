"""
Analisi strategia mista: N_safe partite sull'esito più probabile + N_jolly sulla quota più alta.

Budget fisso: 1€ per scommessa.
Ogni giornata: scelgo le N_safe partite con prob_max più alta → scommetto sull'esito più probabile.
              scelgo le N_jolly partite con quota_max più alta → scommetto sull'esito con quota massima.

Parametri esplorati:
  - N_safe: 6, 7, 8, 9, 10
  - N_jolly: 0, 1, 2, 3
  - min_prob: soglia minima su prob_max per includere una partita nel pool "safe"
  - min_quota_jolly: quota minima per considerare un jolly
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Carica CSV grezzi (tutte le stagioni disponibili) ───────────────────────
# Legge direttamente i CSV raw per non dipendere dal dataset processato del progetto.
RAW_DIR = Path(__file__).parent.parent / "data/raw"
ALL_SEASONS = ["1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]

QUOTE_COLS_RAW = {
    "H": ["B365H", "WHH", "IWH", "PSH", "VCH"],
    "D": ["B365D", "WHD", "IWD", "PSD", "VCD"],
    "A": ["B365A", "WHA", "IWA", "PSA", "VCA"],
}

def load_season(season: str) -> pd.DataFrame:
    path = RAW_DIR / f"serie_a_{season}.csv"
    if not path.exists():
        return pd.DataFrame()
    raw = pd.read_csv(path, dayfirst=True)
    raw["season"] = season
    # Normalizza nomi colonne: rimuovi spazi
    raw.columns = raw.columns.str.strip()
    # Tieni solo le righe con FTR valido
    raw = raw[raw["FTR"].isin(["H", "D", "A"])].copy()
    raw["date"] = pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce")
    raw = raw.dropna(subset=["date"])
    # Calcola prob implicite medie e std per ogni esito
    for esito in ["H", "D", "A"]:
        cols = QUOTE_COLS_RAW[esito]
        vals = raw[[c for c in cols if c in raw.columns]].apply(pd.to_numeric, errors="coerce")
        raw[f"prob_{esito}"] = (1.0 / vals).mean(axis=1)
        raw[f"std_{esito}"] = vals.std(axis=1)
    # Normalizza prob (rimuovi vig)
    tot = raw["prob_H"] + raw["prob_D"] + raw["prob_A"]
    for esito in ["H", "D", "A"]:
        raw[f"prob_{esito}"] = raw[f"prob_{esito}"] / tot
    raw["result"] = raw["FTR"]
    return raw

frames = [load_season(s) for s in ALL_SEASONS]
df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
df = df.sort_values("date").reset_index(drop=True)
print(f"Stagioni caricate: {sorted(df['season'].unique())}")

# Colonne quote grezze disponibili
QUOTE_COLS = {
    "H": ["B365H", "WHH", "IWH", "PSH", "VCH"],
    "D": ["B365D", "WHD", "IWD", "PSD", "VCD"],
    "A": ["B365A", "WHA", "IWA", "PSA", "VCA"],
}

# Per ogni partita: prob_max (esito più probabile) e quota_max (quota più alta disponibile)
def best_outcome(row):
    """Restituisce l'esito con probabilità più alta."""
    probs = {"H": row["prob_H"], "D": row["prob_D"], "A": row["prob_A"]}
    return max(probs, key=probs.get)

def max_quota(row):
    """Restituisce (esito, quota) con la quota più alta tra tutti i bookmaker e tutti gli esiti."""
    best_esito, best_q = None, 0.0
    for esito, cols in QUOTE_COLS.items():
        for col in cols:
            if col in row.index:
                v = pd.to_numeric(row[col], errors="coerce")
                if pd.notna(v) and v > best_q:
                    best_q = v
                    best_esito = esito
    return best_esito, best_q

def quota_for_outcome(row, esito):
    """Quota media per un dato esito."""
    cols = QUOTE_COLS[esito]
    vals = [pd.to_numeric(row[c], errors="coerce") for c in cols if c in row.index]
    vals = [v for v in vals if pd.notna(v) and v > 0]
    return np.mean(vals) if vals else np.nan

df["best_outcome"] = df.apply(best_outcome, axis=1)
df["prob_max"] = df[["prob_H", "prob_D", "prob_A"]].max(axis=1)
df["quota_best_outcome"] = df.apply(lambda r: quota_for_outcome(r, r["best_outcome"]), axis=1)

jolly_info = df.apply(max_quota, axis=1)
df["jolly_esito"] = [x[0] for x in jolly_info]
df["jolly_quota"] = [x[1] for x in jolly_info]

# ── Raggruppa per giornata (stessa data = stessa giornata) ──────────────────
# Usiamo la data come proxy di giornata (partite dello stesso weekend)
# Raggruppiamo date entro 3 giorni per coprire anticipi/posticipi
df = df.sort_values("date").reset_index(drop=True)
df["giornata_id"] = (df["date"].diff().dt.days.fillna(0) > 3).cumsum()

giornate = df.groupby("giornata_id")
print(f"Dataset: {len(df)} partite, {df['giornata_id'].nunique()} giornate\n")

# ── Simulazione ─────────────────────────────────────────────────────────────
def simula(n_safe, n_jolly, min_prob=0.0, min_quota_jolly=1.0):
    """
    Simula la strategia su tutte le giornate.
    Restituisce dict con metriche aggregate.
    """
    pl_giornate = []
    scommesse_totali = 0

    for gid, g in giornate:
        # Pool safe: partite con prob_max >= min_prob, ordinate per prob_max desc
        pool_safe = g[g["prob_max"] >= min_prob].sort_values("prob_max", ascending=False)
        # Pool jolly: partite con jolly_quota >= min_quota_jolly, ordinate per jolly_quota desc
        pool_jolly = g[g["jolly_quota"] >= min_quota_jolly].sort_values("jolly_quota", ascending=False)

        if len(pool_safe) < n_safe or (n_jolly > 0 and len(pool_jolly) < n_jolly):
            pl_giornate.append(None)  # giornata saltata
            continue

        pl = 0.0
        n_scommesse = 0

        # Scommesse safe
        for _, row in pool_safe.head(n_safe).iterrows():
            pl -= 1.0  # pago 1€
            n_scommesse += 1
            if row["result"] == row["best_outcome"]:
                pl += row["quota_best_outcome"]

        # Scommesse jolly
        for _, row in pool_jolly.head(n_jolly).iterrows():
            pl -= 1.0
            n_scommesse += 1
            if row["result"] == row["jolly_esito"]:
                pl += row["jolly_quota"]

        pl_giornate.append(pl)
        scommesse_totali += n_scommesse

    pl_valide = [x for x in pl_giornate if x is not None]
    giornate_valide = len(pl_valide)
    pl_totale = sum(pl_valide)
    roi = pl_totale / scommesse_totali if scommesse_totali > 0 else 0
    win_rate_giornate = sum(1 for x in pl_valide if x > 0) / giornate_valide if giornate_valide > 0 else 0

    return {
        "n_safe": n_safe,
        "n_jolly": n_jolly,
        "min_prob": min_prob,
        "min_quota_jolly": min_quota_jolly,
        "giornate": giornate_valide,
        "scommesse": scommesse_totali,
        "pl_totale": round(pl_totale, 2),
        "roi": round(roi * 100, 2),
        "win_rate_giornate_%": round(win_rate_giornate * 100, 1),
        "pl_medio_giornata": round(pl_totale / giornate_valide, 3) if giornate_valide else 0,
    }

# ── Griglia parametri ────────────────────────────────────────────────────────
risultati = []
for n_safe, n_jolly, min_prob, min_q_jolly in itertools.product(
    [6, 7, 8, 9, 10],       # n_safe
    [0, 1, 2, 3],            # n_jolly
    [0.0, 0.40, 0.45, 0.50], # min_prob
    [1.0, 3.0, 5.0, 8.0],    # min_quota_jolly
):
    if n_jolly == 0 and min_q_jolly > 1.0:
        continue  # parametro irrilevante
    r = simula(n_safe, n_jolly, min_prob, min_q_jolly)
    risultati.append(r)

res = pd.DataFrame(risultati).drop_duplicates()

# ── Risultati ────────────────────────────────────────────────────────────────
print("=" * 70)
print("TOP 20 combinazioni per ROI")
print("=" * 70)
top = res.sort_values("roi", ascending=False).head(20)
print(top.to_string(index=False))

print("\n" + "=" * 70)
print("TOP 20 combinazioni per P&L totale")
print("=" * 70)
top_pl = res.sort_values("pl_totale", ascending=False).head(20)
print(top_pl.to_string(index=False))

print("\n" + "=" * 70)
print("Strategia base: 10 safe, 0 jolly, nessun filtro")
print("=" * 70)
base = res[(res["n_safe"] == 10) & (res["n_jolly"] == 0) & (res["min_prob"] == 0.0)]
print(base.to_string(index=False))

print("\n" + "=" * 70)
print("Effetto del jolly (n_safe=9, min_prob=0.45)")
print("=" * 70)
jolly_effect = res[(res["n_safe"] == 9) & (res["min_prob"] == 0.45)].sort_values("n_jolly")
print(jolly_effect.to_string(index=False))

# ── Analisi per stagione della strategia migliore ────────────────────────────
print("\n" + "=" * 70)
print("Stabilità per stagione — strategia con ROI massimo")
print("=" * 70)
best = res.sort_values("roi", ascending=False).iloc[0]
print(f"Strategia: n_safe={int(best.n_safe)}, n_jolly={int(best.n_jolly)}, "
      f"min_prob={best.min_prob}, min_quota_jolly={best.min_quota_jolly}\n")

for season, sg in df.groupby("season"):
    giornate_s = sg.groupby("giornata_id")
    r = simula(int(best.n_safe), int(best.n_jolly), best.min_prob, best.min_quota_jolly)
    # Ricalcola solo su questa stagione
    pl_s, scomm_s = 0.0, 0
    for gid, g in giornate_s:
        pool_safe = g[g["prob_max"] >= best.min_prob].sort_values("prob_max", ascending=False)
        pool_jolly = g[g["jolly_quota"] >= best.min_quota_jolly].sort_values("jolly_quota", ascending=False)
        n_safe_i, n_jolly_i = int(best.n_safe), int(best.n_jolly)
        if len(pool_safe) < n_safe_i or (n_jolly_i > 0 and len(pool_jolly) < n_jolly_i):
            continue
        for _, row in pool_safe.head(n_safe_i).iterrows():
            pl_s -= 1.0; scomm_s += 1
            if row["result"] == row["best_outcome"]:
                pl_s += row["quota_best_outcome"]
        for _, row in pool_jolly.head(n_jolly_i).iterrows():
            pl_s -= 1.0; scomm_s += 1
            if row["result"] == row["jolly_esito"]:
                pl_s += row["jolly_quota"]
    roi_s = pl_s / scomm_s * 100 if scomm_s else 0
    print(f"  Stagione {season}: P&L={pl_s:+.1f}€  ROI={roi_s:+.1f}%  ({scomm_s} scommesse)")

# ── IPOTESI 1: Threshold sulla differenza tra prob ───────────────────────────
# Escludiamo le partite "incerte" dove 1/X/2 sono troppo vicine.
# Usiamo come misura: prob_max - prob_seconda (gap tra prima e seconda scelta).
# Più alto il gap, più il bookmaker è "convinto".
print("\n" + "=" * 70)
print("IPOTESI 1 — Effetto del gap prob_max - prob_seconda sulle ultime 3 stagioni")
print("(2223, 2324, 2425 — periodo con ROI basso)")
print("=" * 70)

df_recent = df[df["season"].isin(["2223", "2324", "2425"])].copy()

def prob_gap(row):
    probs = sorted([row["prob_H"], row["prob_D"], row["prob_A"]], reverse=True)
    return probs[0] - probs[1]

df["prob_gap"] = df.apply(prob_gap, axis=1)
df_recent["prob_gap"] = df_recent.apply(prob_gap, axis=1)

# Analisi per fascia di gap: accuratezza bookmaker e ROI safe
for label, lo, hi in [
    ("gap < 0.10 (incerte)",   0.00, 0.10),
    ("gap 0.10-0.20",          0.10, 0.20),
    ("gap 0.20-0.30",          0.20, 0.30),
    ("gap > 0.30 (chiare)",    0.30, 1.00),
]:
    sub = df_recent[(df_recent["prob_gap"] >= lo) & (df_recent["prob_gap"] < hi)]
    if len(sub) == 0:
        continue
    acc = (sub["result"] == sub["best_outcome"]).mean()
    # ROI safe: scommetto 1€ sull'esito più probabile
    pl = sum(row["quota_best_outcome"] - 1 if row["result"] == row["best_outcome"] else -1
             for _, row in sub.iterrows())
    roi = pl / len(sub) * 100
    print(f"  {label:30s}  n={len(sub):4d}  acc={acc:.1%}  ROI={roi:+.1f}%")

# Stessa analisi su tutto il dataset per confronto
print("\n  Confronto su tutte le 9 stagioni:")
for label, lo, hi in [
    ("gap < 0.10",   0.00, 0.10),
    ("gap 0.10-0.20", 0.10, 0.20),
    ("gap 0.20-0.30", 0.20, 0.30),
    ("gap > 0.30",   0.30, 1.00),
]:
    sub = df[(df["prob_gap"] >= lo) & (df["prob_gap"] < hi)]
    if len(sub) == 0:
        continue
    acc = (sub["result"] == sub["best_outcome"]).mean()
    pl = sum(row["quota_best_outcome"] - 1 if row["result"] == row["best_outcome"] else -1
             for _, row in sub.iterrows())
    roi = pl / len(sub) * 100
    print(f"  {label:30s}  n={len(sub):4d}  acc={acc:.1%}  ROI={roi:+.1f}%")

# ── IPOTESI 2: Ciclicità del segnale ─────────────────────────────────────────
# I bookmaker guardano le serie storiche e correggono le inefficienze.
# Ipotesi: il ROI oscilla nel tempo con un pattern ciclico.
# Analizziamo il ROI anno per anno con la strategia base (10 safe, 0 jolly)
# e con la strategia jolly (10+1) per vedere se c'è un pattern.
print("\n" + "=" * 70)
print("IPOTESI 2 — Ciclicità del segnale: ROI per stagione, strategia base vs jolly")
print("=" * 70)
print(f"{'Stagione':>10}  {'ROI base (10+0)':>16}  {'ROI jolly (10+1, q>5)':>22}  {'Diff':>8}  {'Partite':>8}")

season_order = ["1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]
for season in season_order:
    sg = df[df["season"] == season]
    giornate_s = sg.groupby("giornata_id")

    def roi_stagione(n_safe, n_jolly, min_prob, min_q_jolly):
        pl, scomm = 0.0, 0
        for gid, g in giornate_s:
            pool_safe = g[g["prob_max"] >= min_prob].sort_values("prob_max", ascending=False)
            pool_jolly = g[g["jolly_quota"] >= min_q_jolly].sort_values("jolly_quota", ascending=False)
            if len(pool_safe) < n_safe or (n_jolly > 0 and len(pool_jolly) < n_jolly):
                continue
            for _, row in pool_safe.head(n_safe).iterrows():
                pl -= 1.0; scomm += 1
                if row["result"] == row["best_outcome"]:
                    pl += row["quota_best_outcome"]
            for _, row in pool_jolly.head(n_jolly).iterrows():
                pl -= 1.0; scomm += 1
                if row["result"] == row["jolly_esito"]:
                    pl += row["jolly_quota"]
        return (pl / scomm * 100 if scomm else 0), scomm

    roi_base, n_base = roi_stagione(10, 0, 0.0, 1.0)
    roi_jolly, n_jolly_s = roi_stagione(10, 1, 0.40, 5.0)
    diff = roi_jolly - roi_base
    print(f"  {season:>8}  {roi_base:>+14.1f}%  {roi_jolly:>+20.1f}%  {diff:>+6.1f}%  {n_base:>7}")

print("\n  Nota: il 'jolly' aggiunge valore quando ROI_jolly >> ROI_base.")
print("  Se entrambi sono bassi, il mercato è efficiente in quella stagione.")

# ── Analisi gap nelle stagioni recenti con jolly ──────────────────────────────
print("\n" + "=" * 70)
print("IPOTESI 1+2 combinata — Gap alto + jolly nelle ultime 3 stagioni")
print("=" * 70)

def simula_con_gap(data, n_safe, n_jolly, min_gap, min_q_jolly):
    """Simula filtrando per gap minimo tra prob."""
    giornate_loc = data.groupby("giornata_id")
    pl, scomm = 0.0, 0
    for gid, g in giornate_loc:
        pool_safe = g[g["prob_gap"] >= min_gap].sort_values("prob_max", ascending=False)
        pool_jolly = g[g["jolly_quota"] >= min_q_jolly].sort_values("jolly_quota", ascending=False)
        if len(pool_safe) < n_safe or (n_jolly > 0 and len(pool_jolly) < n_jolly):
            continue
        for _, row in pool_safe.head(n_safe).iterrows():
            pl -= 1.0; scomm += 1
            if row["result"] == row["best_outcome"]:
                pl += row["quota_best_outcome"]
        for _, row in pool_jolly.head(n_jolly).iterrows():
            pl -= 1.0; scomm += 1
            if row["result"] == row["jolly_esito"]:
                pl += row["jolly_quota"]
    return (pl / scomm * 100 if scomm else 0), scomm, pl

print(f"\n  Ultime 3 stagioni (2223+2324+2425):")
print(f"  {'min_gap':>8}  {'n_jolly':>8}  {'min_q_jolly':>12}  {'ROI':>8}  {'P&L':>8}  {'Scomm':>7}")
for min_gap, n_jolly, min_q in itertools.product(
    [0.0, 0.10, 0.15, 0.20, 0.25],
    [0, 1],
    [1.0, 5.0, 8.0],
):
    if n_jolly == 0 and min_q > 1.0:
        continue
    roi, scomm, pl = simula_con_gap(df_recent, 10, n_jolly, min_gap, min_q)
    if scomm >= 50:  # solo combinazioni con abbastanza dati
        print(f"  {min_gap:>8.2f}  {n_jolly:>8}  {min_q:>12.1f}  {roi:>+7.1f}%  {pl:>+7.1f}€  {scomm:>7}")


# ── OTTIMIZZAZIONE ROI sulle ultime 3 stagioni ───────────────────────────────
print("\n" + "=" * 70)
print("OTTIMIZZAZIONE — Grid search completa sulle ultime 3 stagioni (2223+2324+2425)")
print("=" * 70)

opt_results = []
for n_safe, n_jolly, min_gap, min_q_jolly in itertools.product(
    [6, 7, 8, 9, 10],
    [0, 1, 2],
    [0.0, 0.10, 0.15, 0.20, 0.25, 0.30],
    [1.0, 3.0, 5.0, 8.0, 10.0],
):
    if n_jolly == 0 and min_q_jolly > 1.0:
        continue
    roi, scomm, pl = simula_con_gap(df_recent, n_safe, n_jolly, min_gap, min_q_jolly)
    if scomm >= 60:
        opt_results.append({
            "n_safe": n_safe, "n_jolly": n_jolly,
            "min_gap": min_gap, "min_q_jolly": min_q_jolly,
            "roi": round(roi, 2), "pl": round(pl, 2), "scommesse": scomm,
        })

opt_df = pd.DataFrame(opt_results)

print("\nTOP 15 per ROI (min 60 scommesse):")
print(f"  {'n_safe':>6} {'n_jolly':>7} {'min_gap':>8} {'min_q_jolly':>12} {'ROI':>8} {'P&L':>8} {'Scomm':>7}")
for _, r in opt_df.sort_values("roi", ascending=False).head(15).iterrows():
    print(f"  {int(r.n_safe):>6} {int(r.n_jolly):>7} {r.min_gap:>8.2f} {r.min_q_jolly:>12.1f} {r.roi:>+7.1f}% {r.pl:>+7.1f}€ {int(r.scommesse):>7}")

print("\nTOP 15 per P&L (min 60 scommesse):")
print(f"  {'n_safe':>6} {'n_jolly':>7} {'min_gap':>8} {'min_q_jolly':>12} {'ROI':>8} {'P&L':>8} {'Scomm':>7}")
for _, r in opt_df.sort_values("pl", ascending=False).head(15).iterrows():
    print(f"  {int(r.n_safe):>6} {int(r.n_jolly):>7} {r.min_gap:>8.2f} {r.min_q_jolly:>12.1f} {r.roi:>+7.1f}% {r.pl:>+7.1f}€ {int(r.scommesse):>7}")

# Verifica stabilità della strategia ottimale su tutte le 9 stagioni
best_opt = opt_df.sort_values("roi", ascending=False).iloc[0]
print(f"\nStrategia ottimale per le ultime 3 stagioni:")
print(f"  n_safe={int(best_opt.n_safe)}, n_jolly={int(best_opt.n_jolly)}, "
      f"min_gap={best_opt.min_gap}, min_q_jolly={best_opt.min_q_jolly}")
print(f"  ROI={best_opt.roi:+.1f}%  P&L={best_opt.pl:+.1f}€  ({int(best_opt.scommesse)} scommesse)\n")
print("  Verifica su tutte le stagioni (overfitting check):")
for season in season_order:
    sg = df[df["season"] == season]
    roi_s, scomm_s, pl_s = simula_con_gap(
        sg, int(best_opt.n_safe), int(best_opt.n_jolly),
        best_opt.min_gap, best_opt.min_q_jolly
    )
    print(f"    {season}: ROI={roi_s:+.1f}%  P&L={pl_s:+.1f}€  ({scomm_s} scommesse)")
