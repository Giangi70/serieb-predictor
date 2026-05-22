"""Inferenza su nuove partite usando il modello addestrato."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import MODELS_DIR

_cache: dict = {}


def load_model() -> dict:
    """Carica il modello dal disco (con cache in memoria)."""
    if not _cache:
        path = MODELS_DIR / "model.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Modello non trovato: {path}. Esegui prima train.py")
        _cache.update(joblib.load(path))
    return _cache


def build_features_from_odds(odds: dict[str, float]) -> dict[str, float]:
    """Converte quote raw (es. PSH, WHD) nelle feature attese dal modello.

    Gestisce sia il formato storico (PSH/PSD/PSA) che il formato live
    dell'API (stessa convenzione). Calcola prob, std, divergence, n_bookmakers.
    """
    # Bookmaker supportati: prefisso → suffissi H/D/A
    BK_SUFFIXES = {
        "B365": ("B365H", "B365D", "B365A"),
        "WH":   ("WHH",   "WHD",   "WHA"),
        "IW":   ("IWH",   "IWD",   "IWA"),
        "PS":   ("PSH",   "PSD",   "PSA"),
        "VC":   ("VCH",   "VCD",   "VCA"),
    }

    feat: dict[str, float] = {}
    odds_h, odds_d, odds_a = [], [], []

    for bk, (ch, cd, ca) in BK_SUFFIXES.items():
        h, d, a = odds.get(ch), odds.get(cd), odds.get(ca)
        if h and d and a and h > 1 and d > 1 and a > 1:
            feat[f"{bk}_H"] = h
            feat[f"{bk}_D"] = d
            feat[f"{bk}_A"] = a
            odds_h.append(h)
            odds_d.append(d)
            odds_a.append(a)

    if not odds_h:
        return feat

    def implied_prob(ol: list) -> float:
        raw = np.mean([1 / o for o in ol])
        total = np.mean([1/h + 1/d + 1/a for h, d, a in zip(odds_h, odds_d, odds_a)])
        return raw / total

    feat["prob_H"] = implied_prob(odds_h)
    feat["prob_D"] = implied_prob(odds_d)
    feat["prob_A"] = implied_prob(odds_a)
    feat["std_H"] = float(np.std(odds_h))
    feat["std_D"] = float(np.std(odds_d))
    feat["std_A"] = float(np.std(odds_a))
    feat["divergence"] = max(
        max(odds_h) - min(odds_h),
        max(odds_d) - min(odds_d),
        max(odds_a) - min(odds_a),
    )
    feat["n_bookmakers"] = len(odds_h)
    return feat


def predict(odds: dict[str, float]) -> dict:
    """Predice le probabilità di 1/X/2 per una partita.

    Args:
        odds: Quote raw dei bookmaker (es. {"PSH": 2.1, "PSD": 3.2, "PSA": 3.5, ...})

    Returns:
        Dizionario con:
        - "probs": {"H": float, "D": float, "A": float}
        - "prediction": "H" | "D" | "A"
        - "confidence": float (probabilità della classe predetta)
    """
    bundle = load_model()
    model = bundle["model"]
    le = bundle["encoder"]
    feature_cols = bundle["features"]

    features = build_features_from_odds(odds)
    X = np.array([features.get(col, 0.0) for col in feature_cols]).reshape(1, -1)

    proba = model.predict_proba(X)[0]
    classes = le.classes_  # ['A', 'D', 'H']

    probs = {cls: float(p) for cls, p in zip(classes, proba)}
    best = max(probs, key=probs.__getitem__)

    return {
        "probs": probs,
        "prediction": best,
        "confidence": probs[best],
    }


# Soglie filtro value betting calibrate sui dati storici (5 stagioni)
VALUE_BET_FILTERS = {
    "A": {"prob_min": 0.45, "std_max": 0.0417},  # ROI +10.2% su 393 partite
}


def is_value_bet(result: dict, odds: dict[str, float]) -> bool:
    """Restituisce True se la partita soddisfa il filtro value betting."""
    prediction = result["prediction"]
    if prediction not in VALUE_BET_FILTERS:
        return False

    f = VALUE_BET_FILTERS[prediction]
    features = build_features_from_odds(odds)
    std = features.get(f"std_{prediction}", 999)
    prob = result["probs"][prediction]
    return prob >= f["prob_min"] and std <= f["std_max"]


def predict_match(home: str, away: str, odds: dict[str, float]) -> dict:
    """Wrapper con metadati partita.

    Args:
        home: Nome squadra casa.
        away: Nome squadra trasferta.
        odds: Quote bookmaker.

    Returns:
        Risultato predict() arricchito con home/away.
    """
    result = predict(odds)
    result["home"] = home
    result["away"] = away
    label_map = {"H": home, "D": "Pareggio", "A": away}
    result["prediction_label"] = label_map[result["prediction"]]
    result["value_bet"] = is_value_bet(result, odds)
    return result
