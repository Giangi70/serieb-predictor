"""Addestra il modello XGBoost e lo salva in models/."""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import DATA_PROCESSED, MODELS_DIR
from src.training.preprocess import run as preprocess_run

# Colonne da escludere dalle feature
NON_FEATURE_COLS = {"result", "season", "date", "home_team", "away_team"}


def load_dataset() -> pd.DataFrame:
    """Carica il dataset processato, eseguendo il preprocessing se necessario."""
    path = DATA_PROCESSED / "dataset.csv"
    if not path.exists():
        print("[INFO] Dataset non trovato, eseguo preprocessing...")
        return preprocess_run()
    return pd.read_csv(path)


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Restituisce le colonne feature (esclude target e metadati)."""
    return [c for c in df.columns if c not in NON_FEATURE_COLS]


def train(df: pd.DataFrame) -> tuple[XGBClassifier, LabelEncoder, list[str]]:
    """Addestra il modello e restituisce (model, encoder, feature_cols).

    Args:
        df: DataFrame con feature e colonna 'result'.

    Returns:
        Tupla (modello addestrato, label encoder, lista feature).
    """
    feature_cols = get_feature_cols(df)
    X = df[feature_cols].fillna(0).values
    le = LabelEncoder()
    y = le.fit_transform(df["result"])  # A=0, D=1, H=2

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )

    # Cross-validation per stimare le performance
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"[CV] Accuracy: {scores.mean():.3f} ± {scores.std():.3f}")

    # Training finale su tutto il dataset
    model.fit(X, y)

    # Report sul training set
    y_pred = model.predict(X)
    print("\n[REPORT] Training set:")
    print(classification_report(y, y_pred, target_names=le.classes_))

    return model, le, feature_cols


def save_model(model: XGBClassifier, le: LabelEncoder, feature_cols: list[str]) -> Path:
    """Salva modello, encoder e lista feature in models/."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out = MODELS_DIR / "model.joblib"
    joblib.dump({"model": model, "encoder": le, "features": feature_cols}, out)
    print(f"[OK] Modello salvato: {out}")
    return out


def run() -> Path:
    """Pipeline completa: carica → addestra → salva."""
    df = load_dataset()
    print(f"[INFO] Dataset: {len(df)} partite, {len(get_feature_cols(df))} feature")
    model, le, feature_cols = train(df)
    return save_model(model, le, feature_cols)


if __name__ == "__main__":
    run()
